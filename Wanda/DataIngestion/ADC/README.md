# ADC

This folder contains the ADS1256 library and the DAQ manager module to interface with the ADS1256 Pi Hats on the Raspberry Pis

## Files
 
| File | Description |
|---|---|
| [`ADS1256.py`](ADS1256.py) | Low-level SPI library for the ADS1256 ADC |
| [`adcmanager.py`](adcmanager.py) | High-level DAQ and Sensor manager, configured via YAML |

## ADS1256.py

This library is a modified version of the library from [this repo for Waveshare boards](https://github.com/waveshareteam/High-Precision-AD-DA-Board/tree/master/RaspberryPI/ADS1256/python3).

**Modifications**
- Added `scan_mode` instance variable to properly support differential mode (`setMode()` was previously not working)
- Supports multiple instances of the ADS1256 with seperate pin numbers.

### Setup

The raspberry pi 5 no longer supports the [`RPi.GPIO` Library](https://pypi.org/project/RPi.GPIO/). Instead install the [`rpi-lgpio` Library](https://pypi.org/project/rpi-lgpio/). This library does not need any of the python code to be changed (this includes the import statement).

To use the library on a raspberry pi add the line `dtoverlay=spi0-0cs` to `/boot/firmware/config.txt` (or `/boot/firmware/config.txt` on older versions), removing any conflicting dtoverlays if necessary (comment out `dtparam=spi=on`). A longer explanation why this change is needed can be found in the [Pi Hat Folder](Pi%20Hat/).

### Usage

Declare an instance of the ADS1256 class with the pins for the ADC (for pin numbers refer to the [Pi Hat README](Pi%20Hat#jumpers)).

Example:
```python
from ADS1256 import ADS1256, GAIN_E, DRATE_E

adc = ADS1256(rst_pin=24, cs_pin=8, drdy_pin=22)
adc.init()
adc.configADC(GAIN_E['GAIN_2'], DRATE_E['3750SPS'])
adc.setMode(0) # 0 = single-ended (8 ch), 1 = differential (4 ch)

voltage = adc.getChannelVoltage(channel=0)
```

An additional example file is provided in [`4chdiff.py`](4chdiff.py)

#### Functions

| Function | Description |
|---|---|
| `init()` | Initializes GPIO/SPI, resets chip, and verifies chip ID. Applies a default config. **Must be called before any other function can work** |
| `configADC(gain, dataRate)` | Change the PGA gain or data rate. Acceptable parameters can be found at the top of [`ADS1256.py`](ADS1256.py) in `GAIN_E` and `DRATE_E`. |
| `setMode(mode)` | `0` = single-ended (8 channels), `1` = differential (4 channels, default). |
| `getChannelValue(channel)` | Get the output value of a specific channel. The returned value is the raw 24-but reading of a channel. This output value is not directly equal to the voltage. |
| `getChannelVoltage(self, channel, Vref=2.5)` | Get the output voltage of a specific channel. In differential mode: channels 0-3. In single ended mode: chanmels: 0-7. **Primary function for retrieving information from sensor channels** |
| `readChipID()` | Reads the chip ID of the ADS1256. Returns `3` if ADS1256 is healthy/connected |
| `module_exit()` | Cleans GPIO and closes SPI. Recomeneded to call on shutdown |

**Available Gain Settings (`GAIN_E`):** `GAIN_1`, `GAIN_2`, `GAIN_4`, `GAIN_8`, `GAIN_16`, `GAIN_32`, `GAIN_64`
 
**Available Data Rates (`DRATE_E`):** `30000SPS`, `15000SPS`, `7500SPS`, `3750SPS`, `2000SPS`, `1000SPS`, `500SPS`, `100SPS`, `60SPS`, `50SPS`, `30SPS`, `25SPS`, `15SPS`, `10SPS`, `5SPS`, `2d5SPS`

---

## adcmanager.py

DAQ manager that wraps `ADS1256.py`. Reads a YAML config file to initialize ADCs and map named sensors to specific channels, additionally handles sensor calibration values.

### Usage
 
```python
from adcmanager import DAQ
 
with DAQ("config.yaml") as daq:
    values = daq.get_all_sensor_values()
    print(values)  # {'pt1': 245.3, 'pt2': 118.7, ...}
```

Using `DAQ` as a context manager (`with` statement) is recommended since it runs a health check on startup and calls `cleanup()` on exit.

### Config File
 
The config file is a YAML file with two top-level sections: ADC hardware configuration and sensor definitions.
 
```yaml
ADC1:
  enabled: true
  differential: false       # true = differential mode (4 ch), false = single-ended (8 ch)
  gain: "GAIN_2"            # See GAIN_E in ADS1256.py
  data_rate: "3750SPS"      # See DRATE_E in ADS1256.py
  RST_PIN: 24               # BCM pin numbers
  CS_PIN: 8
  DRDY_PIN: 22
  channels:
    0: "pt2"                # Map channel index to sensor name (must match a key under `sensors`)
    1: "pt1"
    2: null                 # Unmapped channels should be set to null
 
ADC2:
  enabled: true
  differential: false
  gain: "GAIN_1"
  data_rate: "3750SPS"
  RST_PIN: 25
  CS_PIN: 7
  DRDY_PIN: 23
  channels:
    0: "pt3"
    1: "continuity_raw"
    2: null
 
sensors:
  pt1:
    zero: -1031.4           # Voltage offset (additive, applied after scale)
    scale: 3071.4           # Volts-to-engineering-units scale factor
  pt2:
    zero: -283.77
    scale: 918.83
  pt3:
    zero: null              # A null zero defaults to 0
    scale: null             # A null scale defaults to 1
  continuity_raw:
    zero: 0
    scale: 1
```

**Calibration formula:** `calibrated_value = voltage × scale + zero`
 
Sensor names used in the `channels` map must have a corresponding entry under `sensors`. Channels set to `null` are ignored

### DAQ Class
 
| Method | Description |
|---|---|
| `DAQ(config_filename)` | Loads config, initializes enabled ADCs, and registers all sensors. |
| `get_all_sensor_values()` | Returns a `dict` of `{sensor_name: calibrated_value}` for all configured sensors. |
| `get_sensor_names()` | Returns a list of all configured sensor names. |
| `get_sensor_dict()` | Returns the `{name: Sensor}` dictionary. |
| `check_health(retries=1)` | Reads chip ID from each ADC. Attempts re-initialization on failure. Returns `True` if all ADCs are healthy. |
| `cleanup()` | Releases GPIO and SPI resources. Called automatically when used as a context manager. |
 
### Sensor Class
 
`Sensor` objects are created automatically by `DAQ` during config loading. They can also be created manually via `daq.create_sensor(sensor_name)`.
 
| Method | Description |
|---|---|
| `get_voltage()` | Returns the raw voltage from the sensor's ADC channel. |
| `get_calibrated_value_linear()` | Returns `voltage × scale + zero` using values from the config. |
 
---

## Example Scripts
 
The following scripts are development and calibration utilities. They are not part of the data ingestion and are not intended for production.
 
| File | Description |
|---|---|
| `4chdiff.py` | Basic example reading 4 differential channels in a loop and printing voltages. |
| `calibration.py` | Reads all channels and prints a rolling average, useful for determining `scale` and `zero` values for the config file. Supports both single-ended and differential mode via the `DIFFERENTIAL` flag. |
| `livechannels.py` | Same as `calibration.py` but without averaging — prints raw per-sample values. Useful for checking noise and live sensor response. |
 
---
 
## Helpful Resources
 
- [ADS1256 Datasheet](https://www.ti.com/product/ADS1256)
- [Waveshare High-Precision AD/DA Board](https://github.com/waveshareteam/High-Precision-AD-DA-Board)
- [`rpi-lgpio` (Pi 5 GPIO replacement)](https://pypi.org/project/rpi-lgpio/)
