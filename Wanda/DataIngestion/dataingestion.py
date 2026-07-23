#!/usr/bin/python

# from Wanda.DataIngestion.ADC import adcmanager
from ADC.adcmanager import DAQ

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

import statistics
from collections import deque

import os
module_path = os.path.abspath(__file__)
module_directory = os.path.dirname(module_path)

# config
DAQ_CONFIG_FILENAME = os.path.join(module_directory, "config.yaml")
TARGET_RPS = 100
SAMPLE_INTERVAL = 1.0 / TARGET_RPS

# QuestDB batches raw rows internally.  It flushes after this many rows, or
# after this many milliseconds have elapsed when the next row is appended.
QUESTDB_AUTO_FLUSH_ROWS = 250
QUESTDB_AUTO_FLUSH_INTERVAL_MS = 1000
QUESTDB_QUEUE_SIZE = 2048

# Grafana is a display stream, not the raw acquisition archive.  Collect all
# samples received during each interval, publish their per-field median, and
# retain the unfiltered stream in QuestDB.
GRAFANA_SEND_HZ = 20
GRAFANA_WINDOW_SECONDS = 1.0 / GRAFANA_SEND_HZ
GRAFANA_QUEUE_SIZE = 256

# Optional second smoothing stage, applied after the window median.  Leave it
# disabled for the lowest-latency filtered display.
GRAFANA_EMA_ENABLED = False
GRAFANA_EMA_STRENGTH = 0.25


est = timezone('US/Eastern')
HOSTNAME = socket.gethostname()

# questdb config
QDB_CONF = (
    'http::addr=192.168.1.32:9000;'
    'auto_flush=on;'
    f'auto_flush_rows={QUESTDB_AUTO_FLUSH_ROWS};'
    f'auto_flush_interval={QUESTDB_AUTO_FLUSH_INTERVAL_MS};'
)

# grafana config
GRAFANA_URL = f"http://192.168.1.32:3000/api/live/push/{HOSTNAME}"
try:
    with open(os.path.join(module_directory, "grafana.key"), 'r') as grafana_key_file:
        GRAFANA_TOKEN = grafana_key_file.read().strip()
        GRAFANA_HEADERS = {"Authorization": f"Bearer {GRAFANA_TOKEN}"}
        GRAFANA_ENABLED = True
except FileNotFoundError:
    print("Warning: grafana.key not found. Grafana streaming disabled.")
    GRAFANA_ENABLED = False
    pass

# stats
stats = {
    'adc_time': deque(maxlen=100),
    'questdb_send_time': deque(maxlen=100),
    'grafana_send_time': deque(maxlen=100),
    'main_loop_time': deque(maxlen=100),
    'queue_wait': deque(maxlen=100)
}

# queues
questdb_queue = queue.Queue(QUESTDB_QUEUE_SIZE)
grafana_queue = queue.Queue(GRAFANA_QUEUE_SIZE)

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
    previous_filtered_columns = {}
    window_samples = []
    next_publish_time = time.monotonic() + GRAFANA_WINDOW_SECONDS

    def filter_window(samples):
        """Return the median of every field represented in this time window."""
        fields = set().union(*(sample.keys() for sample in samples))
        median_columns = {
            field: statistics.median(
                sample[field] for sample in samples if field in sample
            )
            for field in fields
        }

        if not GRAFANA_EMA_ENABLED:
            return median_columns

        filtered_columns = {}
        for field, value in median_columns.items():
            previous_value = previous_filtered_columns.get(field, value)
            filtered_columns[field] = (
                GRAFANA_EMA_STRENGTH * value
                + (1 - GRAFANA_EMA_STRENGTH) * previous_value
            )
        previous_filtered_columns.update(filtered_columns)
        return filtered_columns

    def publish(columns):
        fields = ",".join([f"{key}={value}" for key, value in columns.items()])
        payload = f"telemetry {fields}"

        try:
            start = time.perf_counter()
            requests.post(GRAFANA_URL, data=payload, headers=GRAFANA_HEADERS, timeout=0.1)
            stats['grafana_send_time'].append(time.perf_counter() - start)
        except requests.exceptions.RequestException:
            pass # Silently ignore network timeouts so we don't spam logs
        except Exception as e:
            print_log(f"Unexpected Grafana Formatting Error: {e}")

    try:
        while True:
            now = time.monotonic()
            if now >= next_publish_time:
                if window_samples:
                    publish(columns=filter_window(window_samples))
                    window_samples.clear()

                # Keep a fixed publish cadence even if a slow POST skipped one
                # or more intervals.
                now = time.monotonic()
                while next_publish_time <= now:
                    next_publish_time += GRAFANA_WINDOW_SECONDS
                continue

            timeout = next_publish_time - now
            try:
                data = grafana_queue.get(timeout=timeout)
            except queue.Empty:
                # The next iteration gives publishing precedence over dequeuing
                # even when samples arrive continuously.
                continue

            if data is None:
                break

            window_samples.append(data['columns'])
            # The sample is now retained by window_samples, so release the
            # queue slot before the next Grafana HTTP request.
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
    if GRAFANA_ENABLED:
        threading.Thread(target=grafana_worker, daemon=True).start()
    else:
        print_log("Warning: grafana.key not found. Grafana streaming disabled.")

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
            except queue.Full:
                if row_count % TARGET_RPS == 0:
                    print_log("Warning: Data Loss <QUESTDB QUEUE FULL>")

            try:    
                if GRAFANA_ENABLED:
                    grafana_queue.put_nowait(packet)
            except queue.Full:
                if row_count % TARGET_RPS == 0:
                    print_log("Warning: Data Loss <GRAFANA QUEUE FULL>")

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
                if GRAFANA_ENABLED:
                    avg_grafana = np.mean(stats['grafana_send_time']) * 1000
                avg_queuew = np.mean(stats['queue_wait']) * 1000

                # report
                print_log(f"="*50)
                print_log(f"AVG RPS:     {avg_rps:.1f}")
                print_log(f"AVG ADC:     {avg_adc:.1f} ms")
                print_log(f"AVG QuestDB: {avg_questdb:.1f} ms")
                if GRAFANA_ENABLED:
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
