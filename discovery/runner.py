import os
import itertools
from datetime import datetime, timezone

import crud
from discovery.base import BaseDiscoveryProvider, ProviderRateLimitError, ProviderUnavailableError
from discovery.local_provider import LocalProvider
from discovery.fullcontact_provider import FullContactProvider


def _now():
    return datetime.now(timezone.utc)


def _build_default_providers() -> list[BaseDiscoveryProvider]:
    """Build the default provider list based on available configuration."""
    providers: list[BaseDiscoveryProvider] = [LocalProvider()]
    fc = FullContactProvider()
    if fc.is_available():
        providers.append(fc)
    return providers


def run_discovery(
    new_person_id: str | None = None,
    providers: list[BaseDiscoveryProvider] | None = None,
    staleness_days: int | None = None,
    quiet: bool = False,
) -> dict:
    """
    Run connection discovery across people pairs.

    Args:
        new_person_id: If given, only discover connections between this person
                       and all other existing people. If None, scan all pairs.
        providers:     List of provider instances to use. Defaults to
                       LocalProvider + any configured OSINT providers.
        staleness_days: Skip pairs whose last_checked is within this many days.
                        Defaults to DISCOVERY_STALENESS_DAYS env var (default 7).
        quiet:         If True, suppress per-pair progress output.

    Returns:
        {
            "pairs_checked": int,
            "pairs_skipped_stale": int,
            "connections_found": int,
            "errors": [(person_a_name, person_b_name, provider_name, error_msg)]
        }
    """
    if providers is None:
        providers = _build_default_providers()

    if staleness_days is None:
        staleness_days = int(os.getenv("DISCOVERY_STALENESS_DAYS", "7"))

    # Active providers (mutable — rate-limited ones get removed mid-run)
    active_providers = [p for p in providers if p.is_available()]

    summary = {
        "pairs_checked": 0,
        "pairs_skipped_stale": 0,
        "connections_found": 0,
        "errors": [],
    }

    all_people = crud.find_all()

    # Build the list of pairs to process
    if new_person_id:
        subject = crud.find_by_id(new_person_id)
        if not subject:
            return summary
        others = [p for p in all_people if str(p["_id"]) != new_person_id]
        pairs = [(subject, other) for other in others]
    else:
        pairs = list(itertools.combinations(all_people, 2))

    for person_a, person_b in pairs:
        id_a = str(person_a["_id"])
        id_b = str(person_b["_id"])
        name_a = person_a.get("name", id_a[:8])
        name_b = person_b.get("name", id_b[:8])

        # Staleness guard
        last_checked = crud.get_last_checked(id_a, id_b)
        if last_checked is not None:
            age_days = (_now() - last_checked.replace(tzinfo=timezone.utc)).days
            if age_days < staleness_days:
                summary["pairs_skipped_stale"] += 1
                continue

        summary["pairs_checked"] += 1
        pair_links_found = 0

        for provider in list(active_providers):  # copy so we can remove safely
            try:
                links = provider.find_links(person_a, person_b)
                if links:
                    for lnk in links:
                        lnk["provider"] = provider.name
                    crud.upsert_connection(id_a, id_b, links, provider.name)
                    pair_links_found += len(links)
                    summary["connections_found"] += len(links)
                else:
                    # Still record that this provider ran (updates last_checked)
                    crud.upsert_connection(id_a, id_b, [], provider.name)

            except ProviderRateLimitError:
                if not quiet:
                    print(f"  [!] {provider.name}: rate limited — disabling for this run")
                active_providers.remove(provider)

            except ProviderUnavailableError as exc:
                summary["errors"].append((name_a, name_b, provider.name, str(exc)))

            except Exception as exc:  # noqa: BLE001 — one pair failure must not stop the batch
                summary["errors"].append((name_a, name_b, provider.name, str(exc)))

        if not quiet:
            status = f"{pair_links_found} link(s)" if pair_links_found else "no links"
            print(f"  {name_a} ↔ {name_b}: {status}")

    return summary


def osint_providers_available() -> bool:
    """Return True if at least one non-local provider is configured."""
    return FullContactProvider().is_available()


def build_osint_providers() -> list[BaseDiscoveryProvider]:
    """Return only OSINT (non-local) providers that are available."""
    providers = []
    fc = FullContactProvider()
    if fc.is_available():
        providers.append(fc)
    return providers
