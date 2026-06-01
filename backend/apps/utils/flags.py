_CACHE_TIMEOUT = 60


def flag_enabled(name: str) -> bool:
    """Return True if the named FeatureFlag exists and is enabled.

    Result is cached for 60 seconds (Django default cache / Redis DB 1) to
    avoid a per-request DB hit. Returns False for unknown flags.
    """
    from django.core.cache import cache

    cache_key = f'feature_flag_{name}'
    cached = cache.get(cache_key)
    if cached is not None:
        return bool(cached)

    try:
        from apps.repositories.models import FeatureFlag
        result = FeatureFlag.objects.get(name=name).enabled
    except Exception:
        result = False

    cache.set(cache_key, result, _CACHE_TIMEOUT)
    return result
