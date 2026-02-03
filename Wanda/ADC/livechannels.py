#!/usr/bin/python

#KXR DAQ - calibration file for 4-8 channels
import numpy as np
import RPi.GPIO as GPIO
import ADS1256
import sys
from collections import deque
import time

DIFFERENTIAL = True
ADC_ID = 1

VREF = 2.5
PGA = 64

# Pin definition (GPIO)    
if ADC_ID == 1:
    RST_PIN  = 24
    CS_PIN   = 8
    DRDY_PIN = 22
else: 
    RST_PIN  = 25
    CS_PIN   = 7
    DRDY_PIN = 23

scale_factors = [1, 1, 1, 1, 1, 1, 1, 1]
bias_factors = [0, 0, 0, 0, 0, 0, 0, 0]
# history = [deque(maxlen=500) for _ in range(8)]
loop_time = deque(maxlen=10)

try:
    ADC = ADS1256.ADS1256(RST_PIN, CS_PIN, DRDY_PIN)
    ADC.init()
    ADC.configADC(6,0xC0)
    
    if not DIFFERENTIAL:
        ADC.setMode(0)

    while True:
        start_time = time.time()
        voltages = ADC.getAllVoltages()
        output_line = ''
        for i, voltage in enumerate(voltages):
            value = (voltage * scale_factors[i]) + bias_factors[i]
            if DIFFERENTIAL and i > 3:
                break
            output_line = output_line + f" {i}: {value:<10.6f}"
        print(output_line)

        loop_time.append(time.time() - start_time)


except Exception as e:
    GPIO.cleanup()
    print(e)
    print("\r\nProgram end     ")
    exit()
