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
        value = self._device.char_read(self.CHAR_IR_TEMP_DATA)

        rawTamb = (value[3] << 8) + value[2]
        return float(rawTamb >> 2) * 0.03125

    def enable_humidity_sensor(self):
        self._device.char_write_handle(self.CHAR_HANDLE_HUMIDITY_CONTROL, [1])

    def disable_humidity_sensor(self):
        self._device.char_write_handle(self.CHAR_HANDLE_HUMIDITY_CONTROL, [0])

    def read_humidity_sensor(self, retries=10):
        value = self._device.char_read(self.CHAR_HUMIDITY_DATA)

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
                        "sample_interval": 120,
                        "sample_delay": 3,
                        "enable": sensortag.enable_humidity_sensor,
                        "disable": sensortag.disable_humidity_sensor,
                        "read": sensortag.read_humidity_sensor,
                        "format": "{:.2f}",
                    },
            }

        while True:
            sensors_to_sample = [name for (name, sensor) in sensor_list.items() if sensor.get("last_sample_time", 0) + sensor.get("sample_interval", 0) <= time.monotonic()]
            sample_delay = 1

            for sensor in [sensor_list[name] for name in sensors_to_sample]:
                sample_delay = max(sample_delay, sensor.get("sample_delay", 0))
                sensor["enable"]()

            if sample_delay > 0:
                time.sleep(sample_delay)

            for sensor in [sensor_list[name] for name in sensors_to_sample]:
                value = sensor["read"]()
                formatter = sensor.get("format", "{}")
                value_formatted = formatter.format(value)

                #print("%s = %s" % (sensor["topic"], value_formatted))
                mqtt_client.publish(sensor["topic"], value_formatted);

                sensor["disable"]()
                sensor["last_sample_time"] = time.monotonic()

            time.sleep(15)

    except ConnectionRefusedError:
        print("MQTT failed, waiting to retry...\n")
        time.sleep(5)

    except pygatt.exceptions.NotConnectedError:
        print("BLE failed, waiting to retry...\n")
        time.sleep(5)

    except pygatt.exceptions.NotificationTimeout:
        time.sleep(1)
