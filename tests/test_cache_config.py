import asyncio
from app.configs.cache_config import RedisCache

async def run_tests():
    print("=== RedisCache Manual Tests ===")

    # Initialize cache (cluster mode)
    cache = RedisCache(cluster_mode=False, host="localhost", port=7004)
    print("1. Initialized RedisCache (single node)")

    # Connect
    try:
        await cache.connect()
        print("2. Connect: PASS")
    except Exception as e:
        print(f"2. Connect: FAIL ({e})")

    # Set / Get JSON value
    try:
        await cache.set("test_json", {"a": 1, "b": 2})
        value = await cache.get("test_json")
        assert value == {"a": 1, "b": 2}
        print("3. Set/Get JSON: PASS")
    except Exception as e:
        print(f"3. Set/Get JSON: FAIL ({e})")

    # Set / Get non-JSON (pickle)
    try:
        await cache.set("test_pickle", set([1,2,3]))
        value = await cache.get("test_pickle")
        assert value == set([1,2,3])
        print("4. Set/Get Pickle: PASS")
    except Exception as e:
        print(f"4. Set/Get Pickle: FAIL ({e})")

    # Set without serialization
    try:
        await cache.set("test_raw", 123, serialize=False)
        value = await cache.get("test_raw")
        assert value == "123"
        print("5. Set/Get Raw: PASS")
    except Exception as e:
        print(f"5. Set/Get Raw: FAIL ({e})")

    # Get non-existing key with default
    try:
        value = await cache.get("non_existing", default="NA")
        assert value == "NA"
        print("6. Get non-existing key: PASS")
    except Exception as e:
        print(f"6. Get non-existing key: FAIL ({e})")

    # Delete key
    try:
        await cache.set("del_key", "to_delete")
        deleted = await cache.delete("del_key")
        assert deleted is True
        print("7. Delete existing key: PASS")
    except Exception as e:
        print(f"7. Delete existing key: FAIL ({e})")

    # Delete non-existing key
    try:
        deleted = await cache.delete("no_key")
        assert deleted is False
        print("8. Delete non-existing key: PASS")
    except Exception as e:
        print(f"8. Delete non-existing key: FAIL ({e})")

    # Exists
    try:
        await cache.set("exists_key", 1)
        exists = await cache.exists("exists_key")
        assert exists is True
        exists = await cache.exists("no_key")
        assert exists is False
        print("9. Exists key check: PASS")
    except Exception as e:
        print(f"9. Exists key check: FAIL ({e})")

    # Expire / TTL
    try:
        await cache.set("ttl_key", "test")
        await cache.expire("ttl_key", 5)
        ttl = await cache.ttl("ttl_key")
        assert ttl <= 5
        ttl_non = await cache.ttl("non_key")
        assert ttl_non == -1
        print("10. Expire/TTL: PASS")
    except Exception as e:
        print(f"10. Expire/TTL: FAIL ({e})")

    # Clear pattern
    try:
        await cache.set("pattern_a", 1)
        await cache.set("pattern_b", 2)
        cleared = await cache.clear_pattern("pattern_*")
        assert cleared >= 2
        print("11. Clear pattern: PASS")
    except Exception as e:
        print(f"11. Clear pattern: FAIL ({e})")

    # Increment
    try:
        await cache.set("counter", 5)
        new_val = await cache.increment("counter", 3)
        assert new_val == 8
        new_val2 = await cache.increment("new_counter")
        assert new_val2 == 1
        print("12. Increment: PASS")
    except Exception as e:
        print(f"12. Increment: FAIL ({e})")

    # Connected property
    try:
        assert cache.connected is True
        print("13. Connected property: PASS")
    except Exception as e:
        print(f"13. Connected property: FAIL ({e})")

    # Health check
    try:
        health = cache.health_check()
        assert "status" in health and "mode" in health
        print("14. Health check: PASS")
    except Exception as e:
        print(f"14. Health check: FAIL ({e})")

    # Disconnect
    try:
        await cache.disconnect()
        assert cache.connected is False
        print("15. Disconnect: PASS")
    except Exception as e:
        print(f"15. Disconnect: FAIL ({e})")

if __name__ == "__main__":
    asyncio.run(run_tests())