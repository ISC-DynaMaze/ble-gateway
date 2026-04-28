import asyncio
import logging
import os

from gateway import Gateway


async def main():
    logging.basicConfig(level=logging.INFO)
    mqtt_host = os.environ.get("MQTT_HOST", "isc-coordinator.lan")
    mqtt_port = int(os.environ.get("MQTT_PORT", 1883))
    gateway: Gateway = Gateway(mqtt_host=mqtt_host, mqtt_port=mqtt_port)
    await gateway.run()


if __name__ == "__main__":
    asyncio.run(main())
