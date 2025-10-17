#!/usr/bin/python

from ADC import adcmanager

import numpy as np
from questdb.ingress import Sender, Protocol
from datetime import datetime

import json
import time


rows = [
    "cell1_force",
    "cell2_force",
    "cell3_force",
    "net_force",
    "pressure_pt1",
    "pressure_pt2",
    "pressure_pt3",
    "pressure_pt4",
    "pressure_pt5",
    "pressure_pt6",
    "weight_load_cell",
    "chamber_temp",
    "nozzle_temp"
]

conf = (
    'http::addr=localhost:9000;'
    'username=admin;'
    'password=quest;'
    'auto_flush=on;'
    'auto_flush_rows=1;'
    # 'auto_flush_interval=1000;'
    )

SWITCH_STATE_FILENAME = "switch_states.json"
CONFIG_FILE_NAME = adcmanager.CONFIG_FILE_NAME

load_cell_group1 = adcmanager.LoadCellGroup()
load_cell_group1.add_all_from_config()
load_cell_group1.calibrate_tares(num_samples=100)
load_cell_group1.print_load_cells_information()


try:

    with Sender.from_conf(conf) as sender: # Allows for QuestDB insertion
        # st = time.time()
        print("Connected to QuestDB")

        # enable_fire = False
        # while not enable_fire:
        #     # read state file
        #     try:
        #         with open(SWITCH_STATE_FILENAME, 'r') as f:
        #             switch_states = json.load(f)
        #         # check enable fire state
        #         if "enable_fire" in switch_states.keys():
        #             enable_fire = switch_states["enable_fire"]
        #         time.sleep(0.05)
        #     except FileNotFoundError:
        #         print("Waiting for switch state file")

        print("Sending Data")
        # st = time.time()
        while True:

            # get load cell values
            load_cell_group1_forces = load_cell_group1.get_all_forces()
            load_cell_group1_netForce = np.sum(load_cell_group1_forces)

            # send data and time to questDB
            sender.row(
                'telemetry_data',
                columns = {
                    'cell1_force': float(load_cell_group1_forces[0]),
                    'cell2_force': float(load_cell_group1_forces[1]),
                    'cell3_force': float(load_cell_group1_forces[2]),
                    'net_force': float(load_cell_group1_netForce)
                },
                at=datetime.now()
            )
            #
            # if time.time() - st >= 7:
            #     break

                # print('sent')

except KeyboardInterrupt:
    print("Program interuppted by user")

# except Exception as e:
#     print(f"Unexpected error: {e}")
#     GPIO.cleanup()
#     print("\r\nProgram end     ")


