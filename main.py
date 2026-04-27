import asyncio
import logging

from ble_gateway import BLEGateway
from mqtt_gateway import MQTTGateway


def main():
    logging.basicConfig(level=logging.INFO)
    ble = BLEGateway()
    mqtt = MQTTGateway()

    asyncio.run(ble.run())


if __name__ == "__main__":
    main()
