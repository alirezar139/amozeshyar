from kombu.transport import redis as redis_transport


def test_celery_redis_transport_accepts_installed_redis_client():
    # kombu checks the redis-py version only when the worker opens its broker channel,
    # so a mismatched pair passes every other test and crash-loops the worker in production.
    channel = redis_transport.Channel.__new__(redis_transport.Channel)
    channel.global_keyprefix = ""
    assert channel._get_client() is not None
