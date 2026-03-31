import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

_client = None


def _ensure_client():
    global _client
    if _client is None:
        uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        _client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        _client.server_info()


def get_collection():
    _ensure_client()
    db_name = os.getenv("DB_NAME", "people_db")
    return _client[db_name]["people"]


def get_connections_collection():
    _ensure_client()
    db_name = os.getenv("DB_NAME", "people_db")
    col = _client[db_name]["connections"]
    # Idempotent index creation
    col.create_index([("person_a_id", 1), ("person_b_id", 1)], unique=True)
    col.create_index([("person_a_id", 1)])
    col.create_index([("person_b_id", 1)])
    return col
