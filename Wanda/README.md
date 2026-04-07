# WANDA DAQ & CONTROLS

This folder contains all code on the WANDA Raspberry Pis. WANDA (not to be confused with WANDA) is a data acquisition (DAQ) and remote control system designed for use during KXR engine tests. The DAQ side read high-frequency sensor readings (Load Cells, Pressure Transducers, Thermocouples, etc.) and ingests that data realtime into an onboard database. The controls side handles actuation of relays via socket communication with COSMO.

# Structure

The different systems of the WANDA DAQ & CONTROLS system is split up into separate folders.

| File/Folder | Description |
|---|---|
| [`DataIngestion/`](./DataIngestion/) | Contains all code related to retrieving, sending, and storing realtime sensor data |
| [`Controls/`](./Controls/) | Contains all code related to recieving and processing controls commands from COSMO and actuating the proper relays |
| [`Questdb/`](./Questdb/) | Contains scripts to create QuestDB docker containers |
| [`Systemd/`](./Systemd/) | Contains systemd service files to manage WANDA services |
| [`status_server.py`](./status_server.py) | Runs a small Flask server to assist in managing the WANDA system without the use of a terminal |
| [`setupPi.sh`](./setupPi.sh) | Setup script to setup a new Raspberry Pi with the WANDA system |

---

## WANDA Dashboards

The WANDA Dashboards run on each WANDA Pi. These dashboards are used to monitor and manage each Pi individually. Though the dashboard, services can be controled, config files can be edited, log files can be exported, and system health can be monitored.

To access the dashboard connect to either the Pi's self hosted access point, or connect to the KXR network. Navigate to `http://<PI_IP_ADDRESS>:5000` in your web browser.

Each WANDA Pi has a static IP address:
| Pi | IP Address |
|---|---|
| WANDA1 | 192.168.1.30 |
| WANDA2 | 192.168.1.31 |
| WANDA3 | 192.168.1.32 |

---


## System Setup

The Wanda folder is designed to run under the `lti` user account on the Raspberry Pis in the `~/Production` directory.

```bash
cd ~/Production
chmod +x setupPi.sh
./setupPi.sh
```

---

## Notes

The QuestDB dashboard is accessible at http://192.168.1.7:9000
