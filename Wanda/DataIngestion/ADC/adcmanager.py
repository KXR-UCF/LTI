#!/usr/bin/env python3
# Styling: PEP 8

"""KXR file for handling sensors/transducers connected to the KXR ADS1256 Pi hat"""

#TODO change tare to be in ram and have a zero value that is set in the config file

from Wanda.DataIngestion.ADC import ADS1256
import numpy as np
import yaml

from datetime import datetime
from pytz import timezone
est = timezone('US/Eastern')

def print_log(message:str):
    lines = message.split('\n')
    for line in lines:
        print(f"[{datetime.now(tz=est).strftime('%Y-%m-%d %H:%M:%S')}] {line}")

import os
module_path = os.path.abspath(__file__)
module_directory = os.path.dirname(module_path)
del os


class DAQ:

    def __init__(self, config_filename: str):
        self.config_filename = config_filename

        self.config = {}
        self.enabled_adc_ids = []
        self.adcs = {}

        self.sensor_names = []
        self.sensors = {}

        self.load_ADC_from_config()
        self.load_sensors_from_config()

    def load_ADC_from_config(self):
        if not self.config:
            with open(self.config_filename, 'r') as file:
                self.config = yaml.safe_load(file)

        # load ADCs
        ADC1_ENABLED = self.config["ADC1"]["enabled"]
        ADC2_ENABLED = self.config["ADC2"]["enabled"]
            
        if not (ADC1_ENABLED or ADC2_ENABLED):
            print_log("---No ADC Enabled---")
            exit()

        if ADC1_ENABLED:
            self.enabled_adc_ids.append(1)
        if ADC2_ENABLED:
            self.enabled_adc_ids.append(2)

        # sets and initilizes the enabled ADCs from the config file
        for adc_id in self.enabled_adc_ids:
            rst_pin = self.config[f"ADC{adc_id}"]["RST_PIN"]
            cs_pin = self.config[f"ADC{adc_id}"]["CS_PIN"]
            drdy_pin = self.config[f"ADC{adc_id}"]["DRDY_PIN"]

            self.adcs[adc_id] = ADS1256.ADS1256(rst_pin, cs_pin, drdy_pin)
            self.init_adc(adc_id)

            print_log(f"ADC{adc_id} Initialized")

    def init_adc(self, adc_id: int):
        adc = self.adcs[adc_id]
        gain = self.config[f"ADC{adc_id}"]["gain"]
        data_rate = self.config[f"ADC{adc_id}"]["data_rate"]

        adc.init()
        adc.configADC(ADS1256.GAIN_E[gain], ADS1256.DRATE_E[data_rate])
        if not self.config[f"ADC{adc_id}"]["differential"]:
            adc.setMode(0)


    def create_sensor(self, sensor_name: str):
        """Factory method to create a sensor tied to this DAQ's config."""
        return Sensor(sensor_name, self)
    
    def load_sensors_from_config(self):
        if not self.config:
            with open(self.config_filename, 'r') as file:
                self.config = yaml.safe_load(file)

        for sensor_name in self.config["sensors"]:
            sensor_name = str(sensor_name)

            self.sensor_names.append(sensor_name)
            self.sensors[sensor_name] = self.create_sensor(sensor_name)
        
    def get_sensor_names(self) -> list:
        return self.sensor_names       

    def get_sensor_dict(self) -> dict:
        return self.sensors

    def get_all_sensor_values(self) -> dict:
        """
        Fetches and applies calibration to all configured sensors.
        
        Returns:
            results (dict): dictionary of {sensor_name: calibrated_value}.
        """
        sensor_values = {}
        for sensor in self.sensors.values():
            sensor_values[sensor.name] = sensor.get_calibrated_value_linear()
        return sensor_values
    
    def check_health(self, retries: int = 1) -> bool:
        """Checks if the connected ADCs are responding properly, and attempts to reconnect if not."""
        all_healthy = True
        for adc_id, adc in self.adcs.items():
            chip_id = adc.readChipID()
            if chip_id == 3:
                print_log(f"Health Check: ADC{adc_id} is connected and responding.")
            else:
                print_log(f"Health Check: ADC{adc_id} failed! Chip ID returned {chip_id} (expected 3).")
                
                reconnected = False
                for attempt in range(retries):
                    print_log(f"Attempting to reconnect ADC{adc_id} (Attempt {attempt + 1}/{retries})...")
                    self.init_adc(adc_id)
                    
                    if adc.readChipID() == 3:
                        print_log(f"ADC{adc_id} reconnected successfully.")
                        reconnected = True
                        break
                
                if not reconnected:
                    print_log(f"ADC{adc_id} reconnection failed.")
                    all_healthy = False
        return all_healthy

    def cleanup(self):
        for adc in self.adcs.values():
            adc.module_exit()
            break
    
    def __enter__(self):
        # Verify ADCs are connected, with 3 reconnection attempts
        if not self.check_health(retries=3):
            self.cleanup()
            raise SystemExit("CRITICAL: ADCs failed health check. Aborting startup.")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


class Sensor:
    """Sensor parent class which maps the sensor to the ADC and its channel"""
    sensor_type = None

    def __init__(self, sensor_name: str, daq: DAQ):
        """Sets ADC and channel of sensor
        
        Args:
            sensor_name (str): name of sensor in config file
            daq (DAQ): The DAQ manager instance
        """
        self.name = sensor_name
        self.daq = daq
        
        sensor_found = False
        # check for sensors on each enabled ADC
        for adc_id in self.daq.enabled_adc_ids:
            if sensor_found:
                break
            # check each channel of the adc
            for channel_id in self.daq.config[f"ADC{adc_id}"]["channels"]:
                if sensor_found:
                    break

                attached_device_name = self.daq.config[f"ADC{adc_id}"]["channels"][channel_id]
                
                # print_log(f"{attached_device_name}\t{sensor_name}")


                # filter for sensors of sensor type and create a list of them
                if attached_device_name == sensor_name:
                    self.adc_id = adc_id
                    self.channel_id = channel_id
                    sensor_found = True

        if not sensor_found:
            print_log(f"Error: No Sensor with name: {sensor_name} found --> Check config file")
            return
            # might raise some exception here

        self.zero = self.daq.config["sensors"][sensor_name]["zero"]
        if self.zero == None:
            self.zero = 0
            print_log(f"Warning no zero set for sensor <{self.name}> check config file")

        self.scale = self.daq.config["sensors"][sensor_name]["scale"]
        if self.scale == None:
            self.scale = 1
            print_log(f"Warning no scale set for sensor <{self.name}> check config file")

    def get_voltage(self) -> float:
        """Gets the voltages of a sensor
        
        Returns:
            sensor_voltage (float): the voltage (0-5V) returned from the sensor
        """
        adc = self.daq.adcs[self.adc_id]
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
    #     print_log(f"Load Cell <{self.name}> Calibrating Tare")
    #     self.tare = 0
    #     for i in range(num_samples):
    #         sample_arr = np.append(sample_arr, self.get_force())
    #     self.set_tare(-1 * np.mean(sample_arr))
    #     print_log(f"Load Cell <{self.name}> Tare Calibrated")
