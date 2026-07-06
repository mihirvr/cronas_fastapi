from __future__ import annotations

import json
from typing import Iterable

from kafka import KafkaConsumer, KafkaProducer

from shared.config import get_settings


class KafkaBus:
    def __init__(self) -> None:
        settings = get_settings()
        self.bootstrap_servers = settings.kafka_bootstrap_servers

    def producer(self) -> KafkaProducer:
        return KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        )

    def consumer(self, topics: Iterable[str], group_id: str) -> KafkaConsumer:
        return KafkaConsumer(
            *topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        )
