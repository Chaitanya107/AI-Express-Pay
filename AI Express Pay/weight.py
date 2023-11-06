import RPi.GPIO as GPIO  
from hx711 import HX711  

ratio = 1500

GPIO.setmode(GPIO.BCM)
hx = HX711(dout_pin=20, pd_sck_pin=21)
err = hx.zero()
hx.set_scale_ratio(ratio)


while True:
    input("Put weight and Press Enter")
    print("Weight = ",hx.get_data_mean()/ratio)
    #print(hx.get_raw_data_mean())
