#!/usr/bin/env python3

import pygatt
import paho.mqtt.client as mqtt
import time


MQTT_HOST = "192.168.1.104"
MQTT_HOST_PORT = 1883

SENSORTAG_BDADDR = "68:C9:0B:05:63:07"


class CC2530_SensorTag(object):
    CHAR_HANDLE_IR_TEMP_CONTROL = 0x0024
    CHAR_IR_TEMP_DATA = "F000AA01-0451-4000-B000-000000000000"

    CHAR_HANDLE_HUMIDITY_CONTROL = 0x002C
    CHAR_HUMIDITY_DATA = "F000AA21-0451-4000-B000-000000000000"

    def __init__(self, device):
        self._device = device

    def enable_ir_temp_sensor(self):
        self._device.char_write_handle(self.CHAR_HANDLE_IR_TEMP_CONTROL, [1])

    def disable_ir_temp_sensor(self):
        self._device.char_write_handle(self.CHAR_HANDLE_IR_TEMP_CONTROL, [0])

    def read_ir_temp_sensor_ambient(self, retries=10):
        value = [0]
        for i in range(0, retries):
            value = self._device.char_read(self.CHAR_IR_TEMP_DATA)
            if all(v != 0 for v in value):
                break

        rawTamb = (value[3] << 8) + value[2]
        return float(rawTamb >> 2) * 0.03125

    def enable_humidity_sensor(self):
        self._device.char_write_handle(self.CHAR_HANDLE_HUMIDITY_CONTROL, [1])

    def disable_humidity_sensor(self):
        self._device.char_write_handle(self.CHAR_HANDLE_HUMIDITY_CONTROL, [0])

    def read_humidity_sensor(self, retries=10):
        value = [0]
        for i in range(0, retries):
            value = self._device.char_read(self.CHAR_HUMIDITY_DATA)
            if all(v != 0 for v in value):
                break

        rawHumidity = (value[3] << 8) + value[2]
        return float(rawHumidity & ~0x0003) / 65536 * 100


while True:
    try:
        mqtt_client = mqtt.Client()
        mqtt_client.connect(MQTT_HOST, MQTT_HOST_PORT, 60)

        bluetooth_adapter = pygatt.GATTToolBackend()
        bluetooth_adapter.start(reset_on_start=False)

        sensortag_device = bluetooth_adapter.connect(SENSORTAG_BDADDR)
        sensortag = CC2530_SensorTag(sensortag_device)

        sensor_list = {
                "temperature": {
                        "topic": "home/sensortag/temperature",
                        "sample_interval": 30,
                        "sample_delay": 2,
                        "enable": sensortag.enable_ir_temp_sensor,
                        "disable": sensortag.disable_ir_temp_sensor,
                        "read": sensortag.read_ir_temp_sensor_ambient,
                        "format": "{:.2f}",
                    },
                "humidity": {
                        "topic": "home/sensortag/humidity",
                        "sample_interval": 60 * 3,
                        "sample_delay": 3,
                        "enable": sensortag.enable_humidity_sensor,
                        "disable": sensortag.disable_humidity_sensor,
                        "read": sensortag.read_humidity_sensor,
                        "format": "{:.2f}",
                    },
            }

        while True:
            sensors_to_sample = dict((name, sensor) for name, sensor in sensor_list.items() if sensor.get("next_sample_time", 0) <= time.monotonic())

            for name, sensor in sensors_to_sample.items():
                #print("Enabling \"{}\"...".format(name))
                sensor["enable"]()

            sample_delay = max([sensor.get("sample_delay", 0) for name, sensor in sensors_to_sample.items()])
            if sample_delay > 0:
                #print("Sample delay {}...".format(sample_delay))
                time.sleep(sample_delay)

            for name, sensor in sensors_to_sample.items():
                value = sensor["read"]()
                formatter = sensor.get("format", "{}")
                value_formatted = formatter.format(value)

                #print("%s = %s" % (sensor["topic"], value_formatted))
                mqtt_client.publish(sensor["topic"], value_formatted);

                #print("Disabling \"{}\"...".format(name))
                sensor["disable"]()

                sensor["last_sample_time"] = time.monotonic()
                sensor["next_sample_time"] = sensor["last_sample_time"] + sensor.get("sample_interval", 0)

            next_wake_time = min([sensor.get("next_sample_time", 0) for name, sensor in sensors_to_sample.items()])
            next_wake_time = max(next_wake_time, time.monotonic() + 5)

            #print("Next wake in {}...".format(next_wake_time - time.monotonic()))
            time.sleep(next_wake_time - time.monotonic())

    except ConnectionRefusedError:
        print("MQTT failed, waiting to retry...")
        time.sleep(5)

    except pygatt.exceptions.NotConnectedError:
        print("BLE failed, waiting to retry...")
        time.sleep(5)

    except pygatt.exceptions.NotificationTimeout:
        time.sleep(1)
