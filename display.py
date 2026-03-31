from datetime import datetime

# Fields handled with custom formatting (excluded from the generic "extras" dump)
_KNOWN_FIELDS = {
    "_id", "name", "phones", "emails", "addresses", "id_cards",
    "notes", "social_profiles", "created_at", "updated_at",
}

_PLATFORM_LABELS = {
    "facebook": "Facebook",
    "instagram": "Instagram",
    "twitter": "Twitter/X",
    "x": "Twitter/X",
    "linkedin": "LinkedIn",
}


def _fmt_dt(dt) -> str:
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    return str(dt)


def print_summary(person: dict) -> None:
    """One-line summary: ID  Name  |  phones  |  emails"""
    pid = str(person["_id"])
    name = person.get("name", "(no name)")
    phones = ", ".join(person.get("phones", [])) or "-"
    emails = ", ".join(person.get("emails", [])) or "-"
    print(f"[{pid}]  {name:<30}  ph: {phones:<20}  em: {emails}")


def print_social_profiles(profiles: list) -> None:
    """Print a formatted social profiles section."""
    if not profiles:
        print("  (no social profiles)")
        return
    # Group by platform
    by_platform: dict[str, list] = {}
    for p in profiles:
        plat = p.get("platform", "unknown")
        by_platform.setdefault(plat, []).append(p)
    for plat, entries in by_platform.items():
        label = _PLATFORM_LABELS.get(plat.lower(), plat.capitalize())
        for e in entries:
            username = e.get("username", "")
            url = e.get("url", "")
            pid = e.get("profile_id", "")
            parts = [f"@{username}" if username else ""]
            if url:
                parts.append(url)
            if pid:
                parts.append(f"id:{pid}")
            print(f"    {label:<12} {' | '.join(p for p in parts if p)}")


def print_connection(conn: dict, perspective_id: str, people_cache: dict) -> None:
    """
    Print a single connection doc from the perspective of one person.
    people_cache: {id_str: name} to avoid repeated DB lookups.
    """
    a_id = str(conn["person_a_id"])
    b_id = str(conn["person_b_id"])
    other_id = b_id if a_id == perspective_id else a_id
    other_name = people_cache.get(other_id, f"[{other_id[:8]}...]")

    links = conn.get("links", [])
    providers = ", ".join(conn.get("providers_run", []))
    last = _fmt_dt(conn.get("last_checked")) if conn.get("last_checked") else "never"

    print(f"  ↔  {other_name}")
    print(f"     {len(links)} link(s)  |  providers: {providers}  |  last checked: {last}")
    for lnk in links:
        ltype = lnk.get("type", "?")
        val = lnk.get("value", "")
        prov = lnk.get("provider", "")
        plat = lnk.get("platform", "")
        detail = f"[{plat}] " if plat else ""
        print(f"       • {ltype}: {detail}{val}  ({prov})")


def print_full(person: dict) -> None:
    """Formatted full record."""
    sep = "─" * 60
    print(sep)
    print(f"  ID      : {person['_id']}")
    print(f"  Name    : {person.get('name', '—')}")

    phones = person.get("phones")
    if phones:
        print(f"  Phones  : {', '.join(phones)}")

    emails = person.get("emails")
    if emails:
        print(f"  Emails  : {', '.join(emails)}")

    addresses = person.get("addresses")
    if addresses:
        print("  Addresses:")
        for addr in addresses:
            if isinstance(addr, dict):
                label = addr.get("label", "")
                value = addr.get("value", "")
                print(f"    [{label}] {value}" if label else f"    {value}")
            else:
                print(f"    {addr}")

    id_cards = person.get("id_cards")
    if id_cards:
        print("  ID Cards:")
        for card in id_cards:
            if isinstance(card, dict):
                ctype = card.get("type", "")
                num = card.get("number", "")
                print(f"    {ctype}: {num}" if ctype else f"    {num}")
            else:
                print(f"    {card}")

    social_profiles = person.get("social_profiles")
    if social_profiles:
        print("  Social:")
        print_social_profiles(social_profiles)

    notes = person.get("notes")
    if notes:
        print(f"  Notes   : {notes}")

    # Print any extra fields not in the known set
    extras = {k: v for k, v in person.items() if k not in _KNOWN_FIELDS}
    if extras:
        print("  Extra fields:")
        for k, v in extras.items():
            print(f"    {k}: {v}")

    created = person.get("created_at")
    updated = person.get("updated_at")
    if created:
        print(f"  Created : {_fmt_dt(created)}")
    if updated:
        print(f"  Updated : {_fmt_dt(updated)}")
    print(sep)
