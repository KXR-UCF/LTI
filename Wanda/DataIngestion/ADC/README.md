# ADS1256

This folder contains information regarding the ADC using an ADS1256. 

## ADS1256.py

This library is a modified version of the library from [this repo for Waveshare boards](https://github.com/waveshareteam/High-Precision-AD-DA-Board/tree/master/RaspberryPI/ADS1256/python3).

This modified version supports setting the scan_mode to 1 (differential mode), and also the ability to create multiple instances with different pins to be able to use multiple ADCs.

### How to Use

Declare an instance of the ADS1256 class with the pins for the ADC (for pin numbers refer to the [Pi Hat README](Pi%20Hat#jumpers)). Make sure to also run the instance's `init()` function.

#### Functions

+ `configADC(gain, dataRate)`: Change the gain or data rate. Acceptable parameters can be found at the top of [`ADS1256.py`](ADS1256.py).

+ `setMode(mode)`: sets mode to single-ended (8 channels) or differential mode (4 channels). The hat uses differential mode (int 1). If for somereason you need to use single-ended inputs which supports 8 channels, pass 0 to this function.

+ `getChannelValue(channel)`: Get the output value of a specific channel. This output value is not directly equal to the voltage.

+ `getChannelVoltage(self, channel, Vref=2.5)`: Get the output voltage of a specific channel. In differential mode: channels 0-3. In single ended mode: chanmels: 0-7.  
**This is the primary function that should be used to get data from the adc.**

An example file is provided: [`4chdiff.py`](4chdiff.py)

### Potential Issues

The raspberry pi 5 no longer supports the [`RPi.GPIO` Library](https://pypi.org/project/RPi.GPIO/). Instead install the [`rpi-lgpio` Library](https://pypi.org/project/rpi-lgpio/). This library does not need any of the python code to be changed (this includes the import statement).

To use the library on a raspberry pi add the line `dtoverlay=spi0-0cs` to `/boot/firmware/config.txt` (or `/boot/firmware/config.txt` on older versions), removing any conflicting dtoverlays if necessary (comment out `dtparam=spi=on`). A longer explanation why this change is needed can be found in the [Pi Hat Folder](Pi%20Hat/).


## adcmanager.py

This module helps handle multiple sensors and maps them to their ADC and channel. Each sensor should be created using the `Sensor` class. This class is capable of retrieving voltage values from the appropriate channel and applies the stored calibration file before output. The mapping and calibration values can be configured in the [`config.yaml` file](config.yaml). 

TBA

## config.yaml

TBA

## Helpful Resources
[ADS1256 Datasheet](https://www.ti.com/product/ADS1256)