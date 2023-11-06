#!/usr/bin/env python3
import RPi.GPIO as GPIO  
from hx711 import HX711  

try:
    GPIO.setmode(GPIO.BCM)  
    hx = HX711(dout_pin=20, pd_sck_pin=21)
    err = hx.zero()
    if err:
        raise ValueError('Tare is unsuccessful.')

    reading = hx.get_raw_data_mean()
    if reading:  
        print('Data subtracted by offset but still not converted to units:',
              reading)
    else:
        print('invalid data', reading)

    input('Put known weight on the scale and then press Enter')
    reading = hx.get_data_mean()
    if reading:
        print('Mean value from HX711 subtracted by offset:', reading)
        known_weight_grams = input(
            'Write how many grams it was and press Enter: ')
        try:
            value = float(known_weight_grams)
            print(value, 'grams')
        except ValueError:
            print('Expected integer or float and I have got:',
                  known_weight_grams)

        ratio = reading / value  
        hx.set_scale_ratio(ratio)  
        print('Your ratio is', ratio)
    else:
        raise ValueError('Cannot calculate mean value. Try debug mode. Variable reading:', reading)

    input('Press Enter to show reading')
    print('Current weight on the scale in grams is: ',hx.get_data_mean()/ratio)

except (KeyboardInterrupt, SystemExit):
    print('Bye :)')

finally:
    GPIO.cleanup()
