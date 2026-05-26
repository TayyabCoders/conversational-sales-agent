import asyncio
from app.configs.database_config import Database

# ⚠️ UPDATE THESE VALUES according to your local DB
MASTER_DB_CONFIG = {
    "username": "user",
    "password": "1234",
    "host": "localhost",
    "port": 5433,
    "database": "postgres",
}

# Replica optional – same DB used for manual testing
REPLICA_DB_CONFIG = {
    "username": "",
    "password": "",
    "host": "",
    "port": "",
    "database": "",
}

async def run_tests():
    print("=== Database Manual Tests ===")

    # Initialize Database
    try:
        db = Database(
            master_config=MASTER_DB_CONFIG,
            replica_config=REPLICA_DB_CONFIG,
        )
        print("1. Database initialized: PASS")
    except Exception as e:
        print(f"1. Database initialized: FAIL ({e})")
        return

    # Connect
    try:
        await db.connect()
        print("2. Connect: PASS")
    except Exception as e:
        print(f"2. Connect: FAIL ({e})")
        return

    # Health Check
    try:
        health = db.health_check()
        assert "status" in health
        assert health["status"] == "healthy"
        print("3. Health check: PASS")
        print("   Health info:", health)
    except Exception as e:
        print(f"3. Health check: FAIL ({e})")

    # Get Session
    try:
        session = db.get_session()
        assert session is not None
        print("4. Get session: PASS")
    except Exception as e:
        print(f"4. Get session: FAIL ({e})")

    # Read Query (Replica preferred)
    try:
        result = session.execute("SELECT 1").scalar()
        assert result == 1
        print("5. Read query (SELECT): PASS")
    except Exception as e:
        print(f"5. Read query (SELECT): FAIL ({e})")

    # Write Query (Master)
    try:
        session.execute("CREATE TEMP TABLE IF NOT EXISTS test_table (id INT)")
        session.execute("INSERT INTO test_table (id) VALUES (1)")
        session.commit()
        print("6. Write query (INSERT): PASS")
    except Exception as e:
        session.rollback()
        print(f"6. Write query (INSERT): FAIL ({e})")

    # Read After Write
    try:
        value = session.execute("SELECT id FROM test_table").scalar()
        assert value == 1
        print("7. Read after write: PASS")
    except Exception as e:
        print(f"7. Read after write: FAIL ({e})")

    # Disconnect
    try:
        await db.disconnect()
        print("8. Disconnect: PASS")
    except Exception as e:
        print(f"8. Disconnect: FAIL ({e})")

    # Session after disconnect (should fail)
    try:
        db.get_session()
        print("9. Get session after disconnect: FAIL (should raise error)")
    except RuntimeError:
        print("9. Get session after disconnect: PASS")

if __name__ == "__main__":
    asyncio.run(run_tests())