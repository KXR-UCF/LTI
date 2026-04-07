#!/usr/bin/python

# from Wanda.DataIngestion.ADC import adcmanager
from Wanda.DataIngestion.ADC.adcmanager import DAQ

import numpy as np
from questdb.ingress import Sender, Protocol, TimestampNanos

import time
import socket
import json
import requests
import threading
import queue

from datetime import datetime
from pytz import timezone

from collections import deque

import os
module_path = os.path.abspath(__file__)
module_directory = os.path.dirname(module_path)
del os

# config
DAQ_CONFIG_FILENAME = "config.yaml"
TARGET_RPS = 100
SAMPLE_INTERVAL = 1.0 / TARGET_RPS
est = timezone('US/Eastern')
HOSTNAME = socket.gethostname()

# questdb config
QDB_CONF = (
    'tcp::addr=192.168.1.32:9009;'
    'auto_flush=on;'
    'auto_flush_interval=100;'
    # 'auto_flush_rows=2;'
)

# grafana config
GRAFANA_URL = f"http://192.168.1.32:3000/api/live/push/{HOSTNAME}"
with open("grafana.key", 'r') as grafana_key_file:
    GRAFANA_TOKEN = grafana_key_file.read().strip()
    GRAFANA_HEADERS = {"Authorization": f"Bearer {GRAFANA_TOKEN}"}

# stats
stats = {
    'adc_time': deque(maxlen=100),
    'questdb_send_time': deque(maxlen=100),
    'grafana_send_time': deque(maxlen=100),
    'main_loop_time': deque(maxlen=100),
    'queue_wait': deque(maxlen=100)
}

# queues
questdb_queue = queue.Queue(1000)
grafana_queue = queue.Queue(1000)

def print_log(message:str):
    lines = message.split('\n')
    for line in lines:
        print(f"[{datetime.now(tz=est).strftime('%Y-%m-%d %H:%M:%S')}] {line}")

def questdb_worker():
    try:
        with Sender.from_conf(QDB_CONF) as sender:
            while True:
                data = questdb_queue.get()
                if data is None: 
                    break

                start = time.perf_counter()
                sender.row(
                    table_name=HOSTNAME,
                    columns=data['columns'],
                    at=data['time']
                )
                stats['questdb_send_time'].append(time.perf_counter() - start)

                questdb_queue.task_done()

    except Exception as e:
        print_log(f"QuestDB Error: {e}")


def grafana_worker():
    try:
        while True:
            data = grafana_queue.get()
            if data is None:
                break

            try:
                fields = ",".join([f"{k}={v}" for k, v in data['columns'].items()])
                payload = f"{HOSTNAME} {fields}"

                start = time.perf_counter()
                requests.post(GRAFANA_URL, data=payload, headers=GRAFANA_HEADERS, timeout=0.1)
                stats['grafana_send_time'].append(time.perf_counter() - start)

            except requests.exceptions.RequestException:
                pass # Silently ignore network timeouts so we don't spam logs
            except Exception as e:
                print_log(f"Unexpected Grafana Formatting Error: {e}")
            finally:
                grafana_queue.task_done()

    except Exception as e:
        print_log(f"Grafana Error: {e}")

# init sensors
with DAQ(DAQ_CONFIG_FILENAME) as daq:
    sensor_dict = daq.get_sensor_dict()

    # sensors = [adcmanager.Sensor(name) for name in adcmanager.config["sensors"]]
    load_cells_for_net_force = ['lc1', 'lc2', 'lc3']
    net_force_measured = any(sensor_name in load_cells_for_net_force for sensor_name in sensor_dict.keys())

    # start worker threads
    threading.Thread(target=questdb_worker, daemon=True).start()
    threading.Thread(target=grafana_worker, daemon=True).start()

    row_count = 0
    start_time = time.time()
    last_report_rows = 0
    last_report_time = time.time()

    print_log("Starting Data Ingestion")
    try:
        next_sample_time = time.time()
        while True:
            loop_start = time.perf_counter()
            # save all sensor values
            adc_start = time.perf_counter()
            columns = daq.get_all_sensor_values()

            # sum net force
            if net_force_measured:
                columns['lc_net_force'] = sum(columns.get(lc, 0) for lc in load_cells_for_net_force)
            stats['adc_time'].append(time.perf_counter() - adc_start)
            timestamp = datetime.now(tz=est)

            # send to workers
            queue_start = time.perf_counter()
            packet = {'columns': columns, 'time': timestamp}
            try:
                questdb_queue.put_nowait(packet)
                grafana_queue.put_nowait(packet)
            except queue.Full:
                print_log("Warning: Data Loss <QUEUE FULL>")
            stats['queue_wait'].append(time.perf_counter() - queue_start)

            row_count += 1
            stats['main_loop_time'].append(time.perf_counter() - loop_start)

            # report speed stats
            current_time = time.time()
            if current_time - last_report_time > 10:
                # get averages
                avg_rps = (row_count - last_report_rows) / (current_time - last_report_time)
                avg_adc = np.mean(stats['adc_time']) * 1000
                avg_questdb = np.mean(stats['questdb_send_time']) * 1000
                avg_grafana = np.mean(stats['grafana_send_time']) * 1000
                avg_queuew = np.mean(stats['queue_wait']) * 1000

                # report
                print_log(f"="*50)
                print_log(f"AVG RPS:     {avg_rps:.1f}")
                print_log(f"AVG ADC:     {avg_adc:.1f} ms")
                print_log(f"AVG QuestDB: {avg_questdb:.1f} ms")
                print_log(f"AVG Grafana: {avg_grafana:.1f} ms")
                print_log(f"AVG Queue:   {avg_queuew:.1f} ms")

                # reset last
                last_report_rows = row_count
                last_report_time = current_time

            next_sample_time += SAMPLE_INTERVAL
            sleep_time = next_sample_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print_log("Program interuppted by user")

    except Exception as e:
        print_log(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
