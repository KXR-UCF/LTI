# ADS1256 Pi Hat

PCB designed and documented by [Ethan Voth](https://github.com/evoth)

A simple PCB to interface up to four load cells with a Raspberry Pi using [this HiLetgo ADS1256 board](https://www.amazon.com/HiLetgo-ADS1256-Acquisition-Precision-Collecting/dp/B09KGXC44Q) and four [JST S4B-XH-A connectors](https://www.digikey.com/en/products/detail/jst-sales-america-inc/S4B-XH-A/1651041). Includes solder bridges to select separate data lines (DRDY, CS, PDWN) when connecting two boards at the same time.

This board will be used to facilitate high-speed data acquisition for rocket motor static fires, interfacing with multiple load cells and possibly a pressure transducer (PT). Data acquisition is a key responsibility of the Knights Experimental Rocketry (KXR) Launch Test Infrastructure (LTI) team, which provides test stands and data for multiple rocketry teams within KXR.

Since this is the third PCB I've ever designed (I'm a CS major with only self-taught electronics knowledge), there are certainly improvements to be made. Ground plane, separate analog ground, sources of noise, and filtering for analog lines would be good areas of learning for a future version of this board.

## Files

The KiCad project (including schematic, board, and fabrication files) can be found in the `KXR_pi_hat_v0.2` directory.

(Ignore `KXR_pi_hat_v0.1`, which was an... interesting idea to cram 5 independent HX711 modules onto 2 boards with a single design.)

## Parts

### [HiLetgo ADS1256 Board](https://www.amazon.com/HiLetgo-ADS1256-Acquisition-Precision-Collecting/dp/B09KGXC44Q)

![Front and back view of HiLetgo ADS1256 board](images/HiLetgo_ADS1256.jpg)

This HiLetgo module contains support components for the [ADS1256 ADC](https://www.ti.com/lit/ds/symlink/ads1255.pdf?ts=1750027613648) and breaks out the analog inputs and data lines. Since we only need one or two of these for our application, it made more sense to use a ready-made module than trying to integrate the raw ADC chip.

**Pins**

- **5V, GND**: Power for the board. There are also separate analog grounds which were tied to the same GND for this design.
- **SCLK, DIN, DOUT**: SPI bus for communication between the Pi and ADS1256 to change settings and read data. Can be shared between multiple modules.
- **CS, DRDY, PDWN**: Additional lines for signalling during data transmission. Need to be connected to separate pins for each module.
- **AIN0-AIN7**: Analog inputs for voltage measurement. These pins can either act as 8 single-ended inputs or 4 differential inputs. Load cells give a differential signal.

### JST S4B-XH-A Connectors

![JST S4B-XH-A connector](images/JST_S4B-XH-A.jpg)

These are standard 2.5mm right-angle connectors, which were selected because 2.5mm JST connectors had been used to connect load cells in previous designs.

Below is the wiring convention used in this design:

[![Diagram showing below information](images/load_cell_wiring.png)](images/load_cell_wiring.png)

- **Pin 1**: GND/Excitation- (black)
- **Pin 2**: Signal- (white)
- **Pin 3**: Signal+ (green)
- **Pin 4**: 5V/Excitation+ (red)

### [Stacking Headers](https://www.amazon.com/Female-Stacking-Header-Compatible-Raspberry/dp/B084Q4W1PW)

![Stacking headers](images/headers.jpg)

We used stacking headers to allow another board to be stacked on top, but any 2x20 2.54mm pitch female headers should work for attaching the PCB to the Pi.

## Assembly

### 1. Solder headers

The headers for connecting to the Pi should be soldered first, because otherwise the ADS1256 board might get in the way. Make sure the female side is facing down (towards side with KXR logo).

### 2. Solder ADS1256 module

Solder the ADS1256 module onto the top of the board, lined up with the footprint. **It will not work if soldered on the other side!**

### 3. Solder JST connectors

Same deal, solder the connectors as marked on the PCB.

### 4. Bridge solder jumpers

Select pins for DRDY, CS, and PDWN using solder jumpers on the back of the board. By bridging either the left or right pads with the center pads, corresponding pins from the ADS1256 module can be connected to one of two different pins on the Pi. See the [Jumpers](#jumpers) section for more details.

## Schematic

[![Screenshot of the schematic](images/schematic.png)](images/schematic.png)

This should be pretty self-explanatory. J1 is connected to AIN0/1, J2 is connected to AIN2/3, etc., and the SPI lines are connected to the hardware SPI on the Pi. The solder jumpers are the only thing to watch out for.

## Jumpers

[![Image of solder jumpers on the back of the board](images/jumpers.png)](images/jumpers.png)

To use two boards at the same time, they will need to have separate data lines. To do this, bridge the solder jumpers on the right side for "Board 1", and the left side for "Board 2".

### "Board 1" pins:

| Pin      | GPIO   | Physical Pin # |
| -------- | ------ | -------------- |
| **DRDY** | GPIO22 | 15             |
| **CS**   | GPIO8  | 24             |
| **PDWN** | GPIO24 | 18             |

### "Board 2" pins:

| Pin      | GPIO   | Physical Pin # |
| -------- | ------ | -------------- |
| **DRDY** | GPIO23 | 16             |
| **CS**   | GPIO7  | 26             |
| **PDWN** | GPIO25 | 22             |

## Software

To use the ADS1256, find an applicable library, modifying it as needed. For example, you could clone [this repo for Waveshare boards](https://github.com/waveshareteam/High-Precision-AD-DA-Board/tree/master/RaspberryPI/ADS1256/python3) and modify `config.py` with the applicable pin numbers. This library is slightly broken as it does not support differential mode. This can be fixed by changing the global ScanMode variable to an [instance variable](https://docs.python.org/3/tutorial/classes.html#class-and-instance-variables) in the ADS1256 class in the ADS1256.py module. Additionally the ScanMode variable should be set to 1 for differential mode.

The raspberry pi 5 no longer supports the [`RPi.GPIO` Library](https://pypi.org/project/RPi.GPIO/). Instead install the [`rpi-lgpio` Library](https://pypi.org/project/rpi-lgpio/). This library does not need any of the python code to be changed (this includes the import statement).

One issue you may run into is the fact that the board uses the hardware CS pin, which is often claimed by the SPI interface, so it can't be used as a GPIO output. Since most ADS1256 libraries will manually set the CS pin, you will need to free up the pin to be used as an output. This can be done by changing the SPI device tree overlay to one which doesn't claim the CS pin, such as `spi0-0cs`. To do this, add the line `dtoverlay=spi0-0cs` to `/boot/firmware/config.txt` (or `/boot/firmware/config.txt` on older versions), removing any conflicting dtoverlays if necessary (comment out `dtparam=spi=on`).

Good luck!

## Pictures

[![Front side of PCB](images/PCB_front.jpg)](images/PCB_front.jpg)
[![Back side of PCB](images/PCB_back.jpg)](images/PCB_back.jpg)
[![Fully assembled PCB with Pi](images/fully_assembled.jpg)](images/fully_assembled.jpg)