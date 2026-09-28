from ingest.normalize.location import normalize_location


def test_city_only_location_resolves_its_configured_country():
    decision = normalize_location("nairobi")

    assert decision.city == "Nairobi"
    assert decision.country == "Kenya"
    assert decision.country_code == "KE"
    assert decision.workplace_type is None


def test_remote_country_location_preserves_remote_and_country():
    decision = normalize_location("Remote - Kenya")

    assert decision.city is None
    assert decision.country == "Kenya"
    assert decision.country_code == "KE"
    assert decision.workplace_type == "Remote"


def test_unknown_location_is_not_guessed():
    decision = normalize_location("Across the region")

    assert decision.city is None
    assert decision.country is None
    assert decision.country_code is None
