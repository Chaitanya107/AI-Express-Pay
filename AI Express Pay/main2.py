#!/usr/bin/env python

import cv2
from picamera2 import Picamera2
import os
import sys, getopt, time
import numpy as np
from edge_impulse_linux.image import ImageImpulseRunner
from collections import Counter

import RPi.GPIO as GPIO
from hx711 import HX711

import requests
import json
from requests.structures import CaseInsensitiveDict

ratio = 1500 #11950.897647

GPIO.setmode(GPIO.BCM)
hx = HX711(dout_pin=20, pd_sck_pin=21)
err = hx.zero()
hx.set_scale_ratio(ratio)

runner = None
old_label = None
old_weight = 9999999999
post_done = 0


product_id = {'Apple': 1, 'Lays': 2, 'DM': 3}
names = {'Apple':'Apple', 'Lays':'Lays', 'DM':'Diary Milk'}
units = {"Apple":"KG", "Lays":"U", "DM":"U"}
unit_weight = {'Lays':13, 'DM':24}
unit_price = {'Apple':10, 'Lays':1, 'DM':2}

def help():
    print('python3 main.py <path_to_model.eim>')

def find_weight():
    return hx.get_data_mean()/ratio
    
def post_data_to_api(label, value):
    if label == 'Apple':
        taken = value * 0.12
    else:
        taken = value
        
    final_rate = taken * unit_price[label]
    url = "https://ai-express-pay.onrender.com/product"
    headers = CaseInsensitiveDict()
    headers["Content-Type"] = "application/json"
    data_dict = {"id":str(product_id[label]),"name":names[label],"price":unit_price[label],"unit":units[label],"taken":str(taken),"payable":str(final_rate)}
    data = json.dumps(data_dict)
    resp = requests.post(url, headers=headers, data=data)
    print(resp.status_code)
    return (resp.status_code)

def main(argv):
    try:
        opts, args = getopt.getopt(argv, "h", ["--help"])
    except getopt.GetoptError:
        help()
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            help()
            sys.exit()

    if len(args) != 1:
        help()
        sys.exit(2)

    model = args[0]

    dir_path = os.path.dirname(os.path.realpath(__file__))
    modelfile = os.path.join(dir_path, model)

    print('MODEL: ' + modelfile)
    
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (4608,2592)}))
    picam2.start()

    with ImageImpulseRunner(modelfile) as runner:
        try:
            model_info = runner.init()
            print('Loaded runner for "' + model_info['project']['owner'] + ' / ' + model_info['project']['name'] + '"')
            labels = model_info['model_parameters']['labels']
            
            while True:
                global old_label, post_done, old_weight
                img = picam2.capture_array()
                if img is None:
                    print('Failed to capture image')
                    exit(1)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

                features, cropped = runner.get_features_from_image(img)

                res = runner.classify(features)

                if "classification" in res["result"].keys():
                    print('Result (%d ms.) ' % (res['timing']['dsp'] + res['timing']['classification']), end='')
                    for label in labels:
                        score = res['result']['classification'][label]
                        print('%s: %.2f\t' % (label, score), end='')
                    print('', flush=True)

                elif "bounding_boxes" in res["result"].keys():
                    print('Found %d bounding boxes (%d ms.)' % (len(res["result"]["bounding_boxes"]), res['timing']['dsp'] + res['timing']['classification']))
                    data = res["result"]["bounding_boxes"]
                    products = dict(Counter(item['label'] for item in data if item['value'] > 0.9))
                    print(products)
                    if post_done == 0:
                        for key, value in products.items():
                            if key != old_label:
                                status = post_data_to_api(key, value)
                                if status == 200:
                                    post_done = 1
                            else:
                                old_label = key
                                post_done = 0
                       

                cv2.imshow('image', cv2.cvtColor(cropped, cv2.COLOR_GRAY2RGB))
                cv2.waitKey(1)

        finally:
            if (runner):
                runner.stop()

if __name__ == "__main__":
   main(sys.argv[1:])
