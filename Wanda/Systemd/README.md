# WANDA systemd services

This directory contains systemd unit files for WANDA services. Use systemd to
start services at boot, recover them after failures, and inspect their logs.

## Service roles

| Unit | Run on | Purpose |
| --- | --- | --- |
| [controller_socket.service](controller_socket.service) | One WANDA Pi only | Receives control commands and coordinates relay control |
| [worker_socket.service](worker_socket.service) | Relay Pi that is not the controller | Connects to the controller and performs relay work |
| [dataingestion.service](dataingestion.service) | Each Pi with sensors | Runs the ADC-to-QuestDB/Grafana ingestion loop |
| [questdb.service](questdb.service) | One host only | Runs the QuestDB Docker container |
| [wanda_status_server.service](wanda_status_server.service) | Each WANDA Pi | Runs the local management dashboard |
| [grafana.service](grafana.service) | One host | Runs the Grafana container created by `Scripts/wanda_grafana_setup.sh` |
| [lti-assets.service](lti-assets.service) | As required | Manages LTI assets service |

Do not enable both the controller and worker socket services on the same Pi
unless the deployment is intentionally designed for that arrangement.

## Install or update units

The units are written for the `lti` user and `/home/lti/Wanda` paths. Update the
unit files first if your installation uses a different user or location.

```bash
cd /path/to/LTI/Wanda/Systemd
sudo cp *.service /etc/systemd/system/
sudo systemctl daemon-reload
```

Enable and start only the units appropriate to the Pi's role:

```bash
sudo systemctl enable --now dataingestion.service
sudo systemctl status dataingestion.service
```

## Common operations

```bash
sudo systemctl start <service>.service
sudo systemctl stop <service>.service
sudo systemctl restart <service>.service
sudo systemctl disable <service>.service
sudo journalctl -u <service>.service -f
```

After editing a unit file, always run `sudo systemctl daemon-reload` before
restarting its service.
