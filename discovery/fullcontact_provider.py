import os
import requests
from discovery.base import BaseDiscoveryProvider, ProviderUnavailableError, ProviderRateLimitError

_ENRICH_URL = "https://api.fullcontact.com/v3/person.enrich"


class FullContactProvider(BaseDiscoveryProvider):
    """
    Discovers connections by enriching both people via the FullContact
    Person Enrich API, then comparing the returned profile data.

    Requires FULLCONTACT_API_KEY in the environment (or passed to __init__).
    Set it in .env to enable this provider.

    What it compares after enrichment:
      - Social handles returned by the API (may surface handles not in our DB)
      - Employer/organization names
      - Current city/region
    """

    name = "fullcontact"

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.getenv("FULLCONTACT_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self._api_key)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _build_request_body(self, person: dict) -> dict:
        body: dict = {}
        emails = person.get("emails")
        if emails:
            body["emails"] = list(emails)
        phones = person.get("phones")
        if phones:
            body["phones"] = list(phones)
        # Pass social handles as location hints
        social = []
        for sp in person.get("social_profiles") or []:
            if isinstance(sp, dict) and sp.get("platform") and sp.get("username"):
                social.append({
                    "type": sp["platform"].lower(),
                    "userid": sp.get("profile_id") or "",
                    "username": sp["username"],
                    "url": sp.get("url") or "",
                })
        if social:
            body["social"] = social
        if person.get("name"):
            body["person"] = {"name": {"full": person["name"]}}
        return body

    def _enrich(self, person: dict) -> dict:
        """Call the FullContact Person Enrich endpoint. Returns the response dict."""
        body = self._build_request_body(person)
        if not body:
            return {}
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = requests.post(_ENRICH_URL, json=body, headers=headers, timeout=15)
        except requests.ConnectionError as e:
            raise ProviderUnavailableError(f"FullContact unreachable: {e}") from e
        except requests.Timeout as e:
            raise ProviderUnavailableError(f"FullContact timeout: {e}") from e

        if resp.status_code == 429:
            raise ProviderRateLimitError("FullContact rate limit reached")
        if resp.status_code == 404:
            # Person not found in FullContact — not an error, just no data
            return {}
        if not resp.ok:
            raise ProviderUnavailableError(
                f"FullContact returned HTTP {resp.status_code}: {resp.text[:200]}"
            )
        return resp.json()

    # ── Comparison helpers ────────────────────────────────────────────────────

    @staticmethod
    def _social_handles(enriched: dict) -> set[str]:
        """Extract 'platform:username' keys from enriched profile details."""
        handles = set()
        for sp in enriched.get("details", {}).get("profiles", []) or []:
            plat = (sp.get("network") or "").lower()
            username = sp.get("username") or sp.get("userid") or ""
            if plat and username:
                handles.add(f"{plat}:{username}")
        return handles

    @staticmethod
    def _employers(enriched: dict) -> set[str]:
        employers = set()
        for emp in enriched.get("details", {}).get("employment", []) or []:
            name = (emp.get("name") or "").strip().lower()
            if name:
                employers.add(name)
        return employers

    @staticmethod
    def _locations(enriched: dict) -> set[str]:
        locs = set()
        for loc in enriched.get("details", {}).get("locations", []) or []:
            city = (loc.get("city") or "").strip().lower()
            region = (loc.get("region") or "").strip().lower()
            key = f"{city},{region}".strip(",")
            if key:
                locs.add(key)
        return locs

    # ── Main interface ────────────────────────────────────────────────────────

    def find_links(self, person_a: dict, person_b: dict) -> list[dict]:
        enriched_a = self._enrich(person_a)
        enriched_b = self._enrich(person_b)

        if not enriched_a or not enriched_b:
            return []

        links = []

        # Shared social handles (from API, may be richer than our local data)
        handles_a = self._social_handles(enriched_a)
        handles_b = self._social_handles(enriched_b)
        for key in handles_a & handles_b:
            platform, username = key.split(":", 1)
            links.append({
                "type": "shared_social_profile",
                "value": username,
                "platform": platform,
            })

        # Shared employer
        for emp in self._employers(enriched_a) & self._employers(enriched_b):
            links.append({"type": "shared_employer", "value": emp})

        # Shared location (city+region)
        for loc in self._locations(enriched_a) & self._locations(enriched_b):
            links.append({"type": "shared_location", "value": loc})

        return links
