import asyncio
import logging

from bleak import BleakClient, BleakScanner
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
        devices: list[BLEDevice] = await BleakScanner.discover(
            timeout=timeout, service_uuids=[self.SERVICES_UUID]
        )
        return devices
    
    async def connect(self, device: BLEDevice):
        self.logger.info(f"Connecting to {device.address}")
        async with BleakClient(device, self.on_disconnected) as client:
            await client.start_notify(self.BUTTON_CHAR, self.on_button)
            await client.start_notify(self.IR_CHAR, self.on_ir)
            self.clients[client.address] = client
            await asyncio.sleep(1e9)
    
    def on_disconnected(self, client: BleakClient):
        self.logger.info(f"Client {client.address} disconnected")
    
    def on_button(self, _, data: bytes):
        self.logger.info(f"Received button update: {data}")
    
    def on_ir(self, _, data: bytes):
        self.logger.info(f"Received IR update: {data}")

    async def run(self):
        devices: list[BLEDevice] = await self.scan()
        await asyncio.gather(
            *(
                self.connect(device)
                for device in devices
            )
        )
