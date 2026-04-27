import asyncio
import logging
import struct
from functools import partial

from bleak import BleakClient, BleakScanner
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice


class BLEGateway:
    SERVICES_UUID = "794F1FE3-9BE8-4875-83BA-731E1037A880"
    BUTTON_CHAR = "794F1FE3-9BE8-4875-83BA-731E1037A881"
    LED_CHAR = "794F1FE3-9BE8-4875-83BA-731E1037A882"
    IR_CHAR = "794F1FE3-9BE8-4875-83BA-731E1037A883"

    def __init__(self) -> None:
        self.lock: asyncio.Lock = asyncio.Lock()
        self.clients: dict[str, BleakClient] = {}
        self.logger = logging.getLogger("BLEGateway")

    async def scan(self, timeout=5) -> list[BLEDevice]:
        self.logger.info(f"Discovering devices for {timeout} seconds")
        devices: list[BLEDevice] = await BleakScanner.discover(
            timeout=timeout, service_uuids=[self.SERVICES_UUID]
        )
        self.logger.info(f"Found {len(devices)} devices")
        return devices

    async def connect(self, device: BLEDevice):
        self.logger.info(f"Connecting to {device.address}")
        async with BleakClient(device, self.on_disconnected) as client:
            await client.start_notify(self.BUTTON_CHAR, partial(self.on_button, client))
            await client.start_notify(self.IR_CHAR, partial(self.on_ir, client))
            self.clients[client.address] = client
            await asyncio.sleep(1e9)

    def on_disconnected(self, client: BleakClient):
        address: str = client.address
        self.logger.info(f"Client {address} disconnected")
        if address in self.clients:
            self.clients.pop(address)

    def on_button(
        self, client: BleakClient, char: BleakGATTCharacteristic, data: bytes
    ) -> None:
        self.logger.info(f"Received button update from {client.address}: {data}")

    def on_ir(
        self, client: BleakClient, char: BleakGATTCharacteristic, data: bytes
    ) -> None:
        self.logger.info(f"Received IR update from {client.address}: {data}")
        occupied: bool = struct.unpack(">B", data)[0] != 0
        if occupied:
            asyncio.create_task(self.set_led(client.address, (255, 0, 0)))
        else:
            asyncio.create_task(self.set_led(client.address, (0, 255, 0)))

    async def set_led(self, address: str, color: tuple[int, int, int]) -> bool:
        client = self.clients.get(address)
        if client is None:
            self.logger.error(f"Could not find client {address}")
            return False

        payload: bytes = struct.pack(">BBB", *color)
        await client.write_gatt_char(self.LED_CHAR, payload)
        return True

    async def run(self):
        devices: list[BLEDevice] = await self.scan()
        await asyncio.gather(*(self.connect(device) for device in devices))
