# COSMO - Launch Test & Infrastructure

COSMO is the uprange control system. It reads commands from the serial control
device and forwards them to the WANDA controller. COSMO does not read or write
telemetry data; Grafana is the live telemetry interface.

## Structure

| File/Folder | Description |
|---|---|
| [`socket_client.py`](socket_client.py) | Reads `/dev/ttyACM0` and sends commands to WANDA on port `9600` |
| [`Systemd/`](Systemd/) | Service files for COSMO processes |
| [`cosmo_status_server.py`](cosmo_status_server.py) | COSMO status dashboard |
| [`ingest_telemetry.py`](ingest_telemetry.py) | Development-only QuestDB sample-data generator |
| [`Telemetry_visualization/`](Telemetry_visualization/) | Deprecated custom telemetry frontend and backend |

---

## Control Configuration

Before enabling the COSMO control bridge, verify these values:

| Setting | Location | Checked-in value |
|---|---|---|
| WANDA controller address | `socket_client.py` | `192.168.1.30:9600` |
| Serial control device | `socket_client.py` | `/dev/ttyACM0` |
| Relay mapping | `Wanda/Controls/config.yaml` | Must match the physical stand |

The current COSMO service units expect user `kxr` and paths under
`/home/kxr/LTI-25/Cosmo`. Update the service files if the deployed location is
different.

---

## Deprecated Telemetry Visualization

`Telemetry_visualization/` contains the earlier custom TypeScript backend and
Vite frontend. It is retained for reference only; Grafana is the supported live
telemetry interface.

---

## Testing with Sample Data

`ingest_telemetry.py` generates sample QuestDB telemetry for development. It
creates or truncates its test tables, so do not run it against a production
database.

```bash
cd Cosmo
python3 ingest_telemetry.py 30
```
