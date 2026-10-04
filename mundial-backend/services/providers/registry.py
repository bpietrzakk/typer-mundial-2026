from services.providers.base import FootballProvider
from services.providers.football_data import PROVIDER_NAME, FootballDataProvider

# one shared instance per provider so the rate limiter state is shared too
_instances: dict[str, FootballProvider] = {}

_FACTORIES = {
    PROVIDER_NAME: FootballDataProvider,
}


def get_provider(name: str) -> FootballProvider:
    # name = value of competitions.provider, e.g. 'football-data'
    if name not in _FACTORIES:
        raise ValueError(f"unknown provider: {name}")
    if name not in _instances:
        _instances[name] = _FACTORIES[name]()
    return _instances[name]
