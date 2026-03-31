import re
from datetime import datetime, timezone
from bson import ObjectId
from bson.errors import InvalidId
from db import get_collection, get_connections_collection


def _now():
    return datetime.now(timezone.utc)


def _col():
    return get_collection()


def _conn_col():
    return get_connections_collection()


def _canonical_pair(id_a: str, id_b: str) -> tuple[str, str]:
    """Return (smaller_hex, larger_hex) to enforce a canonical pair ordering."""
    return (id_a, id_b) if id_a < id_b else (id_b, id_a)


# ── Create ────────────────────────────────────────────────────────────────────

def add_person(data: dict) -> str:
    """Insert a new person document. Returns the inserted _id as a string."""
    data = dict(data)
    data["created_at"] = _now()
    data["updated_at"] = _now()
    result = _col().insert_one(data)
    return str(result.inserted_id)


# ── Read ──────────────────────────────────────────────────────────────────────

def find_all() -> list:
    """Return all people sorted by name."""
    return list(_col().find().sort("name", 1))


def find_by_id(id_str: str) -> dict | None:
    """Fetch a single document by its ObjectId string."""
    try:
        oid = ObjectId(id_str)
    except InvalidId:
        return None
    return _col().find_one({"_id": oid})


def find_by_name(name: str) -> list:
    """Case-insensitive partial match on the name field."""
    pattern = re.compile(re.escape(name), re.IGNORECASE)
    return list(_col().find({"name": pattern}))


def search(field: str, value: str) -> list:
    """Search any field by case-insensitive substring match."""
    pattern = re.compile(re.escape(value), re.IGNORECASE)
    return list(_col().find({field: pattern}))


def resolve(id_or_name: str) -> list:
    """
    Return matching documents given either an ObjectId string or a name.
    Always returns a list (may contain 0, 1, or multiple results).
    """
    doc = find_by_id(id_or_name)
    if doc:
        return [doc]
    return find_by_name(id_or_name)


# ── Update ────────────────────────────────────────────────────────────────────

def update_person(id_str: str, updates: dict) -> bool:
    """
    Apply field updates to a document by ObjectId string.
    Returns True if a document was modified.
    """
    try:
        oid = ObjectId(id_str)
    except InvalidId:
        return False
    updates["updated_at"] = _now()
    result = _col().update_one({"_id": oid}, {"$set": updates})
    return result.modified_count > 0


# ── Delete ────────────────────────────────────────────────────────────────────

def delete_person(id_str: str) -> bool:
    """Delete a document by ObjectId string. Returns True if deleted."""
    try:
        oid = ObjectId(id_str)
    except InvalidId:
        return False
    result = _col().delete_one({"_id": oid})
    return result.deleted_count > 0


# ── Social Profiles ───────────────────────────────────────────────────────────

def add_social_profile(id_str: str, profile: dict) -> bool:
    """Append one social profile dict to a person's social_profiles list."""
    try:
        oid = ObjectId(id_str)
    except InvalidId:
        return False
    result = _col().update_one(
        {"_id": oid},
        {"$push": {"social_profiles": profile}, "$set": {"updated_at": _now()}},
    )
    return result.modified_count > 0


def remove_social_profile(id_str: str, platform: str, username: str) -> bool:
    """Remove a social profile from a person's list by platform + username match."""
    try:
        oid = ObjectId(id_str)
    except InvalidId:
        return False
    result = _col().update_one(
        {"_id": oid},
        {
            "$pull": {"social_profiles": {"platform": platform, "username": username}},
            "$set": {"updated_at": _now()},
        },
    )
    return result.modified_count > 0


def get_social_profiles(id_str: str) -> list:
    """Return the social_profiles list for a person, or []."""
    doc = find_by_id(id_str)
    if not doc:
        return []
    return doc.get("social_profiles", [])


# ── Connections ───────────────────────────────────────────────────────────────

def upsert_connection(id_a: str, id_b: str, new_links: list, provider: str) -> str:
    """
    Insert or update a connection document for the given pair.
    Merges new_links into existing links (deduplicated by type+value+provider).
    Returns the _id string of the connection doc.
    """
    small, large = _canonical_pair(id_a, id_b)
    oid_a, oid_b = ObjectId(small), ObjectId(large)

    existing = _conn_col().find_one({"person_a_id": oid_a, "person_b_id": oid_b})
    existing_keys = set()
    if existing:
        for lnk in existing.get("links", []):
            existing_keys.add((lnk.get("type"), lnk.get("value"), lnk.get("provider")))

    deduped = [
        lnk for lnk in new_links
        if (lnk.get("type"), lnk.get("value"), lnk.get("provider")) not in existing_keys
    ]

    now = _now()
    update = {
        "$set": {"last_checked": now},
        "$setOnInsert": {"discovered_at": now},
        "$addToSet": {"providers_run": provider},
    }
    if deduped:
        update["$push"] = {"links": {"$each": deduped}}

    result = _conn_col().update_one(
        {"person_a_id": oid_a, "person_b_id": oid_b},
        update,
        upsert=True,
    )
    if result.upserted_id:
        return str(result.upserted_id)
    doc = _conn_col().find_one({"person_a_id": oid_a, "person_b_id": oid_b}, {"_id": 1})
    return str(doc["_id"])


def find_connections_for_person(id_str: str) -> list:
    """Return all connection docs where this person appears on either side."""
    try:
        oid = ObjectId(id_str)
    except InvalidId:
        return []
    return list(_conn_col().find({"$or": [{"person_a_id": oid}, {"person_b_id": oid}]}))


def find_connection_between(id_a: str, id_b: str) -> dict | None:
    """Return the connection doc for a specific pair, or None."""
    try:
        small, large = _canonical_pair(id_a, id_b)
        oid_a, oid_b = ObjectId(small), ObjectId(large)
    except InvalidId:
        return None
    return _conn_col().find_one({"person_a_id": oid_a, "person_b_id": oid_b})


def get_last_checked(id_a: str, id_b: str) -> datetime | None:
    """Return last_checked datetime for a pair, or None if never checked."""
    doc = find_connection_between(id_a, id_b)
    if doc:
        return doc.get("last_checked")
    return None


def delete_connections_for_person(id_str: str) -> int:
    """Remove all connection docs involving this person. Returns count deleted."""
    try:
        oid = ObjectId(id_str)
    except InvalidId:
        return 0
    result = _conn_col().delete_many(
        {"$or": [{"person_a_id": oid}, {"person_b_id": oid}]}
    )
    return result.deleted_count
