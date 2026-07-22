# WANDA DAQ & CONTROLS

WANDA is the downrange system for KXR engine tests. The DAQ side reads sensor
data from the ADS1256 Pi Hats and sends it to QuestDB and Grafana Live. The
controls side receives commands from COSMO and actuates the appropriate relays.

## Structure

| File/Folder | Description |
|---|---|
| [`DataIngestion/`](./DataIngestion/) | Retrieves sensor data and sends it to QuestDB and Grafana Live |
| [`Controls/`](./Controls/) | Receives control commands from COSMO and actuates relays |
| [`Systemd/`](./Systemd/) | Service files for WANDA processes |
| [`wanda_status_server.py`](./wanda_status_server.py) | Flask dashboard for monitoring and managing a WANDA Pi |
| [`Scripts/wanda_pi_setup.sh`](./Scripts/wanda_pi_setup.sh) | Sets up a new WANDA Pi |

---

## WANDA Dashboards

The WANDA dashboard runs on each WANDA Pi. It can monitor services and system
health, edit configuration files, and export logs.

Connect to the Pi's access point or the KXR network, then open
`http://<PI_IP_ADDRESS>:5000` in a web browser.

| Pi | IP Address |
|---|---|
| WANDA1 | `192.168.1.30` |
| WANDA2 | `192.168.1.31` |
| WANDA3 | `192.168.1.32` |

---

## System Setup

The WANDA service files are written for the `lti` user and expect the repository
at `/home/lti/Wanda`.

```bash
cd /home/lti/Wanda
bash Scripts/wanda_pi_setup.sh
```

The setup script installs dependencies, creates QuestDB and Grafana, configures
SPI, installs the service units, and enables the WANDA dashboard. Run it with
`--skip-grafana` on a Pi that is not the designated Grafana host.

Choose the remaining services by Pi role. In particular, only one Pi should run
the controller socket service, QuestDB, or Grafana. See [`Systemd/README.md`](Systemd/README.md)
for service roles and commands.

---

## Notes

- Sensor channels and calibration are configured in [`DataIngestion/config.yaml`](DataIngestion/config.yaml).
- Relay names and switch mappings are configured in [`Controls/config.yaml`](Controls/config.yaml).
- Grafana requires a service-account token in the applicable `grafana.key` files.
