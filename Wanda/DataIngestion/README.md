# Data Ingestion

This folder contains the data ingestion code for WANDA DAQ. The code reads the sensor data from the ADS1256 Pi Hats and sends it to QuestDB for storage and Grafana Live for live telemetry dashboards.

## Files

| File | Description |
|---|---|
| `dataingestion.py` | Reads all sensors and sends data to QuestDB and Grafana|
| `config.yaml` | ADC configuration file (See [`ADC README`](ADC#config-file) for configuration requirements and formatting) |
| `ADC/` | Contains ADS1256 library and DAQ manager (See [`ADC/README.md`](ADC/README.md)) |

---

## dataingestion.py

Runs the primary data acquisition loop on the Raspberry Pis. Reads all sensors configured with the `DAQ` class and sends the data to two separate threads. One thread handles QuestDB ingestions while the other thread handles streaming data to Grafana Live.

### Configuration

At the top of `dataingestions.py`, several configuration constants can be adjusted:

| Config Const | Default | Description |
|---|---|---|
| `DAQ_CONFIG_FILENAME` | `"config.yaml"` | Relative path to config YAML file to be passed to `DAQ` class |
| `TARGET_RPS` | `100` | Target sample rate of all sensors in Hz |
| `QDB_CONF` | `http::addr=192.168.1.32:9000` | Questdb configuration string for QuestDB library |
| `GRAFANA_URL` | `http://192.168.1.32:3000/api/live/push/{HOSTNAME}` | Grafana Live url to push data to. |

Grafana requires a service token to be able to send data to Grafana Live. This key is read from a file named `grafana.key` in the same directory as the `dataingestion.py` file. This file must exist for grafana to work and must only contain the raw token value.

### Internal Calculations

The data ingestion code also creates another column in the data base called `lc_net_force`. This column is the sum of the load cells specified in `load_cells_for_net_force`. This is used to measure the net thrust distributed among the three thrust load cells.

### Usage

```bash
python dataingestion.py
```

This process is also managed and ran by systemd - see [`../Systemd/dataingestion.service`](../Systemd/dataingestion.service). To run as a service:
 
```bash
sudo systemctl start dataingestion
sudo systemctl enable dataingestion  # start on boot
sudo journalctl -u dataingestion -f  # follow logs
```

Performace information is printed to the console/logs every 10 seconds. The performance information contains the average latency for the ADC, QuestDB, and Grafana. In the case of a network bottleneck, the queues for the threads may fill in which case a warning will be printed to the console/log (`Warning: Data Loss <{service} QUEUE FULL>`).

---

## Config Files

The configuration file is a YAML file that is used by the `DAQ` class in `ADC/adcmanager.py`. See [`ADC/README.md`](ADC/README.md) for full documentation of the config format.


---

## Dependencies
 
All python dependencies are listed in [`../requirements.txt`](../requirements.txt).

Steps for dependency installation:
```bash
# Check python version is at least 3.11.0
python3 --version

# Create and enter virtual enviroment
python3 -m venv venv
source venv/bin/activate

# install `swig` and `libgpio-dev`
sudo apt update
sudo apt install swig liblgpio-dev

# install required python packages
pip install -r requirements.txt
```
 
## Helpful Resources
 
- [QuestDB Python Client](https://py-questdb-client.readthedocs.io/)
- [Grafana Live HTTP API](https://grafana.com/docs/grafana/latest/setup-grafana/set-up-grafana-live/)