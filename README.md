# fmb-ic-plus


## Overview
The fmb-ic-plus Python module provides interaction capabilities with FMB Oxford IC Plus 50 ionisation chambers (models YMCS0004 and YMCS0005) using Tango Controls via PyTango module. It allows embedding the IC Plus 50 into Tango environment, communicating with it separately or via macros or script during an experiment. It also enhances the built-in capabilities of the IC Plus 50 by making it possible to:
- set the desired configuration by adjusting High Voltage, Range and Offset and reading the measured data via a user-friendly GUI (graphical user interface)   instead of CLI (command line interface)
- perform repeated and fully automated measurements of the current during an operator-adjustable period of time (the so-called Exposition Time), e.g. the duration of an experiment and receive both an averaged result in Amperes or raw data with no transformations.
- abort an ongoing measurement at any time
- store the measured data in Tango Database

The fmb-ic-plus supports simultaneous use of up to 16 IC Plus 50 chambers. Each chamber is equipped with RS232 Communincation Port and is to be connected to host computer via an appropriate cable and RS232 to USB Type A adapter if needed.

For specific technical details regarding the IC Plus 50 chamberes please refer to 
Operating and Service Manual by the link in the Documentation section below.


## Prerequisites
It is implied that the client/operator has at his disposal a Linux-based computer, Python3 and corresponding version of pip installed.  
The fmb-ic-plus is a noarch package and is suitable for all currently supported implementations of Linux OS.


## Additional Soft- and Hardware Documentation
Useful links:
- [Tango Controls](https://tango-controls.readthedocs.io/en/latest/)
- [PyTango](https://pytango.readthedocs.io/en/stable/)
- [IC Plus Ion Chambers datasheet](https://fmb-oxford.com/products/detectors-diagnostics/ion-chambers/ic-plus-ion-chamber/)
- [IC Plus YMCS0004 and YMCS0005 Operating and Service Manual](https://archive.org/details/manualzilla-id-6000555)


## Installation
**The installation command implies installation of the package with its two indispensable dependencies: [PyTango](https://pytango.readthedocs.io/en/stable/) and [PySerial](https://github.com/pyserial/pyserial/tree/master).**

Clone the repository to the desired directory.

Install the package globally. Execute from a package directory:  
`sudo python3 -m pip install .`

List all the globally installed packages:  
`sudo pip list`

Uninstall the package via pip:  
`sudo pip uninstall fmb-ic-plus -y`

Uninstall the package and its dependency PySerial:  
`sudo pip uninstall fmb-ic-plus pyserial -y`


## Examples/Usage
TBD


## Author
Andrey Pechnikov


## License
MIT License


## Project status
Stable release, v. 1.0.  
No further development planned as of Jan, 2024.


## Nota bene
Built and tested with Python 3.9. Python 2 untested.  
Tested on Raspberry Pi 3B under AlmaLinux 9.3.
