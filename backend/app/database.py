from pymongo import AsyncMongoClient

from app.config import get_settings


settings = get_settings()

client = None
db = None


async def connect_to_mongodb():
    global client, db

    client = AsyncMongoClient(settings.mongodb_url)

    # Test MongoDB connection
    await client.admin.command("ping")

    db = client[settings.mongodb_database]

    print(f"✅ Connected to MongoDB: {settings.mongodb_database}")


async def close_mongodb_connection():
    global client

    if client is not None:
        await client.close()
        client = None

    print("🔌 MongoDB connection closed")


def get_database():
    if db is None:
        raise RuntimeError("MongoDB database is not initialized")

    return db


# Temporary compatibility dependency.
# Existing routers currently import get_db.
async def get_db():
    return get_database()


async def create_indexes():
    database = get_database()

    # =========================
    # Users
    # =========================
    await database.users.create_index(
        "email",
        unique=True
    )

    # =========================
    # Complaints
    # =========================
    await database.complaints.create_index("citizen_id")
    await database.complaints.create_index("status")
    await database.complaints.create_index("category")
    await database.complaints.create_index("created_at")

    await database.complaints.create_index(
        [("location.geo", "2dsphere")]
    )

    # =========================
    # Incidents
    # =========================
    await database.incidents.create_index("status")
    await database.incidents.create_index("priority")
    await database.incidents.create_index("created_at")

    await database.incidents.create_index(
        [("location.geo", "2dsphere")]
    )

    # =========================
    # Incident Links
    # =========================
    await database.incident_links.create_index("complaint_a")
    await database.incident_links.create_index("complaint_b")
    await database.incident_links.create_index("status")

    print("✅ MongoDB indexes created")