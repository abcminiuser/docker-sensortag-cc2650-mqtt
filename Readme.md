# TI SensorTag to MQTT Bridge

This is a Docker image that connects to a
[TI CC2650 SensorTag](http://processors.wiki.ti.com/index.php/CC2650_SensorTag_User's_Guide)
Bluetooth Low Energy development kit, and periodically samples various sensors
and publishes them to a running MQTT broker (in my use case, this is a
[Eclipse Mosquito](https://projects.eclipse.org/projects/technology.mosquitto)
instance which feeds the resulting aggregate data from this and other sensors
into a running [HomeAssistant](http://home-assistant.io/) home automation
instance.

This is very basic and extremely hacky - it's pretty much only for my own benefit,
although others may find it useful for their own hardware hacking.


## Limitations

Many. Hard coded server addresses in the script, single SensorTag instance, hard
coded SensorTag BDADDR.

I've based this on the Python Gattool library, which isn't very good, but is one
of the few that actually (kinda) works on Alpine instances without `systemd` or
any sort of Bluetooth daemon. Behind the scenes it's just wrapping the command
line `gattool` from BlueZ, but hey, it works. Kinda.

Only tested with the CC2650 version of the TI SensorTag. Other versions will use
different BLE GATT handles and UUIDs.

Note that the PyGatt library can't write via UUID, you have to specify the
handle instead. Reads go via UUIDs. Why? Because BLE is a dumpster fire on
Linux.

SensorTag must be powered on and broadcasting (via the power button) for the
script to connect to it. Periodic broadcasts are only maintained for two
minutes, after which the power button must be pressed again if the connection is
lost.


## Setup

1. Attach USB BLE adapter to server.
2. Edit the Python script to use the appropriate BDADDR and MQTT host values
3. Build and run the docker image:
	```
	docker build -t sensortag .
	docker run -d sensortag
	```
4. Press power button on SensorTag (running factory BLE firmwarw) to start
periodic broadcasts for 2 minutes, so that the script can connect to it.


Docker compose sample:
```
version: '2'

services:
  mqtt:
    container_name: MQTT
    image: eclipse-mosquitto:latest
    network_mode: "bridge"
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /volume1/docker/Mosquitto/data:/mosquitto/data
      - /volume1/docker/Mosquitto/log:/mosquitto/log
      - /volume1/docker/Mosquitto/mosquitto.conf:/mosquitto/config/mosquitto.conf
    ports:
      - "1883:1883"
      - "9001:9001"
    environment:
      - TZ=Australia/Melbourne
    restart: unless-stopped

  home-assistant:
    container_name: HomeAssistant
    image: homeassistant/home-assistant:latest
    network_mode: "host"
    depends_on:
      - "home-assistant-db"
      - "mqtt"
    volumes:
      - /volume1/docker/HomeAssistant:/config
      - /etc/localtime:/etc/localtime:ro
    ports:
      - "8123:8123"
    environment:
      - TZ=Australia/Melbourne
    restart: unless-stopped

  sensortag:
    container_name: SensorTag
    build: docker-sensortag-cc2650-mqtt
    network_mode: "host"
    environment:
      - TZ=Australia/Melbourne
    restart: unless-stopped
```

Build via `docker-compose build`, run the stack via `docker-compose up -d`.
