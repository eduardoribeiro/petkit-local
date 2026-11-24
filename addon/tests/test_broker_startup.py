"""Exercise the real TLS listener and amqtt's SSL context integration."""

from petkit_local.mqtt.broker import start_broker


async def test_broker_starts_with_tls(tmp_path):
    broker = await start_broker(
        port=0,
        tls=True,
        tls_port=0,
        certfile=str(tmp_path / "broker.crt"),
        keyfile=str(tmp_path / "broker.key"),
    )
    try:
        assert "tls" in broker.listeners_config
    finally:
        await broker.shutdown()
