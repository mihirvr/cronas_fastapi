from kafka.admin import KafkaAdminClient, NewTopic

from shared.config import get_settings


def main() -> None:
    settings = get_settings()
    admin = KafkaAdminClient(bootstrap_servers=settings.kafka_bootstrap_servers)
    topics = [
        NewTopic(name=settings.jobs_run_topic, num_partitions=1, replication_factor=1),
        NewTopic(name=settings.jobs_retry_topic, num_partitions=1, replication_factor=1),
        NewTopic(name=settings.jobs_dlq_topic, num_partitions=1, replication_factor=1),
    ]
    try:
        admin.create_topics(topics)
        print('Kafka topics created')
    except Exception as exc:
        print(f'Kafka topic creation skipped: {exc}')
    finally:
        admin.close()


if __name__ == '__main__':
    main()
