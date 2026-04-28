import asyncio
import logging
import threading
import time
from functools import partial

from bleak import BleakClient
from paho.mqtt.client import MQTTMessage

from ble_gateway import BLEGateway
from models import LedCommand
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

        self.blinks: dict[str, threading.Event] = {}

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
        command: LedCommand
        try:
            command = LedCommand.model_validate_json(message.payload)
        except Exception as e:
            self.logger.error(e)
            return

        self.logger.info(f"Setting led {uuid} to {command.color}")
        if len(command.timings) == 0:
            if uuid in self.blinks:
                self.blinks[uuid].set()
                self.blinks.pop(uuid)
            self.loop.call_soon_threadsafe(
                asyncio.ensure_future, self.ble.set_led(uuid, command.color)
            )
        else:
            self.start_blink(uuid, command)

    def start_blink(self, address: str, command: LedCommand):
        if address in self.blinks:
            self.blinks[address].set()
        event = threading.Event()
        self.blinks[address] = event
        thread = threading.Thread(
            target=partial(self.blink_loop, event, address, command)
        )
        thread.start()

    def blink_loop(self, event: threading.Event, address: str, command: LedCommand):
        i: int = 0
        while not event.is_set():
            on_sec: float = command.timings[i]
            off_sec: float = (
                command.timings[i + 1] if i + 1 < len(command.timings) else on_sec
            )
            self.loop.call_soon_threadsafe(
                asyncio.ensure_future, self.ble.set_led(address, command.color)
            )
            time.sleep(on_sec)
            if event.is_set():
                break
            self.loop.call_soon_threadsafe(
                asyncio.ensure_future, self.ble.set_led(address, command.off_color)
            )
            time.sleep(off_sec)
            i += 2
            if i >= len(command.timings):
                i = 0
