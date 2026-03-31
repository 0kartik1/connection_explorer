#!/usr/bin/env python3
"""
People Details Manager — CLI
Usage:  python app.py <command> [options]
"""

import argparse
import sys
import crud
import display


# ── Helpers ───────────────────────────────────────────────────────────────────

def _input_list(prompt: str) -> list:
    """Prompt for comma-separated values; return a list (empty if blank)."""
    raw = input(prompt).strip()
    if not raw:
        return []
    return [v.strip() for v in raw.split(",") if v.strip()]


def _input_addresses() -> list:
    """Interactively collect one or more addresses."""
    addresses = []
    print("  Enter addresses (blank label+value to stop):")
    while True:
        label = input("    Label (e.g. home, work) [blank to stop]: ").strip()
        if not label:
            break
        value = input("    Address value: ").strip()
        if value:
            addresses.append({"label": label, "value": value})
    return addresses


def _input_id_cards() -> list:
    """Interactively collect one or more ID card entries."""
    cards = []
    print("  Enter ID cards (blank type to stop):")
    while True:
        ctype = input("    Card type (e.g. aadhaar, passport) [blank to stop]: ").strip()
        if not ctype:
            break
        number = input("    Card number: ").strip()
        if number:
            cards.append({"type": ctype, "number": number})
    return cards


def _input_extras() -> dict:
    """Collect arbitrary extra key-value fields."""
    extras = {}
    print("  Extra fields (blank key to stop):")
    while True:
        key = input("    Field name [blank to stop]: ").strip()
        if not key:
            break
        val = input(f"    {key}: ").strip()
        extras[key] = val
    return extras


def _pick_one(matches: list, id_or_name: str) -> dict | None:
    """If multiple matches, let the user pick one. Returns chosen doc or None."""
    if not matches:
        print(f"No record found matching '{id_or_name}'.")
        return None
    if len(matches) == 1:
        return matches[0]
    print(f"Multiple records match '{id_or_name}':")
    for i, m in enumerate(matches, 1):
        print(f"  {i}. {m.get('name', '?')}  [{m['_id']}]")
    choice = input("Pick number (or blank to cancel): ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(matches)):
        print("Cancelled.")
        return None
    return matches[int(choice) - 1]


def _print_discovery_summary(summary: dict) -> None:
    checked = summary["pairs_checked"]
    skipped = summary["pairs_skipped_stale"]
    found = summary["connections_found"]
    errors = summary["errors"]
    print(
        f"  Discovery done — {checked} pair(s) checked, "
        f"{skipped} skipped (recent), {found} link(s) found."
    )
    for name_a, name_b, provider, msg in errors:
        print(f"  [!] {provider} error on {name_a} ↔ {name_b}: {msg}")


def _build_people_cache(connections: list) -> dict:
    """Build {id_str: name} cache for all person IDs appearing in connections."""
    ids = set()
    for conn in connections:
        ids.add(str(conn["person_a_id"]))
        ids.add(str(conn["person_b_id"]))
    cache = {}
    for id_str in ids:
        doc = crud.find_by_id(id_str)
        if doc:
            cache[id_str] = doc.get("name", f"[{id_str[:8]}...]")
    return cache


# ── People commands ───────────────────────────────────────────────────────────

def cmd_add(_args):
    print("=== Add New Person ===")
    data = {}

    name = input("Name: ").strip()
    if not name:
        print("Name is required.")
        return
    data["name"] = name

    phones = _input_list("Phones (comma-separated, blank to skip): ")
    if phones:
        data["phones"] = phones

    emails = _input_list("Emails (comma-separated, blank to skip): ")
    if emails:
        data["emails"] = emails

    addresses = _input_addresses()
    if addresses:
        data["addresses"] = addresses

    id_cards = _input_id_cards()
    if id_cards:
        data["id_cards"] = id_cards

    notes = input("Notes (blank to skip): ").strip()
    if notes:
        data["notes"] = notes

    extras = _input_extras()
    data.update(extras)

    inserted_id = crud.add_person(data)
    print(f"\nSaved. ID: {inserted_id}")

    # Auto-run local discovery against all existing people
    from discovery import run_discovery, osint_providers_available, build_osint_providers
    from discovery.local_provider import LocalProvider

    all_people = crud.find_all()
    if len(all_people) > 1:
        print("\nRunning local connection discovery...")
        summary = run_discovery(
            new_person_id=inserted_id,
            providers=[LocalProvider()],
            staleness_days=0,
            quiet=False,
        )
        _print_discovery_summary(summary)

        if osint_providers_available():
            answer = input("\nRun OSINT enrichment discovery? (y/n) [n]: ").strip().lower()
            if answer == "y":
                print("Running OSINT discovery...")
                summary2 = run_discovery(
                    new_person_id=inserted_id,
                    providers=build_osint_providers(),
                    staleness_days=0,
                    quiet=False,
                )
                _print_discovery_summary(summary2)


def cmd_list(_args):
    people = crud.find_all()
    if not people:
        print("No records found.")
        return
    print(f"{'ID':<26}  {'Name':<30}  Phones / Emails")
    print("─" * 80)
    for p in people:
        display.print_summary(p)


def cmd_view(args):
    matches = crud.resolve(args.id_or_name)
    person = _pick_one(matches, args.id_or_name)
    if person:
        display.print_full(person)


def cmd_search(args):
    results = crud.search(args.field, args.value)
    if not results:
        print(f"No results for {args.field}='{args.value}'.")
        return
    print(f"{len(results)} result(s):")
    for p in results:
        display.print_summary(p)


def cmd_update(args):
    matches = crud.resolve(args.id_or_name)
    person = _pick_one(matches, args.id_or_name)
    if not person:
        return

    print(f"=== Update: {person.get('name', person['_id'])} ===")
    print("Enter new values (blank = keep existing):\n")

    updates = {}

    name = input(f"Name [{person.get('name', '')}]: ").strip()
    if name:
        updates["name"] = name

    phones_raw = input(f"Phones [{', '.join(person.get('phones', []))}]: ").strip()
    if phones_raw:
        updates["phones"] = [v.strip() for v in phones_raw.split(",") if v.strip()]

    emails_raw = input(f"Emails [{', '.join(person.get('emails', []))}]: ").strip()
    if emails_raw:
        updates["emails"] = [v.strip() for v in emails_raw.split(",") if v.strip()]

    print("  Update addresses? (y/n)", end=" ")
    if input().strip().lower() == "y":
        updates["addresses"] = _input_addresses()

    print("  Update ID cards? (y/n)", end=" ")
    if input().strip().lower() == "y":
        updates["id_cards"] = _input_id_cards()

    notes = input(f"Notes [{person.get('notes', '')}]: ").strip()
    if notes:
        updates["notes"] = notes

    extras = _input_extras()
    updates.update(extras)

    if not updates:
        print("Nothing to update.")
        return

    ok = crud.update_person(str(person["_id"]), updates)
    print("Updated." if ok else "Update failed.")


def cmd_delete(args):
    matches = crud.resolve(args.id_or_name)
    person = _pick_one(matches, args.id_or_name)
    if not person:
        return

    display.print_summary(person)
    confirm = input("Delete this record? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Cancelled.")
        return

    pid = str(person["_id"])
    removed = crud.delete_connections_for_person(pid)
    if removed:
        print(f"Removed {removed} connection record(s).")
    ok = crud.delete_person(pid)
    print("Deleted." if ok else "Delete failed.")


# ── Social commands ───────────────────────────────────────────────────────────

def cmd_social(args):
    dispatch = {
        "add": _social_add,
        "list": _social_list,
        "remove": _social_remove,
    }
    dispatch[args.social_cmd](args)


def _social_add(args):
    matches = crud.resolve(args.id_or_name)
    person = _pick_one(matches, args.id_or_name)
    if not person:
        return

    print(f"=== Add Social Profile: {person.get('name')} ===")
    platform = input("Platform (facebook/instagram/twitter/linkedin/other): ").strip().lower()
    if not platform:
        print("Platform is required.")
        return
    username = input("Username/handle: ").strip()
    if not username:
        print("Username is required.")
        return
    url = input("Profile URL (blank to skip): ").strip()
    profile_id = input("Profile ID (blank to skip): ").strip()

    profile: dict = {"platform": platform, "username": username}
    if url:
        profile["url"] = url
    if profile_id:
        profile["profile_id"] = profile_id

    ok = crud.add_social_profile(str(person["_id"]), profile)
    print("Social profile added." if ok else "Failed to add social profile.")


def _social_list(args):
    matches = crud.resolve(args.id_or_name)
    person = _pick_one(matches, args.id_or_name)
    if not person:
        return

    profiles = crud.get_social_profiles(str(person["_id"]))
    print(f"Social profiles for {person.get('name')}:")
    display.print_social_profiles(profiles)


def _social_remove(args):
    matches = crud.resolve(args.id_or_name)
    person = _pick_one(matches, args.id_or_name)
    if not person:
        return

    profiles = crud.get_social_profiles(str(person["_id"]))
    if not profiles:
        print("No social profiles to remove.")
        return

    print(f"Social profiles for {person.get('name')}:")
    for i, p in enumerate(profiles, 1):
        plat = p.get("platform", "?")
        user = p.get("username", "?")
        print(f"  {i}. [{plat}] @{user}")

    choice = input("Remove number (blank to cancel): ").strip()
    if not choice.isdigit() or not (1 <= int(choice) <= len(profiles)):
        print("Cancelled.")
        return

    target = profiles[int(choice) - 1]
    ok = crud.remove_social_profile(
        str(person["_id"]),
        target["platform"],
        target["username"],
    )
    print("Removed." if ok else "Remove failed.")


# ── Connections commands ──────────────────────────────────────────────────────

def cmd_connections(args):
    dispatch = {
        "list": _connections_list,
        "show": _connections_show,
        "run": _connections_run,
    }
    dispatch[args.conn_cmd](args)


def _connections_list(args):
    matches = crud.resolve(args.id_or_name)
    person = _pick_one(matches, args.id_or_name)
    if not person:
        return

    pid = str(person["_id"])
    connections = crud.find_connections_for_person(pid)

    if not connections:
        print(f"No connections found for {person.get('name')}.")
        return

    print(f"Connections for {person.get('name')} ({len(connections)}):")
    print("─" * 60)
    cache = _build_people_cache(connections)
    for conn in connections:
        display.print_connection(conn, pid, cache)


def _connections_show(args):
    matches_a = crud.resolve(args.person_a)
    person_a = _pick_one(matches_a, args.person_a)
    if not person_a:
        return

    matches_b = crud.resolve(args.person_b)
    person_b = _pick_one(matches_b, args.person_b)
    if not person_b:
        return

    conn = crud.find_connection_between(str(person_a["_id"]), str(person_b["_id"]))
    if not conn:
        print(f"No connection record between {person_a.get('name')} and {person_b.get('name')}.")
        print("Run discovery first:  python app.py connections run --all")
        return

    cache = {
        str(person_a["_id"]): person_a.get("name", "?"),
        str(person_b["_id"]): person_b.get("name", "?"),
    }
    print(f"Connection: {person_a.get('name')} ↔ {person_b.get('name')}")
    print("─" * 60)
    display.print_connection(conn, str(person_a["_id"]), cache)


def _connections_run(args):
    from discovery import run_discovery

    if args.all:
        print("Running full pairwise discovery scan...")
        summary = run_discovery(quiet=False)
    else:
        matches = crud.resolve(args.person)
        person = _pick_one(matches, args.person)
        if not person:
            return
        print(f"Running discovery for {person.get('name')}...")
        summary = run_discovery(new_person_id=str(person["_id"]), quiet=False)

    _print_discovery_summary(summary)


# ── Argument parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="app.py",
        description="People Details Manager — local MongoDB CLI",
    )
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    # ── People commands
    sub.add_parser("add", help="Add a new person (interactive)")
    sub.add_parser("list", help="List all people")

    p_view = sub.add_parser("view", help="View full details of a person")
    p_view.add_argument("id_or_name", help="ObjectId or name (partial match)")

    p_search = sub.add_parser("search", help="Search by any field")
    p_search.add_argument("--field", required=True, help="Field name to search in")
    p_search.add_argument("--value", required=True, help="Value to search for")

    p_update = sub.add_parser("update", help="Update a person's details (interactive)")
    p_update.add_argument("id_or_name", help="ObjectId or name (partial match)")

    p_delete = sub.add_parser("delete", help="Delete a person's record")
    p_delete.add_argument("id_or_name", help="ObjectId or name (partial match)")

    # ── Social subcommands
    p_social = sub.add_parser("social", help="Manage social profiles")
    social_sub = p_social.add_subparsers(dest="social_cmd", metavar="action")
    social_sub.required = True

    ss_add = social_sub.add_parser("add", help="Add a social profile to a person")
    ss_add.add_argument("id_or_name")

    ss_list = social_sub.add_parser("list", help="List social profiles of a person")
    ss_list.add_argument("id_or_name")

    ss_remove = social_sub.add_parser("remove", help="Remove a social profile")
    ss_remove.add_argument("id_or_name")

    # ── Connections subcommands
    p_conn = sub.add_parser("connections", help="Manage and discover connections")
    conn_sub = p_conn.add_subparsers(dest="conn_cmd", metavar="action")
    conn_sub.required = True

    cs_list = conn_sub.add_parser("list", help="List connections for a person")
    cs_list.add_argument("id_or_name")

    cs_show = conn_sub.add_parser("show", help="Show connection between two people")
    cs_show.add_argument("person_a")
    cs_show.add_argument("person_b")

    cs_run = conn_sub.add_parser("run", help="Run connection discovery")
    cs_run_grp = cs_run.add_mutually_exclusive_group(required=True)
    cs_run_grp.add_argument(
        "--person", metavar="ID_OR_NAME",
        help="Discover for one person vs. all others",
    )
    cs_run_grp.add_argument(
        "--all", action="store_true",
        help="Full pairwise scan of all people",
    )

    return parser


COMMANDS = {
    "add": cmd_add,
    "list": cmd_list,
    "view": cmd_view,
    "search": cmd_search,
    "update": cmd_update,
    "delete": cmd_delete,
    "social": cmd_social,
    "connections": cmd_connections,
}


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        COMMANDS[args.command](args)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
