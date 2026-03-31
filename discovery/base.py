from abc import ABC, abstractmethod


class BaseDiscoveryProvider(ABC):
    """
    Base class for all connection discovery providers.

    Implementations receive two full person documents and return a list of
    link dicts describing evidence of a connection between the two people.

    Each returned link dict must have at minimum:
        {"type": str, "value": str}
    The runner injects {"provider": self.name} before persisting.
    Optional fields: "platform" (for social overlap links).
    """

    name: str = ""

    @abstractmethod
    def find_links(self, person_a: dict, person_b: dict) -> list[dict]:
        """
        Return a list of link dicts connecting person_a and person_b.
        Return [] if no connection evidence is found.
        Raise ProviderUnavailableError on network / service errors.
        Raise ProviderRateLimitError when the API signals rate limiting (HTTP 429).
        """

    def is_available(self) -> bool:
        """
        Return False if this provider cannot run (e.g. missing API key).
        The runner skips unavailable providers silently.
        """
        return True


class DiscoveryError(Exception):
    pass


class ProviderUnavailableError(DiscoveryError):
    """Raised when the provider service is unreachable or returns an error."""
    pass


class ProviderRateLimitError(DiscoveryError):
    """Raised when the provider signals the client is rate-limited."""
    pass
