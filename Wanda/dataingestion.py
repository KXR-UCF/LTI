#!/usr/bin/python

from ADC import adcmanager

import numpy as np
from questdb.ingress import Sender, Protocol, TimestampNanos

import time
import socket

from datetime import datetime
from pytz import timezone
est = timezone('US/Eastern')

def print_log(message:str):
    lines = message.split('\n')
    for line in lines:
        print(f"[{datetime.now(tz=est).strftime('%Y-%m-%d %H:%M:%S')}] {line}")

hostname = socket.gethostname()

TARGET_RPS = 100
SAMPLE_INTERVAL = 1.0 / TARGET_RPS

conf = (
    'tcp::addr=192.168.1.32:9009;'
    'auto_flush=on;'
    'auto_flush_interval=100;'
    # 'auto_flush_rows=2;'
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
        print_log("Connected to QuestDB")
        start_time = time.time()
        next_sample_time = start_time
        print_log("Sending Data")
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
                at=datetime.now(tz=est)
            )
            # flush row to questdb
            # sender.flush()
            row_count += 1
            questdb_times.append(time.time() - questdb_start)
            
            # get time stats
            current_time = time.time()
            if current_time - last_report_time > 20:
                total_RPS = row_count / (current_time - start_time)
                print_log(f"Rate: {total_RPS:.1f} RPS")
                last_report_time = current_time
            
            # Rate limiting
            next_sample_time += SAMPLE_INTERVAL
            sleep_time = next_sample_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)
            
            loop_times.append(time.time() - loop_start)


except KeyboardInterrupt:
    print_log("Program interuppted by user")

except Exception as e:
    print_log(f"Unexpected error: {e}")
    import traceback
    traceback.print_exc()

finally:
     total_elapsed = time.time() - start_time
     if total_elapsed > 0 and row_count > 0:
         final_RPS = row_count / total_elapsed
         avg_adc = np.mean(adc_times)
         avg_questdb = np.mean(questdb_times)
         avg_loop = np.mean(loop_times)

         print_log(f"{'='*60}")
         print_log(f"{'Total Samples':<15} {row_count}")
         print_log(f"{'Total Time':<15} {total_elapsed:.0f} s")
         print_log(f"{'Total Rate:':<15} {final_RPS:.0f} RPS")
         print_log(f"{'='*60}")
         print_log(f"{'ADC overhead:':<15} {100*avg_adc/avg_loop:.0f}%")
         print_log(f"{'QuestDB overhead:':<15} {100*avg_questdb/avg_loop:.0f}%")
         print_log(f"{'My overhead:':<15} {100*(1-(avg_adc+avg_questdb)/avg_loop):.0f}%")
         print_log(f"{'='*60}")
