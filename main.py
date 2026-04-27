import asyncio
import json
import logging
import os
import struct

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from paho.mqtt.client import MQTTMessage

from ble_gateway import BLEGateway
from mqtt_gateway import MQTTGateway


async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("MainLogger")

    loop = asyncio.get_running_loop()

    mqtt_host = os.environ.get("MQTT_HOST", "isc-coordinator.lan")
    mqtt_port = int(os.environ.get("MQTT_PORT", 1883))

    ble = BLEGateway()
    mqtt = MQTTGateway(mqtt_host, mqtt_port)

    def on_button(client: BleakClient, char: BleakGATTCharacteristic, data: bytes):
        is_pressed: bool = struct.unpack(">B", data)[0] != 0
        address: str = client.address
        topic: str = f"{address}/button"
        logger.info(f"{topic} -> {is_pressed}")
        mqtt.send(topic, b"1" if is_pressed else b"0")
    
    def on_ir(client: BleakClient, char: BleakGATTCharacteristic, data: bytes):
        is_occupied: bool = struct.unpack(">B", data)[0] != 0
        address: str = client.address
        topic: str = f"{address}/ir"
        logger.info(f"{topic} -> {is_occupied}")
        mqtt.send(topic, b"1" if is_occupied else b"0")
    
    def on_led(message: MQTTMessage):
        uuid: str = message.topic.split("/")[0]
        color: tuple[int, int, int]
        try:
            data = json.loads(message.payload)
            assert isinstance(data, list)
            assert len(data) == 3
            assert all(map(lambda i: isinstance(i, int), data))
            color = tuple(data)
        except Exception as e:
            logger.error(e)
            return
        logger.info(f"Setting led {uuid} to {color}")
        loop.call_soon_threadsafe(asyncio.ensure_future, ble.set_led(uuid, color))

    ble.on_button = on_button
    ble.on_ir = on_ir

    mqtt.add_listener("+/led", on_led)

    mqtt.run()
    await ble.run()


if __name__ == "__main__":
    asyncio.run(main())
