from ingest.classify.tech import classify_technology_title


def test_technical_title_is_classified_from_config():
    decision = classify_technology_title("Senior Backend Engineer")

    assert decision.category == "Software Engineering"
    assert decision.source == "title_rule"


def test_generic_product_manager_is_not_assumed_technical():
    assert classify_technology_title("Product Manager").category is None


def test_technical_product_manager_requires_strong_evidence():
    assert classify_technology_title("Technical Product Manager").category == "Technical Product"


def test_non_technical_title_is_excluded():
    assert classify_technology_title("Finance Manager").category is None
