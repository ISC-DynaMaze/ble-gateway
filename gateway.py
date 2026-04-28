import asyncio
import json
import logging

from bleak import BleakClient
from paho.mqtt.client import MQTTMessage

from ble_gateway import BLEGateway
from mqtt_gateway import MQTTGateway


class Gateway:
    def __init__(self, mqtt_host: str, mqtt_port: int) -> None:
        self.logger = logging.getLogger("Gateway")
        self.loop: asyncio.AbstractEventLoop = asyncio.get_event_loop()

        self.ble = BLEGateway()
        self.mqtt = MQTTGateway(mqtt_host, mqtt_port)

        self.ble.on_connected = self.on_connected
        self.ble.on_disconnected = self.on_disconnected
        self.ble.on_button = self.on_button
        self.ble.on_ir = self.on_ir

        self.mqtt.add_listener("+/led", self.on_led)

    async def run(self):
        self.loop = asyncio.get_running_loop()
        self.mqtt.run()
        await self.ble.run()

    def on_connected(self, client: BleakClient):
        address: str = client.address
        topic: str = f"{address}/status"
        self.mqtt.send(topic, b"connected")

    def on_disconnected(self, client: BleakClient):
        address: str = client.address
        topic: str = f"{address}/status"
        self.mqtt.send(topic, b"disconnected")

    def on_button(self, client: BleakClient, is_pressed: bool):
        address: str = client.address
        topic: str = f"{address}/button"
        self.logger.info(f"{topic} -> {is_pressed}")
        self.mqtt.send(topic, b"1" if is_pressed else b"0")

    def on_ir(self, client: BleakClient, is_occupied: bool):
        address: str = client.address
        topic: str = f"{address}/ir"
        self.logger.info(f"{topic} -> {is_occupied}")
        self.mqtt.send(topic, b"1" if is_occupied else b"0")

    def on_led(self, message: MQTTMessage):
        uuid: str = message.topic.split("/")[0]
        color: tuple[int, int, int]
        try:
            data = json.loads(message.payload)
            assert isinstance(data, list)
            assert len(data) == 3
            assert all(map(lambda i: isinstance(i, int), data))
            color = tuple(data)
        except Exception as e:
            self.logger.error(e)
            return
        self.logger.info(f"Setting led {uuid} to {color}")
        self.loop.call_soon_threadsafe(
            asyncio.ensure_future, self.ble.set_led(uuid, color)
        )
