import logging
from typing import Callable

import paho.mqtt.client as mqtt


class MQTTGateway:
    def __init__(self, host: str, port: int = 1883) -> None:
        self.host: str = host
        self.port: int = port

        self.logger = logging.getLogger("MQTTGateway")

        self.mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)  # type: ignore
        self.mqttc.on_connect = self.on_connect
        self.mqttc.on_message = self.on_message

        self.listeners: dict[str, list[Callable[[mqtt.MQTTMessage], None]]] = {}

    def run(self):
        self.logger.info(f"Connecting to {self.host}:{self.port}")
        self.mqttc.connect(self.host, self.port)
        self.mqttc.loop_start()
        for topic in self.listeners.keys():
            self.logger.info(f"Subscribing to {topic}")
            self.mqttc.subscribe(topic)

    def on_connect(self, client, userdata, connect_flags, reason_code, properties):
        self.logger.info("Connected")

    def on_message(self, client: mqtt.Client, userdata, message: mqtt.MQTTMessage):
        topic: str = message.topic
        self.logger.info(f"New message in {topic}")
        for sub, listeners in self.listeners.items():
            if mqtt.topic_matches_sub(sub, topic):
                for listener in listeners:
                    listener(message)

    def add_listener(self, topic: str, callback: Callable[[mqtt.MQTTMessage], None]):
        if topic not in self.listeners:
            self.listeners[topic] = []
        self.listeners[topic].append(callback)

    def send(self, topic: str, message: bytes):
        self.mqttc.publish(topic, message)
