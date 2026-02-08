#!/usr/bin/env python3
# Styling: PEP 8

"""KXR file for handling sensors/transducers connected to the KXR ADS1256 Pi hat"""

#TODO change tare to be in ram and have a zero value that is set in the config file

from ADC import ADS1256
import numpy as np
import yaml
import os

module_path = os.path.abspath(__file__)
module_directory = os.path.dirname(module_path)

CONFIG_FILE_NAME = f"{module_directory}/config.yaml"
with open(CONFIG_FILE_NAME, 'r') as file:
    config = yaml.safe_load(file)

# load ADCs
ENABLED_ADCS = []
ADC1_ENABLED = config["ADC1"]["enabled"]
ADC2_ENABLED = config["ADC2"]["enabled"]
    
if not (ADC1_ENABLED or ADC2_ENABLED):
    print("---No ADC Enabled---")
    exit()

if ADC1_ENABLED:
    ENABLED_ADCS.append(1)
if ADC2_ENABLED:
    ENABLED_ADCS.append(2)

# sets and initilizes the enabled ADCs from the config file
_ADCs = {}
for adc in ENABLED_ADCS:
    rst_pin = config[f"ADC{adc}"]["RST_PIN"]
    cs_pin = config[f"ADC{adc}"]["CS_PIN"]
    drdy_pin = config[f"ADC{adc}"]["DRDY_PIN"]

    gain = config[f"ADC{adc}"]["gain"]
    data_rate = config[f"ADC{adc}"]["data_rate"]

    new_ADC = ADS1256.ADS1256(rst_pin, cs_pin, drdy_pin)
    new_ADC.init()
    new_ADC.configADC(ADS1256.GAIN_E[gain], ADS1256.DRATE_E[data_rate])
    if not config[f"ADC{adc}"]["differential"]:
        new_ADC.setMode(0)
    _ADCs[adc] = (new_ADC)
    print(f"ADC{adc} Initialized")


class Sensor:
    """Sensor parent class which maps the sensor to the ADC and its channel"""
    sensor_type = None

    def __init__(self, sensor_name: str):
        """Sets ADC and channel of sensor
        
        Args:
            sensor_name (str): name of sensor in config file
        """
        self.name = sensor_name
        
        sensor_found = False
        # check for sensors on each enabled ADC
        for adc_id in ENABLED_ADCS:
            if sensor_found:
                break
            # check each channel of the adc
            for channel_id in config[f"ADC{adc_id}"]["channels"]:
                if sensor_found:
                    break

                attached_device_name = config[f"ADC{adc_id}"]["channels"][channel_id]
                
                # print(f"{attached_device_name}\t{sensor_name}")


                # filter for sensors of sensor type and create a list of them
                if attached_device_name == sensor_name:
                    self.adc_id = adc_id
                    self.channel_id = channel_id
                    sensor_found = True

        if not sensor_found:
            print(f"Error: No Sensor with name: {sensor_name} found --> Check config file {CONFIG_FILE_NAME}")
            return
            # might raise some exception here

        self.zero = config["sensors"][sensor_name]["zero"]
        if self.zero == None:
            self.zero = 0
            print(f"Warning no zero set for sensor <{self.name}> check config file")

        self.scale = config["sensors"][sensor_name]["scale"]
        if self.scale == None:
            self.scale = 1
            print(f"Warning no scale set for sensor <{self.name}> check config file")

    def get_voltage(self) -> float:
        """Gets the voltages of a sensor
        
        Returns:
            sensor_voltage (float): the voltage (0-5V) returned from the sensor
        """
        adc = _ADCs[self.adc_id]
        sensor_voltage = adc.getChannelVoltage(self.channel_id) # gets the sensor voltage
        return sensor_voltage
    
    def get_calibrated_value_linear(self):
        """Gets the calibrated value using the zero and scale from the config file

        Returns:
            cal_value (float): the calibrated value from the sensor
        """
        cal_value = self.get_voltage()*self.scale + self.zero
        return cal_value

    # def calibrate_tare(self, num_samples: int):
    #     """Calibrates the tare of the load cell from several samples
        
    #     Args:
    #         num_samples (int): number of samples to average for the tare
    #     """
    #     sample_arr = np.array([])
    #     print(f"Load Cell <{self.name}> Calibrating Tare")
    #     self.tare = 0
    #     for i in range(num_samples):
    #         sample_arr = np.append(sample_arr, self.get_force())
    #     self.set_tare(-1 * np.mean(sample_arr))
    #     print(f"Load Cell <{self.name}> Tare Calibrated")

    # def write_tare_to_config(self):
    #     """Writes the tare to the config file"""
    #     config["devices"][LoadCell.sensor_type][self.name]["tare"] = float(self.tare)
    #     with open(CONFIG_FILE_NAME, 'w') as file:
    #         yaml.safe_dump(config, file, default_flow_style=False, sort_keys=False)
        
