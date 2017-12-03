#!/usr/bin/env python3

import pygatt
import paho.mqtt.client as mqtt
import time


MQTT_HOST = "192.168.1.104"
MQTT_HOST_PORT = 1883

SENSORTAG_BDADDR = "68:C9:0B:05:63:07"



class CC2530_SensorTag(object):
    CHAR_HANDLE_TEMP_CONTROL = 0x0024
    CHAR_TEMP_DATA = "F000AA01-0451-4000-B000-000000000000"

    def __init__(self, device):
        self._device = device

    def enable_temp_sensor(self):
        self._device.char_write_handle(self.CHAR_HANDLE_TEMP_CONTROL, [1])

    def disable_temp_sensor(self):
        self._device.char_write_handle(self.CHAR_HANDLE_TEMP_CONTROL, [0])

    def read_temp_sensor_ambient(self, retries=10):
        value = [0]
        for i in range(0, retries):
            value = self._device.char_read(self.CHAR_TEMP_DATA)
            if all(v != 0 for v in value):
                break

        TEMP_SCALE_DEG_C = 0.03125

        rawTamb = (value[3]<<8) + value[2]
        return float(rawTamb >> 2) * TEMP_SCALE_DEG_C



while True:
    try:
        mqtt_client = mqtt.Client()
        mqtt_client.connect(MQTT_HOST, MQTT_HOST_PORT, 60)

        bluetooth_adapter = pygatt.GATTToolBackend()
        bluetooth_adapter.start(reset_on_start=False)

        sensortag_device = bluetooth_adapter.connect(SENSORTAG_BDADDR)
        sensortag = CC2530_SensorTag(sensortag_device)

        while True:
            sensortag.enable_temp_sensor()
            ambient_temp = sensortag.read_temp_sensor_ambient()
            sensortag.disable_temp_sensor()

            ambient_temp_string = "{:.2f}".format(ambient_temp)
            print("Temperature: {}".format(ambient_temp_string))

            mqtt_client.publish("home/sensortag/temperature", ambient_temp_string);

            time.sleep(30)

    except ConnectionRefusedError:
        print("MQTT failed, waiting to retry...\n")
        time.sleep(5)

    except pygatt.exceptions.NotificationTimeout:
        time.sleep(1)

    except pygatt.exceptions.NotConnectedError:
        print("BLE failed, waiting to retry...\n")
        time.sleep(1)
