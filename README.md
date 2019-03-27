# Doayee ESP32 GUI DFU Tool

A standalone GUI application for ESP32 firmware flashing.
**Note:** Currently using esptool v2.6

![gui](/osxgui.png "Description goes here")


## Installing

You can download prebuilt executable applications for both Windows and MacOS from the [releases section](https://github.com/doayee/esptool-esp32-gui/releases). These are self-contained applications and have no prerequisites on your system. They have been tested with Windows 10 and macOS Mojave.

## Usage

If you compile your project using make, the App and partition table binaries will be put in your /build directory. The bootloader binary is under /build/bootloader.bin

If the partition table has not been changed, it only needs to be reflashed when the ESP32 has been fully erased. Likewise the bootloader binary will not change between edits to your personal app code. This means only the App needs to be flashed each time

## Running From Source

**Note:** Currently using esptool v2.6

1. Install the project dependencies using your python3 package manager
2. Run the doayee_dfu.py script in python3

## Feature Requests

Please feel free to get in touch either via GitHub or [twitter](https://twitter.com/DoayeeTech) with any feature requests or suggestions. This is a very early release application and we hope to made it more feature rich in the near future.
