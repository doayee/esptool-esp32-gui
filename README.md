# DoayeeESP32DFU

A GUI for ESP32 flashing tool esptool.
**Note:** Currently using esptool v2.6

![gui](esp32bta/dfu/osxgui.PNG "Description goes here")


## Installing

You can download prebuilt executable applications for both Windows and MacOS from ?. These are self-contained applications and have no prerequisites on your system. They have been tested with Windows 10 and macOS Mojave.

## Usage

If you compile your project using make, the App and partition table binaries will be put in your /build directory. The bootloader binary is under /build/bootloader.bin

If the partition table has not been changed, it only needs to be reflashed when the ESP32 has been fully erased. Likewise the bootloader binary will not change between edits to your personal app code. This means only the App needs to be flashed each time

## Running From Source

**Note:** Currently using esptool v2.6

1. Install the project dependencies using your python3 package manager
2. Run the doayee_dfu.py script in python3
