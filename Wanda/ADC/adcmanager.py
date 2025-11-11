#!/usr/bin/env python3
# Styling: PEP 8

"""KXR file for handling sensors/transducers connected to the KXR ADS1256 Pi hat"""

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
_ADCs = []
for adc in ENABLED_ADCS:
    rst_pin = config[f"ADC{adc}"]["RST_PIN"]
    cs_pin = config[f"ADC{adc}"]["CS_PIN"]
    drdy_pin = config[f"ADC{adc}"]["DRDY_PIN"]

    gain = config[f"ADC{adc}"]["gain"]
    data_rate = config[f"ADC{adc}"]["data_rate"]

    new_ADC = ADS1256.ADS1256(rst_pin, cs_pin, drdy_pin)
    new_ADC.init()
    new_ADC.configADC(ADS1256.GAIN_E[gain], ADS1256.DRATE_E[data_rate])
    _ADCs.append(new_ADC)
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
            # might raise some exception here

    def get_voltage(self) -> float:
        """Gets the voltages of a sensor
        
        Returns:
            sensor_voltage (float): the voltage (0-5V) returned from the sensor
        """
        adc = _ADCs[self.adc_id - 1]
        sensor_value = adc.getChannelValue(self.channel_id)   # gets the sensor value
        sensor_voltage = sensor_value * 5.0 / 0x7fffff        # converts the digital value to volts
        return sensor_voltage


class LoadCell(Sensor):
    """Child class of Sensor, handles extra functions for load cells"""
    sensor_type = "load_cells"

    def __init__(self, sensor_name):
        super().__init__(sensor_name)
        self.tare = config["devices"][LoadCell.sensor_type][sensor_name]["tare"]
        if self.tare == None:
            self.tare = 0
            # print(f"Warning no tare set for loadcell <{self.name}> check config file")

        self.scale = config["devices"][LoadCell.sensor_type][sensor_name]["scale"]
        if self.scale == None:
            self.scale = 1
            print(f"Warning no scale set for loadcell <{self.name}> check config file")

    def set_tare(self, tare: float):
        """Set tare and write it to the config file
        
        Args:
            tare (float): the tare of this load cell to be set and written to the config file
        """
        self.tare = tare
        self.write_tare_to_config()

    def calibrate_tare(self, num_samples: int):
        """Calibrates the tare of the load cell from several samples
        
        Args:
            num_samples (int): number of samples to average for the tare
        """
        sample_arr = np.array([])
        print(f"Load Cell <{self.name}> Calibrating Tare")
        for i in range(num_samples):
            sample_arr = np.append(sample_arr, self.get_voltage())
        self.set_tare(-1 * np.mean(sample_arr))
        print(f"Load Cell <{self.name}> Tare Calibrated")

    def write_tare_to_config(self):
        """Writes the tare to the config file"""
        config["devices"][LoadCell.sensor_type][self.name]["tare"] = float(self.tare)
        with open(CONFIG_FILE_NAME, 'w') as file:
            yaml.safe_dump(config, file, default_flow_style=False, sort_keys=False)
        
    def get_force(self) -> float:
        """Gets the force using the tare and scale from the config file

        Returns:
            force (float): the force applied to the load cell
        """
        force = (self.get_voltage() + self.tare) * self.scale
        return force


class PressureTransducer(Sensor):
    sensor_type = "pressure_transducers"

    def __init__(self, sensor_name):
        super().__init__(sensor_name)


class ThermoCouple(Sensor):
    sensor_type = "thermo_couples"

    def __init__(self, sensor_name):
        super().__init__(sensor_name)


class SensorGroup:
    """Handles operations between multiple sensors"""

    def __init__(self):
        self.sensors = []

    def get_sensor(self, sensor_name: str) -> type[Sensor]:
        """Returns sensor of sensor_name
        
        Args:
            sensor_name (str): the name of the sensor in the config file
        
        Returns:
            sensor (type[Sensor]): an object of class Sensor or a class 
                that inherits from Sensor with the name sensor_name
        """
        for sensor in self.sensors:
            if sensor_name is sensor.name:
                return sensor

    def add_sensor(self, sensor: Sensor):
        """Adds sensor to the sensor group
        
        Args:
            sensor (Sensor): sensor to add to the sensor group
        """
        self.sensors.append(sensor)

    def add_sensor_from_list(self, sensor_names: list, sensor_class: type[Sensor] = Sensor):
        """Adds sensors to the group from at list
        
        Args:
            sensor_names (list): a list of sensor names from the config file
            sensor_class (type[Sensor], optional): The sensor class or subclass to 
                instantiate for each sensor name. Accepts any class that inherits 
                from Sensor. Defaults to Sensor.
        """
        for sensor_name in sensor_names:
            self.sensors.append(sensor_class(sensor_name))

    def add_all_from_config(self, sensor_class: type[Sensor] = Sensor):
        try:
            for sensor_name in config["devices"][sensor_class.sensor_type]:
                self.sensors.append(sensor_class(sensor_name))
        except KeyError:
            print(f"Sensor type <{sensor_class.sensor_type}> not in config file")

    def remove_sensor(self, sensor_name: str):
        """Remove sensor with name sensor_name from group
        
        Args:
            sensor_name (str): The name of the sensor to remove. 
                The name should match one that is in the config file
        """
        for sensor in self.sensors:
            if sensor_name is sensor.name:
                self.sensors.remove(sensor)

    def get_all_voltages(self) -> list:
        """Gets the voltages of each load cell
        
        Returns:
            voltages (list): A list of the voltages in order of the load cells
        """
        voltages = []
        for sensor in self.sensors:
            voltages.append(sensor.get_voltage())

        return voltages


class LoadCellGroup(SensorGroup):
    """Uses the ADCs to manage all the attached load cells"""
    
    def __init__(self):
        super().__init__()
        
    def add_sensor_from_list(self, load_cell_names: list):
        """Adds load cells to the group from a list
        
        Args:
            load_cell_names (list): a list of load cell names from the config file
        """
        super().add_sensor_from_list(sensor_names=load_cell_names, sensor_type=LoadCell)

    def print_load_cells_information(self):
        print(f"Load Cells:")
        for load_cell in self.sensors:
            print(f"\tADC: {load_cell.adc_id}\
                    \tChannel: {load_cell.channel_id}\
                    \tTare: {load_cell.tare}\
                    \tScale: {load_cell.scale}")
        
    def add_all_from_config(self, sensor_class: type[Sensor] = Sensor):
        super().add_all_from_config(sensor_class=LoadCell)

    def get_all_forces(self) -> list:
        """Gets all the forces on each load cell
        
        Returns:
            forces (list): A list of the forces in order of the load cells
        """
        forces = []
        for sensor in self.sensors:
            forces.append(sensor.get_force())
        return forces

    def calibrate_tares(self, num_samples):
        for load_cell in self.sensors:
            load_cell.calibrate_tare(num_samples)
