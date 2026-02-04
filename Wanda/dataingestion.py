#!/usr/bin/python

from ADC import adcmanager

import numpy as np
from questdb.ingress import Sender, Protocol, TimestampNanos
from datetime import datetime

import time
import socket

hostname = socket.gethostname()

conf = (
    'tcp::addr=localhost:9009;'
    'auto_flush=off;'
    # 'auto_flush_rows=1;'
)

sensors = []
for sensor_name in adcmanager.config["sensors"]:
     sensors.append(adcmanager.Sensor(sensor_name))

net_force_measured = False
load_cells_for_net_force = ['lc1', 'lc2', 'lc3']
for sensor in sensors:
    if sensor.name in load_cells_for_net_force:
        net_force_measured = True


row_count = 0
start_time = 0
last_report_time = time.time()

adc_times = []
questdb_times = []
loop_times = []

try:
    with Sender.from_conf(conf) as sender: # Allows for QuestDB insertion

        sender.row(table_name=hostname, at=datetime.now())

        # st = time.time()
        print("Connected to QuestDB")
        start_time = time.time()
        print("Sending Data")
        while True:
            loop_start = time.time()

            # get sensor values from ADC
            adc_start = time.time()
            lc_net_force = 0
            columns = {}
            for sensor in sensors:
                columns[sensor.name] = sensor.get_calibrated_value_linear()                
                if sensor.name in load_cells_for_net_force:
                    lc_net_force += columns[sensor.name]

            # if netforce load cells exist save netforce
            if net_force_measured:
                columns['lc_net_force'] = lc_net_force

            # save time to get data this iteration
            adc_times.append(time.time() - adc_start)

            # send data and time to questDB
            questdb_start = time.time()
            sender.row(
                table_name=hostname,
                columns=columns,
                at=TimestampNanos.now()
            )
            # flush row to questdb
            sender.flush()
            row_count += 1
            questdb_times.append(time.time() - questdb_start)
            
            # get time stats
            current_time = time.time()
            if current_time - last_report_time > 1:
                total_RPS = row_count / (current_time - start_time)
                print(f"Rate: {total_RPS:.1f} RPS")
                last_report_time = current_time
            
            loop_times.append(time.time() - loop_start)


except KeyboardInterrupt:
    print("Program interuppted by user")

except Exception as e:
    print(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()

finally:
     total_elapsed = time.time() - start_time
     if total_elapsed > 0 and row_count > 0:
         final_RPS = row_count / total_elapsed
         avg_adc = np.mean(adc_times)
         avg_questdb = np.mean(questdb_times)
         avg_loop = np.mean(loop_times)

         print(f"{'='*60}")
         print(f"{'Total Samples':<15} {row_count}")
         print(f"{'Total Time':<15} {total_elapsed:.0f} s")
         print(f"{'Total Rate:':<15} {final_RPS:.0f} RPS")
         print(f"{'='*60}")
         print(f"{'ADC overhead:':<15} {100*avg_adc/avg_loop:.0f}%")
         print(f"{'QuestDB overhead:':<15} {100*avg_questdb/avg_loop:.0f}%")
         print(f"{'My overhead:':<15} {100*(1-(avg_adc+avg_questdb)/avg_loop):.0f}%")
         print(f"{'='*60}")


