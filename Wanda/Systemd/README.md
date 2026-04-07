# Systemd

This folder contains several systemd service files to be able to manage DAQ and Controls services through systemd.

Systemd is a software suite built into many Linux operating systems. The Raspbian OS uses systemd to automate service on the system.

Systemd services can be managed in the terminal:
```bash
sudo systemctl <command> <service>
```
Systemd services have 5 main commands we use:
| Command | Description |
|---|---|
| `start` | Starts the service |
| `stop` | Stops the service |
| `restart` | Restarts the service |
| `enable` | Configures the service to automatically start at boot |
| `disable` | Configures the service to not start automatically at boot |

## Services

| Service | Description |
|---|---|
| [`controller_socket.service`](controller_socket.service) | Handles the controls socket service. Will auto restart on failure. (**Only one WANDA Pi should have this enabled**) |
| [`worker_socket.service`](worker_socket.service) | Manages the start, stop, and restart of the worker socket client. Should restart upon failure. Ex: Controller socket server not running |
| [`dataingestion.service`](dataingestion.service) | Manages the start and stop of the data ingestion python script. Will auto restart on failure. Ex: Database not running |
| [`questdb.service`](questdb.service) | Manages the start and stop of the QuestDB docker container |
| [`status_server.service`](status_server.service) | Manages the start and stop of the WANDA dashboards. Should be set to start on start up of the system. |

---

## Setup

1. For systemd to see the services, they must be moved to the systemd services directory: `/etc/system/systemd/`.

```bash
sudo mv * /etc/system/systemd
```

2. Once the files are there, the systemd configuration must be reloaded. That can be done with this command: 

```bash
sudo systemctl daemon-reload
```

3. Then each required service on the Pi must be configured. Not every service will run on every Pi.

- [`controller_socket.service`](controller_socket.service)  
This service must only be enabled and ran on one Pi. The other Pi's and COSMO will connect to this service. **Make sure the workers and COSMO are set up to connect to this Pi.**

- [worker_socket.service](worker_socket.service)  
This service should enabled and ran on any Pis that need to control relays but is not the controller Pi or running the controller server.

- [dataingestion.service](dataingestion.service)  
This service should be enabled and ran on every Pi that has sensors connected.

- [questdb.service](questdb.service)  
This service only needs to be enabled and ran on a single Pi. **Make sure the data ingestion files on all Pis are configured to send data to this database IP address.**

- [status_server.service](status_server.service)  
This service should be enabled and ran on every Pi. This service is required to be able to manage other services through the dashboards.

For each service that needs to run on the Pi run:
```bash
sudo systemctl enable <service>
sudo systemctl restart <service>
```
