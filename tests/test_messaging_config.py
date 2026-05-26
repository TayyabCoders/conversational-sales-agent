import asyncio
from app.configs.messaging_config import RabbitMQClient

async def run_tests():
    print("=== RabbitMQClient Manual Tests ===")

    # Initialize client
    client = RabbitMQClient(host="localhost", port=5672, username="admin", password="admin")
    print("1. Initialized RabbitMQClient")

    # Connect
    try:
        await client.connect()
        print("2. Connect: PASS")
    except Exception as e:
        print(f"2. Connect: FAIL ({e})")

    # Check connected property
    try:
        assert client.connected is True
        print("3. Connected property: PASS")
    except Exception as e:
        print(f"3. Connected property: FAIL ({e})")

    # Health check
    try:
        health = client.health_check()
        assert "status" in health and "host" in health
        print("4. Health check: PASS")
    except Exception as e:
        print(f"4. Health check: FAIL ({e})")

    # Publish message
    try:
        test_message = {"event": "test", "value": 123}
        result = await client.publish(exchange="test_exchange_manual", routing_key="test.key", message=test_message)
        assert result is True
        print("5. Publish message: PASS")
    except Exception as e:
        print(f"5. Publish message: FAIL ({e})")

    # Disconnect
    try:
        await client.disconnect()
        assert client.connected is False
        print("6. Disconnect: PASS")
    except Exception as e:
        print(f"6. Disconnect: FAIL ({e})")

if __name__ == "__main__":
    asyncio.run(run_tests())