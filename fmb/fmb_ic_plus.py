#!/usr/bin/env python3

import time
from enum import IntEnum
from math import nan
from threading import RLock, Thread

import serial
from tango import (AttrWriteType, Database, DevFailed,
                   DevState, DeviceProxy, Util)
from tango.server import attribute, command, Device, device_property, run


class RangeEnum(IntEnum):
    """
    An enumeration that represents possible measuring ranges of FMB
    YMCS0004/5 picoampermeters with its current ranges and reading times.
    """
    RANGE_1 = 0
    RANGE_2 = 1
    RANGE_3 = 2
    RANGE_4 = 3
    RANGE_5 = 4
    RANGE_6 = 5

    def min(self) -> int:
        """
        A lower range limit of measuring current.
        @return: A minimum current in fA that can be measured
        using this range.
        """
        return 1e2 * pow(10, self)

    def max(self) -> int:
        """
        An upper range limit of measuring current.
        @return: A maximum current in fA that can be measured
        using this range.
        """
        return 1e6 * pow(10, self)

    def to_amperes(self, int_representation: int) -> float:
        """
        A method to convert integer value of a current to A for the range.
        @param int_representation: a 28bit int value of a current.
        @return: a current in A.
        """
        return self.max() / 262144000 * int_representation * 1e-15


class FMBICPlusChannel(Device):
    """
    A Tango device class for FMB Oxford IC Plus ionisation chambers equipped
    with YMCS0004/5 picoampermeters. Those picoampermeters support bus
    connection via RS232 up to 16 devices, so the class represents one
    picoampermeter within that bus.
    """

    MIN_VOLTAGE = 0
    MAX_VOLTAGE = 1700

    MIN_OFFSET = 0
    MAX_OFFSET = 99

    MIN_EXPOSITION_TIME = 1e-6
    MAX_EXPOSITION_TIME = float(24 * 60 * 60)

    address = device_property(dtype=int, doc="A device address which is set "
                              "via switches on the chamber body.",
                              default_value=0)
    _db = None
    _host = None

    @staticmethod
    def fit_voltage_range(high_voltage: int) -> int:
        """
        A method to keep the set voltage within the allowed margin of 0 – 1700.
        """
        high_voltage = min(high_voltage, FMBICPlusChannel.MAX_VOLTAGE)
        high_voltage = max(high_voltage, FMBICPlusChannel.MIN_VOLTAGE)
        return high_voltage

    @staticmethod
    def fit_offset_range(offset: int) -> int:
        """
        A method to keep the set offset within the allowed margin of 0 – 99.
        """
        offset = min(offset, FMBICPlusChannel.MAX_OFFSET)
        offset = max(offset, FMBICPlusChannel.MIN_OFFSET)
        return offset

    @staticmethod
    def fit_exp_time_range(exposition_time: float) -> float:
        """
        A method to keep the set exposition time within
        the allowed margin of 1e-6 – 86400.
        """
        exposition_time = min(
                        exposition_time, FMBICPlusChannel.MAX_EXPOSITION_TIME)
        exposition_time = max(
                        exposition_time, FMBICPlusChannel.MIN_EXPOSITION_TIME)
        return exposition_time

    _high_voltage = 0

    @attribute(label="High Voltage", dtype=int,
               access=AttrWriteType.READ_WRITE,
               min_value=MIN_VOLTAGE, max_value=MAX_VOLTAGE,
               unit="V")
    def high_voltage(self):
        """
        An attribute "high_voltage" getter method.
        Allowed DevState states: ON, RUNNING
        :return: a high voltage setting of the IC in Volts.
        """
        state = self.get_state()
        if (state == DevState.ON or state == DevState.RUNNING):
            self.debug_stream("Receiving high voltage from {} device".format(
                              self.address))
            return self._high_voltage
        else:
            self.error_stream("Unable to receive high voltage from {} "
                              "device".format(self.address))
            self.set_state(DevState.FAULT)
            raise DevFailed()

    @high_voltage.write
    def high_voltage(self, high_voltage: int):
        """
        An attribute "high_voltage" setter method.
        Allowed DevState states: ON
        :param high_voltage: A new high voltage value
        within range [MIN_VOLTAGE, MAX_VOLTAGE] in Volts,
        otherwise it will be cast to the corresponding range limit.
        """
        state = self.get_state()
        if state == DevState.ON:
            self.debug_stream("Assigning high voltage to {} device".format(
                              self.address))
            self._high_voltage = FMBICPlusChannel.fit_voltage_range(
                                                                high_voltage)
            self._host.write_voltage([self.address, high_voltage])
        else:
            self.error_stream("Unable to assign high voltage to {} "
                              "device".format(self.address))
            self.set_state(DevState.FAULT)
            raise DevFailed()

    _range = RangeEnum.RANGE_1

    @attribute(label="Measurement Range", dtype=RangeEnum,
               access=AttrWriteType.READ_WRITE)
    def range(self):
        """
        An attribute "range" getter method.
        Allowed DevState states: ON, RUNNING
        :return: a selected range for measuring.
        """
        state = self.get_state()
        if (state == DevState.ON or state == DevState.RUNNING):
            self.debug_stream("Receiving range from {} device".format(
                              self.address))
            return self._range
        else:
            self.error_stream("Unable to receive range from {} device".format(
                              self.address))
            self.set_state(DevState.FAULT)
            raise DevFailed()

    @range.write
    def range(self, range):
        """
        An attribute "range" setter method.
        Allowed DevState states: ON
        @param range: A new range for performing measurements.
        """
        state = self.get_state()
        if state == DevState.ON:
            self.debug_stream("Assigning range to {} device".format(
                              self.address))
            self._range = RangeEnum(range)
            self._host.write_range([self.address, range+1])
        else:
            self.error_stream("Unable to assign range to {} device".format(
                              self.address))
            self.set_state(DevState.FAULT)
            raise DevFailed()

    _offset = 0

    @attribute(label="Offset", dtype=int, access=AttrWriteType.READ_WRITE,
               min_value=MIN_OFFSET, max_value=MAX_OFFSET,
               unit="%")
    def offset(self):
        """
        An attribute "offset" getter method.
        Allowed DevState states: ON, RUNNING
        @return: IC offset for measured current in percents.
        """
        state = self.get_state()
        if (state == DevState.ON or state == DevState.RUNNING):
            self.debug_stream("Receiving offset from {} device".format(
                              self.address))
            return self._offset
        else:
            self.error_stream("Unable to receive offset from {} device".format(
                              self.address))
            self.set_state(DevState.FAULT)
            raise DevFailed()

    @offset.write
    def offset(self, offset: int):
        """
        An attribute "offset" setter method.
        Allowed DevState states: ON
        @param offset: A percentage of measured current which is interpreted
        as offset. It should be in range [MIN_OFFSET, MAX_OFFSET], otherwise
        values < 0 will be cast to 0, and values > 99 to 99 respectively.
        """
        state = self.get_state()
        if state == DevState.ON:
            self.debug_stream("Assigning offset to {} device".format(
                              self.address))
            self._offset = FMBICPlusChannel.fit_offset_range(offset)
            self._host.write_offset([self.address, offset])
            self._offset = self._host.read_offset(self.address)
        else:
            self.error_stream("Unable to assign offset to {} device".format(
                              self.address))
            self.set_state(DevState.FAULT)
            raise DevFailed()

    _exposition_time = 0.0

    @attribute(label="Exposition Time", dtype=float,
               access=AttrWriteType.READ_WRITE,
               min_value=MIN_EXPOSITION_TIME,
               max_value=MAX_EXPOSITION_TIME, unit="s")
    def exposition_time(self):
        """
        An attribute "exposition_time" getter method.
        Allowed DevState states: ON, RUNNING
        @return: An actual duration of exposition in seconds.
        """
        state = self.get_state()
        if (state == DevState.ON or state == DevState.RUNNING):
            self.debug_stream("Receiving exposition time from {} "
                              "device".format(self.address))
            return self._exposition_time
        else:
            self.error_stream("Unable to receive exposition time from {} "
                              "device".format(self.address))
            self.set_state(DevState.FAULT)
            raise DevFailed()

    @exposition_time.write
    def exposition_time(self, exposition_time: float):
        """
        An attribute "exposition_time" setter method.
        Allowed DevState states: ON
        @param exposition_time: A time in seconds which is used in the
        start() command.
        All non-positive and non-finite values won't be applied.
        Positive finite values which are out of
        [MIN_EXPOSITION_TIME, MAX_EXPOSITION_TIME] range will be set according
        to those limits.
        """
        state = self.get_state()
        if state == DevState.ON:
            self.debug_stream("Assigning exposition time to {} device".format(
                              self.address))
            self._exposition_time = FMBICPlusChannel.fit_exp_time_range(
                                                            exposition_time)
        else:
            self.error_stream("Unable to assign exposition time to {} "
                              "device".format(self.address))
            self.set_state(DevState.FAULT)
            raise DevFailed()

    _current = 0.0

    @attribute(label="Current", dtype=float,
               access=AttrWriteType.READ, unit="A")
    def current(self):
        """
        An attribute "current" getter method.
        Allowed DevState states: ON, RUNNING
        @return: A last measured current value. If no measurements have been
        completed or the last measurement has been failed,
        a NaN value is returned.
        """
        state = self.get_state()
        if (state == DevState.ON or state == DevState.RUNNING):
            self.debug_stream("Receiving current from {} device".format(
                              self.address))
            return self._current
        else:
            self.error_stream("Unable to receive current from {} "
                              "device".format(self.address))
            self.set_state(DevState.FAULT)
            return nan

    _raw_current = 0

    @attribute(label="Raw Current", dtype=int,
               access=AttrWriteType.READ)
    def raw_current(self):
        """
        An attribute "raw_current" getter method.
        Allowed DevState states: ON, RUNNING
        @return: A last measured raw_current value. If no measurements
        have been completed or the last measurement has been failed,
        a NaN value is returned.
        """
        state = self.get_state()
        if (state == DevState.ON or state == DevState.RUNNING):
            self.debug_stream("Receiving raw current from {} device".format(
                              self.address))
            return self._raw_current
        else:
            self.error_stream("Unable to receive raw current from {} "
                              "device".format(self.address))
            self.set_state(DevState.FAULT)
            return nan

    def get_ic_chamber_parameters(self):
        """
        Fetches current 'voltage', 'range' and 'offset' parameters
        from an IC chamber.
        Is called within init_device() and reset() methods.
        """
        self._high_voltage = self._host.read_voltage(self.address)
        self._range = RangeEnum(self._host.read_range(self.address) - 1)
        self._offset = self._host.read_offset(self.address)

    def init_device(self):
        Device.init_device(self)
        self._db = Database()
        hosts = self._db.get_device_name(Util.instance().get_ds_name(),
                                         FMBICPlusHost.__name__)
        if not hosts:
            self.error_stream("{} not found in this device server "
                              "instance".format(FMBICPlusHost.__name__))
            self.set_state(DevState.FAULT)
        self._host = DeviceProxy(hosts[0])
        self.get_ic_chamber_parameters()
        self.set_state(DevState.ON)

    _stop = False

    def __measure(self) -> float:
        """
        A method capable of single/multiple measurement execution within the
        set exposition time.
        Returns the averaged _current value in amperes.
        Is called within start() method in a thread.
        """
        result = 0
        result_raw = 0
        cycles = 0
        self.set_state(DevState.RUNNING)
        self.debug_stream("Starting measurement on {} device".format(
                          self.address))
        start_time = time.perf_counter()
        while time.perf_counter() - start_time <= self._exposition_time:
            try:
                if self._stop:
                    break
                else:
                    iter = self._host.measure(
                        [self.address, int(
                            self._exposition_time /
                            FMBICPlusChannel.MIN_EXPOSITION_TIME)])
                    if iter == -1:
                        continue
                    else:
                        result += self._range.to_amperes(iter)
                        result_raw += iter
                        cycles += 1
            except serial.SerialException as se:
                self.error_stream("Following error occurred while fetching "
                                  "data from {} device\n.{}".format(
                                                            self.address, se))
                self.set_state(DevState.FAULT)
                raise DevFailed()
        self.info_stream(
                "Result of measurement is: {} ({}) for {} cycles".format(
                                                                    result,
                                                                    result_raw,
                                                                    cycles))
        if cycles > 0:
            self._current = result / cycles
            self._raw_current = result_raw / cycles
        else:
            self._current = nan
            self._raw_current = -1
        self._stop = False
        self.set_state(DevState.ON)

    @command(dtype_in=None, dtype_out=None)
    def start(self):
        """
        A command to start a single measurement. After calling, the device
        will enter the RUNNING state. When measurement is complete, a device
        returns to the ON state with "current" attribute updated. If no proper
        data has been fetched during exposition time, a DevFailed exception
        will be thrown and the state will be set to DevState.FAULT.
        Allowed DevState states: ON.
        """
        state = self.get_state()
        if state == DevState.ON:
            self._stop = False
            thread = Thread(target=self.__measure)
            thread.start()
        else:
            self.warn_stream("Failed to perform a measurement while {} "
                             "device in `{}` state. Ignoring request".format(
                                self.address, str(state)))
            self.set_state(DevState.FAULT)
            raise DevFailed()

    @command(dtype_in=None, dtype_out=None)
    def stop(self):
        """
        A command to abort current measurement and turn a device
        into ON state. Attribute "current" is NaN in this case.
        Allowed DevState states: RUNNING, ON.
        """
        state = self.get_state()
        if state == DevState.RUNNING:
            self.debug_stream("Stopping measurement on {} device".format(
                              self.address))
            self._stop = True
            self.set_state(DevState.ON)
        elif state == DevState.ON:
            self.debug_stream("{} device already stopped".format(
                              self.address))
            self._stop = True
        else:
            self.warn_stream("Failed to perform a measurement while {} "
                             "device in `{}` state. Ignoring request".format(
                              self.address, str(state)))
            self.set_state(DevState.FAULT)
            raise DevFailed()

    @command(dtype_in=None, dtype_out=None)
    def reset(self):
        """
        A command to reset IC settings: 'high_voltage', 'range', 'offset'
        to the default values.
        Allowed DevState states: ON.
        """
        state = self.get_state()
        if state == DevState.ON:
            self.debug_stream("Resetting {} device".format(
                              self.address))
            self._host.reset(self.address)
            self.get_ic_chamber_parameters()
        else:
            self.error_stream("Unable to reset {} device".format(
                              self.address))
            self.set_state(DevState.FAULT)
            raise DevFailed()


class FMBICPlusHost(Device):
    """
    A tango device class to serve multiple ICs within one RS232 bus.
    """

    MAX_CHANNELS = 15

    port_id = device_property(dtype=str,
                              doc="Full path to a serial port object on "
                              "Unix-based systems or COMX for Windows.",
                              default_value="/dev/ttyUSB0")
    port_baudrate = device_property(dtype=int,
                                    doc="Serial port speed in bauds.",
                                    default_value=9600)
    port_timeout = device_property(dtype=int, doc="A serial port connection "
                                   "timeout in seconds. Use 0 to disable.",
                                   default_value=0)
    command_timeout = device_property(dtype=float, doc="Timeout in sec/float "
                                      "for a command that should be executed "
                                      "instantly",
                                      default_value=0.0)

    _port = None
    _lock = RLock()

    @command(dtype_in=int, dtype_out=int)
    def read_voltage(self, channel_id: int) -> int:
        """
        A command to read a high voltage of IC from specified channel.
        @param channel_id: A number of channel.
        @return: Channel voltage for correct channel id or -1 otherwise.
        """
        return self.query(":CONF{}:VOLT?\n".format(channel_id), True) \
            if 0 <= channel_id <= FMBICPlusHost.MAX_CHANNELS else -1

    @command(dtype_in=[int], dtype_out=None)
    def write_voltage(self, data: list[int]) -> None:
        """
        A command to write a high voltage to the specified IC channel.
        @param data: an array of two integers, where 1st - channel id,
        2nd - a voltage to set.
        """
        if (len(data) == 2 and 0 <= data[0] <= FMBICPlusHost.MAX_CHANNELS and
                FMBICPlusChannel.MIN_VOLTAGE <= data[1] <=
                FMBICPlusChannel.MAX_VOLTAGE):
            channel_id = data[0]
            voltage = data[1]
            self.query(":CONF{}:VOLT {}\n".format(channel_id, voltage))

    @command(dtype_in=int, dtype_out=int)
    def read_range(self, channel_id: int) -> int:
        """
        A command to read a range of IC from a specified channel.
        @param channel_id: A number of channel.
        @return: Channel range for correct channel id or -1 otherwise.
        """
        return self.query(":CONF{}:CURR:RANG?\n".format(channel_id), True) \
            if 0 <= channel_id <= FMBICPlusHost.MAX_CHANNELS else -1

    @command(dtype_in=[int], dtype_out=None)
    def write_range(self, data: list[int]) -> None:
        """
        A command to write a range to the specified IC channel.
        @param data: an array of two integers, where 1st - channel id,
        2nd - a range to set.
        """
        channel_id = data[0]
        range = data[1]
        self.query(":CONF{}:CURR:RANG {}\n".format(channel_id, range))

    @command(dtype_in=int, dtype_out=int)
    def read_offset(self, channel_id: int) -> int:
        """
        A command to read an offset of IC from specified channel.
        @param channel_id: A number of channel.
        @return: Channel offset for correct channel id or -1 otherwise.
        """
        return self.query(":CONF{}:CURR:OFFS?\n".format(channel_id), True) \
            if 0 <= channel_id <= FMBICPlusHost.MAX_CHANNELS else -1

    @command(dtype_in=[int], dtype_out=None)
    def write_offset(self, data: list[int]) -> None:
        """
        A command to write an offset to the specified IC channel.
        @param data: an array of two integers, where 1st - channel id,
        2nd - an offset to set.
        """
        if (len(data) == 2 and 0 <= data[0] <= FMBICPlusHost.MAX_CHANNELS and
                FMBICPlusChannel.MIN_OFFSET <= data[1] <
                FMBICPlusChannel.MAX_OFFSET):
            channel_id = data[0]
            offset = data[1]
            self.query(":CONF{}:CURR:OFFS {}\n".format(channel_id, offset))

    @command(dtype_in=int, dtype_out=None)
    def reset(self, channel_id: int) -> None:
        """
        A command to reset IC settings to default values.
        @param channel_id: A number of channel to reset.
        """
        self.query("*RST{}\n".format(channel_id))

    @command(dtype_in=[int], dtype_out=int)
    def measure(self, data: list[int]) -> int:
        """
        A command to start a measurement on a specific channel.
        @param data: an array of two integers, where 1st - channel id,
        2nd - expected command execution time in μseconds.
        @return: measured current as integer where 0 is 0 and 262144000 is max
        of the selected range of the IC.
        -1 will be returned if channel id is invalid
        or execution time is out of range.
        """
        if (len(data) == 2 and 0 <= data[0] <= FMBICPlusHost.MAX_CHANNELS):
            channel_id = data[0]
            execution_time = data[1] * FMBICPlusChannel.MIN_EXPOSITION_TIME
            return self.query(":READ{}:CURR?\n".format(channel_id),
                              True, execution_time)
        else:
            return -1

    def query(self, raw_command: str, data_expected=False,
              execution_time=0) -> int:
        """
        An internal thread-safe method to communicate with IC network via
        serial port.
        @param raw_command: An IC command to pass to the network in IC-specific
        format. LF byte at the end is expected.
        @param data_expected: True if command produces an answer with any data
        or False if doesn't.
        @param execution_time: a minimum time to response to the command w/o
        i/o timeouts. It can be useful for executing measurements
        with known exposition time.
        @return: requested data as integer if data_expected is True
        or 0 if not.
        """
        try:
            self._lock.acquire()
            self.debug_stream(
                "Passing following raw command to IC network: \n{}".format(
                    raw_command))
            self._port.write(bytes(raw_command, 'ascii'))
            self._port.timeout = self.command_timeout + execution_time
            answer = (self._port.readline() if data_expected
                      else self._port.read())
            self.info_stream("The answer received from device "
                             "is: {}".format(answer))
            if ((len(answer) < 3 and data_expected) or
                    (answer != b'\x06' and not data_expected)) or not answer:
                self.warn_stream(
                    "An IC didn't respond correctly within {} "
                    "seconds of timeout and {} of execution time".format(
                        self.command_timeout, execution_time))
                return -1
            data = int(answer[1:-1]) if data_expected else 0
            self.debug_stream("An IC responded correctly{}"
                              .format(" with data {}".format(data)
                                      if data_expected else ""))
            return data
        except serial.SerialException as se:
            self.error_stream(
                "Following error occurred during communication "
                "via serial port:\n{}".format(se))
            self.set_state(DevState.FAULT)
            raise DevFailed()
        finally:
            self._lock.release()

    def init_device(self):
        Device.init_device(self)
        try:
            self._port = serial.Serial(self.port_id,
                                       baudrate=self.port_baudrate,
                                       timeout=self.port_timeout)
            self.debug_stream(
                "Connection to the serial port `{}` has been "
                "established successfully".format(self.port_id))
        except serial.SerialException as se:
            self.error_stream(
                "Connection to the serial port `{}` has been "
                "failed with following exception:\n {}".format(self.port_id,
                                                               se))
            self.set_state(DevState.FAULT)
            raise DevFailed()
        self.set_state(DevState.ON)


def main():
    run({FMBICPlusHost.__name__: FMBICPlusHost,
         FMBICPlusChannel.__name__: FMBICPlusChannel})


if __name__ == '__main__':
    main()
