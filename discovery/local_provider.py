from discovery.base import BaseDiscoveryProvider


class LocalProvider(BaseDiscoveryProvider):
    """
    Free, zero-dependency provider that finds connections by comparing data
    already stored in the local MongoDB — no external API calls.

    Checks for overlaps in:
      - phones
      - emails
      - addresses (by address value string)
      - id_cards (by type:number key)
      - social_profiles (by platform:username key)
    """

    name = "local"

    def find_links(self, person_a: dict, person_b: dict) -> list[dict]:
        links = []

        # phones
        phones_a = set(person_a.get("phones") or [])
        phones_b = set(person_b.get("phones") or [])
        for val in phones_a & phones_b:
            links.append({"type": "shared_phone", "value": val})

        # emails
        emails_a = set(person_a.get("emails") or [])
        emails_b = set(person_b.get("emails") or [])
        for val in emails_a & emails_b:
            links.append({"type": "shared_email", "value": val})

        # addresses — compare the value string
        def addr_set(person):
            result = set()
            for addr in person.get("addresses") or []:
                if isinstance(addr, dict) and addr.get("value"):
                    result.add(addr["value"])
                elif isinstance(addr, str):
                    result.add(addr)
            return result

        for val in addr_set(person_a) & addr_set(person_b):
            links.append({"type": "shared_address", "value": val})

        # id_cards — compare "type:number" key
        def card_set(person):
            result = set()
            for card in person.get("id_cards") or []:
                if isinstance(card, dict):
                    key = f"{card.get('type', '')}:{card.get('number', '')}"
                    result.add(key)
            return result

        for val in card_set(person_a) & card_set(person_b):
            links.append({"type": "shared_id_card", "value": val})

        # social_profiles — compare "platform:username" key
        def social_set(person):
            result = {}
            for p in person.get("social_profiles") or []:
                if isinstance(p, dict) and p.get("platform") and p.get("username"):
                    key = f"{p['platform'].lower()}:{p['username']}"
                    result[key] = p["platform"].lower()
            return result

        social_a = social_set(person_a)
        social_b = social_set(person_b)
        for key in set(social_a) & set(social_b):
            platform = social_a[key]
            _, username = key.split(":", 1)
            links.append({
                "type": "shared_social_profile",
                "value": username,
                "platform": platform,
            })

        return links
