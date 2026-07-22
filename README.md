<div align="center">
  <img src="https://github.com/user-attachments/assets/dfb9ba20-90f2-4d87-a80b-ac4135f498d7" alt="LTI Logo" width="300"/>
  
  <h1>LTI - Launch &amp; Test Infrastructure</h1>
</div>

LTI is the KXR team responsible for launch and test infrastructure. This
repository contains the software and hardware files used by the WANDA and COSMO
systems.

## System Overview

| System | Location | Description |
|--------|----------|-------------|
| **WANDA** | [`Wanda/`](Wanda/README.md) | Runs downrange on Raspberry Pis. Handles data acquisition, relay control, QuestDB, and Grafana publishing. |
| **COSMO** | [`Cosmo/`](Cosmo/README.md) | Runs at the uprange control station. Sends control commands to WANDA through the serial-control bridge. |

---

## Repository Structure

```text
├── Wanda/
│   ├── DataIngestion/       # ADS1256 acquisition; sends sensor data to QuestDB and Grafana
│   ├── Controls/            # Controller/worker socket services and relay mapping
│   ├── Systemd/             # Service files for WANDA processes
│   ├── Scripts/             # WANDA Pi, QuestDB, and Grafana setup scripts
│   ├── wanda_status_server.py
│
├── Cosmo/
│   ├── socket_client.py     # Serial command bridge to WANDA
│   ├── Systemd/             # Service files for COSMO processes
│   └── Telemetry_visualization/ # Deprecated custom telemetry frontend/backend
│
└── archive/                 # Historical code
```

---

## Architecture

### Controls

1. **Commands:** COSMO sends commands to the WANDA controller over the local network.
2. **Actuation:** WANDA switches the appropriate local or worker-Pi relays.
3. **State:** WANDA publishes switch and relay state to Grafana Live and records switch state in QuestDB.

### Data Acquisition

1. **Data Ingestion:** WANDA reads sensors from the KXR ADC hats.
2. **Storage:** WANDA writes sensor data to the locally hosted QuestDB container.
3. **Visualization:** WANDA sends live sensor data directly to Grafana Live. Grafana is the supported telemetry interface.

COSMO does not read or write telemetry data. The custom frontend in
`Cosmo/Telemetry_visualization/` is deprecated and retained only as reference.

---

## Helpful Resources

+ See [`Wanda/`](Wanda/README.md) for WANDA setup and service information.
+ See [`Cosmo/`](Cosmo/README.md) for COSMO control-bridge information.
+ The test stand uses custom KXR Raspberry Pi hats built around the ADS1256 24-bit ADC. Hardware design files (KiCad schematics, gerbers, BOM) are located in [`Wanda/DataIngestion/ADC/Pi Hat/`](Wanda/DataIngestion/ADC/Pi%20Hat/).
