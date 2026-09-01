<div align="center">
  <img src="https://github.com/user-attachments/assets/ee2b6c4e-f0bf-4a74-a6a1-2cd7301f3402" alt="LTI Logo" width="300"/>
  
  <h1>LTI - Launch &amp; Test Infrastructure</h1>
</div>

LTI is the KXR team responsible for launch and test infrastructure. This
repository contains the software and hardware files used by the WANDA and COSMO
systems.

## System Overview

| System | Location | Deascription |
|--------|----------|-------------|
| **TBA** | [`TBA/`](TBA/README.md) | Runs downrange on Raspberry Pis. Handles relay control. |
| **TBA** | [`TBA/`](TBA/README.md) | Runs at the uprange control station. Sends control commands to TBA. |

---

## Repository Structure

```text
TBA
```

---

## Architecture

TBA

---

## Helpful Resources

+ The test stand uses custom KXR Raspberry Pi hats built around the ADS1256 24-bit ADC. Hardware design files (KiCad schematics, gerbers, BOM) are located in [KXR-UCF/ADS1256-Pi-Hat](https://github.com/KXR-UCF/ADS1256-Pi-Hat).
