#!/usr/bin/python

#KXR DAQ - example file for 4 differential channels

import numpy as np
import RPi.GPIO as GPIO
import ADS1256

# Example pins for 1 pi hat
# Pin definition        #using pins for hat 1 from kxr hat, gpio pin
RST_PIN  = 24
CS_PIN   = 8
DRDY_PIN = 22

try:
    ADC = ADS1256.ADS1256(RST_PIN, CS_PIN, DRDY_PIN)
    ADC.init()
    ADC.configADC(6,0xF0)

    while True:
        ADC_Value = ADC.getAll()
        voltage = np.array(ADC_Value) * 5.0 / 0x7fffff

        print("0 ADC = %lf" % (voltage[0]), end='\t')
        print("1 ADC = %lf" % (voltage[1]), end='\t')
        print("2 ADC = %lf" % (voltage[2]), end='\t')
        print("3 ADC = %lf" % (voltage[3]))

except:
    GPIO.cleanup()
    print("\r\nProgram end     ")
    exit()
