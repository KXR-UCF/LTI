#!/usr/bin/python

#KXR DAQ - example file for 4 differential channels

import numpy as np
import RPi.GPIO as GPIO
import ADS1256

# Example pins for 1 pi hat
# Pin definition        #using pins for hat 1 from kxr hat, gpio pin
#RST_PIN  = 24
#CS_PIN   = 8
#DRDY_PIN = 22

# ADC2
RST_PIN = 25
CS_PIN = 7
DRDY_PIN = 16

samp = np.array([])
cal_val = 13.36/3.68

try:
    ADC = ADS1256.ADS1256(RST_PIN, CS_PIN, DRDY_PIN)
    ADC.init()
    ADC.configADC(6,0xF0)

    while True:
        ADC_Value = ADC.getAll()
        voltage = np.array(ADC_Value) * 5.0 / 0x7fffff
        voltage = voltage * 1000
        voltage = voltage * cal_val

        #print("0 ADC = %lf" % (voltage[0]), end='\t')
        #print("1 ADC = %lf" % (voltage[1]), end='\t')
        #print("2 ADC = %lf" % (voltage[2]), end='\t')
        print("3 ADC = %lf" % (voltage[3]))
        
        if voltage[3] < 10:
            samp = np.append(samp, voltage[3])
        #print(np.mean(samp))


except:
    GPIO.cleanup()
    print("\r\nProgram end     ")
    exit()
