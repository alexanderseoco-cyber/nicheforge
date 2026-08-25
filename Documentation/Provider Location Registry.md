# Provider Location Registry

NicheForge stores provider-specific geographic identities separately from Census city data.

For DataForSEO Local SERP execution, a city must have a verified `ProviderLocationIdentity` matched by city, state, country, and provider. Validation uses only persisted verified mappings. A missing mapping produces `PROVIDER_LOCATION_UNRESOLVED`; it does not guess a location code or fall back to `location_name`.

The current checkpoint adds storage and lookup semantics only. The existing DataForSEO catalog resolver remains available for a later targeted or bulk catalog-resolution checkpoint, but normal validation does not perform a location-catalog side request.

US national targeting continues to use location code `2840`. Worldwide targets do not create city registry records.
