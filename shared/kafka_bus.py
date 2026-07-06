from __future__ import annotations

import json
from typing import Iterable

from confluent_kafka import Consumer, Producer

from shared.config import get_settings


class KafkaBus:
    def __init__(self) -> None:
        settings = get_settings()
        self.bootstrap_servers = settings.kafka_bootstrap_servers

    def producer(self) -> Producer:
        # confluent-kafka doesn't accept a custom serializer function in the constructor
        # so we will wrap the send method or just configure the broker
        return Producer({'bootstrap.servers': self.bootstrap_servers})

    def consumer(self, topics: Iterable[str], group_id: str) -> Consumer:
        c = Consumer({
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': group_id,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False
        })
        c.subscribe(list(topics))
        return c
