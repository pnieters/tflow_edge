import asyncio
import logging
import struct
import txdbus as dbus

import numpy as np
from twisted.internet import reactor, defer, task
from txdbus import client as dbus_client

def async_sleep(time):
    d = defer.Deferred()
    reactor.callLater(time, d.callback, None)
    return d

class Traumschreiber(object):
    """ Traumschreiber EEG asynchronous context manager

    Usage:

        async with Traumschreiber(addr="74:72:61:75:6D:xx"):
            # do some setup
            # ...

            # start listening to data and define a callback function to execute for each new data-point
            await t.start_listening(data_callback)

            # ...

            # set device state, e.g. toggle one LED on, one off, set a red color and a gain of 8x
            await t.set(a_on=1,b_on=1,color=(255,0,0), gain=8)

            #...
    """
    BIOSIGNALS_UUID = "faa7b588-19e5-f590-0545-c99f193c5c3e"
    LEDS_UUID = "fcbea85a-4d87-18a2-2141-0d8d2437c0a4"

    def __init__(self, addr=None, scan=10):
        """ Scan for a given period (scan) and attempt to open a connection to the
        Traumschreiber device with given Bluetooth-device address (addr)
        """
        self.addr=addr
        self.scan=scan
        self.a_on = 0
        self.b_on = 0
        self.color= (0,0,0)
        self.gain = 1
        self.misc= 0

    async def __aenter__(self):
        logging.info("Connecting...")
        self.bus = await dbus_client.connect(reactor, "system")
        self.manager = await self.bus.getRemoteObject("org.bluez","/",
                "org.freedesktop.DBus.ObjectManager")
        self.adapter,_ = await self._find_object("org.bluez.Adapter1")
        if self.scan:
            try:
                logging.info("Start scanning...")
                await self.adapter.callRemote("StartDiscovery")
                await async_sleep(self.scan)
                await self.adapter.callRemote("StopDiscovery")
                logging.info("Done scanning.")
            except Exception as e:
                logging.warn("Scan return exception: {}".format(e))

        # Attempt to find the traumschreiber device
        for attempt in range(10):
            try:
                self.device, self.device_props  = await self._find_object("org.bluez.Device1",
                        Name="traumschreiber", Address=self.addr)
            except Exception as e:
                logging.warning("Failed finding device with error {}".format(e))
            else:
                break

            await async_sleep(1)
            logging.info("Retry finding device ({})".format(attempt))
        else:
            raise Exception("Failed to find device.")

        # Attempt to connect & pair
        is_connected = False
        for attempt in range(10):
            if not is_connected:
                try:
                        # connect
                        logging.info("Connecting...")
                        await self.device.callRemote("Connect")
                        await async_sleep(3)
                except Exception as e:
                    logging.warning("Connection failed with error {}".format(e))

            is_paired = await self.device_props.callRemote("Get",
                    "org.bluez.Device1", "Paired")
            is_paired=True
            is_connected = await self.device_props.callRemote("Get",
                    "org.bluez.Device1", "Connected")

            if not is_paired:
                try:
                        logging.info("Pairing...")
                        await self.device.callRemote("Pair")
                except Exception as e:
                    logging.warning("Pairing failed with error {}".format(e))

            logging.info("Device status connected: {}, paired: {}".format(is_connected, is_paired))
            if is_connected and is_paired:
                break

            await async_sleep(2)
            logging.info("Retry connecting & pairing ({})".format(attempt))
        else:
            raise Exception("Failed to connect/pair.")

        # Attempt to find the characteristic
        for attempt in range(10):
            try:
                self.biosignals_char, self.biosignals_char_props = \
                    await self._find_object("org.bluez.GattCharacteristic1",
                        UUID=self.BIOSIGNALS_UUID)
                await async_sleep(1)
                self.cfg_char, self.leds_char_props = \
                    await self._find_object("org.bluez.GattCharacteristic1",
                        UUID=self.LEDS_UUID)
            except Exception as e:
                logging.warning("Finding characteristic failed with error: {}".format(e))
                #await self.disconnect_unpair_forget()
            else:
                break

            await async_sleep(1)
            logging.info("Retry finding characteristic ({})".format(attempt))
        else:
            raise Exception("Failed to find characteristic.")

        # set leds to ensure alignment of the command
        for i in range(7):
            await self.set()
        return self

    async def start_listening(self, callback):
        """ Call this function to start listening to data packages from the device """
        logging.info("Start listening...")
        def wrapped_callback(_1, data ,_2):
            try:
                if "Value" in data:
                    np_data = np.frombuffer(np.array(data["Value"], dtype=np.int8), dtype=np.dtype('<i2')).reshape((1,8))
                    callback(np_data)
            except Exception as e:
                logging.warning("Encountered exception in data callback method: {}".format(e))

        self._notifier = await self.biosignals_char_props.notifyOnSignal("PropertiesChanged", wrapped_callback)
        await self.biosignals_char.callRemote("StartNotify")

    async def stop_listening(self):
        """ Call this function to stop listening to data packages from the device """
        if self._notifier:
            logging.info("Stop listening...")
            self.biosignals_char_props.cancelSignalNotification(self._notifier)
            await self.biosignals_char.callRemote("StopNotify")

    async def disconnect_unpair_forget(self, disconnect=True, unpair=True, forget=True):
        """ Disconnect and unpair the device (duh) """
        logging.warning("Disconnecting & unpairing...")
        if forget:
            try:
                await self.adapter.callRemote("RemoveDevice", self.device.objectPath)
            except Exception as e:
                logging.info(e)
        if unpair:
            try:
                await self.device.callRemote("CancelPairing")
            except Exception as e:
                logging.info(e)
        if disconnect:
            try:
                await self.device.callRemote("Disconnect")
            except Exception as e:
                logging.info(e)

    async def __aexit__(self, *args):
        self.stop_listening()
        logging.info("Disconnecting...")
        await self.disconnect_unpair_forget(self, unpair=False, forget=False)

    async def _get(self, obj, prop):
        return await obj.callRemote("Get", "org.freedesktop.DBus.Properties", prop)

    async def _set(self, obj, prop, *args):
        return await obj.callRemote("Set", "org.freedesktop.DBus.Properties", prop, *args)

    async def _find_object(self, interface, **props):
        objects = await self.manager.callRemote("GetManagedObjects")
        for object_path, object_interfaces in objects.items():
            if interface in object_interfaces.keys():
                for prop_name,prop_val in props.items():
                    if prop_val!=None and \
                        (prop_name not in object_interfaces[interface].keys()
                        or object_interfaces[interface][prop_name] != prop_val):
                        break
                else:
                    logging.info("Matched {}".format(object_path))
                    obj = await self.bus.getRemoteObject("org.bluez",
                            object_path, interface)
                    obj_props = await self.bus.getRemoteObject("org.bluez",
                            object_path, "org.freedesktop.DBus.Properties")
                    return obj, obj_props
        else:
            raise Exception("No matching object detected with interface {}{}".format(interface, "" if len(props)==0 else " (with properties: {})".format(props)))

    async def set(self, a_on=None, b_on=None, color=None, gain=None, misc=None):
        """ Set Traumschreiber device properties.

        Args:
            a_on (0 or 1):  turns LED 'a' on (1) or off (0), default: no change
            b_on (0 or 1):  turns LED 'b' on (1) or off (0), default: no change
            color:          sets the color of both LEDs to an RGB tuple of ints (0,0,0) < (r,g,b) < (255,255,255)
            gain:           sets the gain of the Traumschreiber device's amplifier (½x,1x,2x,4x,8x,16x,32x,64x)
        """
        try:
            if not a_on is None:
                self.a_on = a_on
            if not b_on is None:
                self.b_on = b_on
            if not color is None:
                self.color = color
            if not gain is None:
                assert gain in [0.5]+[2**i for i in range(7)], "Gain must be one of the following: 0.5x, 1x, 2x, 4x, 8x, 16x, 32x, 64x (got {})".format(gain)
                self.gain = 0b111 if gain < 1 else {1:0b000, 2:0b001, 4:0b010, 8:0b011, 16:0b100, 32:0b101,64:0b110}[gain]
            if not misc is None:
                self.misc = misc

            val = [self.a_on<<1|self.b_on, self.color[0], self.color[1], self.color[2], self.gain, self.misc]
            self.cfg_char.callRemote("WriteValue", val, {})
        except Exception as e:
            logging.error("Raised exception {} in set method.".format(e))
