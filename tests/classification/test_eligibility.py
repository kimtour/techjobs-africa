import pytest

from ingest.classify.eligibility import classify_eligibility
from ingest.models import EligibilityLevel


@pytest.mark.parametrize(
    ("location", "title", "description", "expected"),
    [
        ("Remote", None, None, EligibilityLevel.UNKNOWN),
        ("Remote - EMEA", None, None, EligibilityLevel.VERIFY),
        ("Remote - Kenya", None, None, EligibilityLevel.CONFIRMED),
        ("Must reside in Kenya", None, None, EligibilityLevel.CONFIRMED),
        ("Must reside in United States", None, None, EligibilityLevel.RESTRICTED),
        ("Remote", None, "Four hours overlap with EST is required.", EligibilityLevel.UNKNOWN),
        ("Remote", None, "West timezone preferred.", EligibilityLevel.UNKNOWN),
        ("Remote", "Join us as an engineer", None, EligibilityLevel.UNKNOWN),
        ("Remote", None, "Our clients in Ghana rely on us.", EligibilityLevel.UNKNOWN),
        ("Remote", None, "We have a worldwide customer base.", EligibilityLevel.UNKNOWN),
        ("Remote", None, "Open to candidates in Africa.", EligibilityLevel.LIKELY),
        ("Worldwide", None, None, EligibilityLevel.CONFIRMED),
        ("Nairobi, Kenya", None, None, EligibilityLevel.CONFIRMED),
    ],
)
def test_eligibility_rules(location, title, description, expected):
    decision = classify_eligibility(location=location, title=title, description=description)
    assert decision.level is expected
