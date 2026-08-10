from __future__ import annotations


def search_volume_compatible(evidence, *, keyword, location_name, language_code, country_code, provider=None):
    return (
        evidence.keyword == keyword
        and evidence.location_name == location_name
        and evidence.language_code == language_code
        and evidence.country_code == country_code
        and (provider is None or evidence.provider == provider)
    )


def serp_compatible(snapshot, *, keyword, location_name, language_code, country_code, depth, provider=None, device_profile="desktop"):
    return (
        snapshot.keyword == keyword
        and snapshot.location_name == location_name
        and snapshot.language_code == language_code
        and snapshot.country_code == country_code
        and snapshot.device_profile == device_profile
        and snapshot.requested_depth >= depth
        and (provider is None or snapshot.provider == provider)
    )


def authority_compatible(evidence, *, target_url, root_domain, target_type="URL", provider=None):
    return (
        evidence.target_url == target_url
        and evidence.root_domain == root_domain
        and evidence.target_type == target_type
        and (provider is None or evidence.provider == provider)
    )
