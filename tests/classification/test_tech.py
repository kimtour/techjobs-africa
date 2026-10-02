from ingest.classify.tech import classify_technology_title


def test_technical_title_is_classified_from_config():
    decision = classify_technology_title("Senior Backend Engineer")

    assert decision.category == "Software Engineering"
    assert decision.source == "title_rule"


def test_generic_product_manager_is_included_as_technical_product():
    assert classify_technology_title("Product Manager").category == "Technical Product"


def test_qa_automation_role_is_included_as_qa_testing():
    assert classify_technology_title("QA Automation Engineer").category == "QA / Testing"


def test_technical_product_manager_requires_strong_evidence():
    assert classify_technology_title("Technical Product Manager").category == "Technical Product"


def test_non_technical_title_is_excluded():
    assert classify_technology_title("Finance Manager").category is None


def test_human_resources_title_is_excluded():
    assert classify_technology_title("Human Resources Business Partner").category is None


def test_sales_role_with_generic_ict_term_is_excluded():
    assert classify_technology_title("Senior Sales Officer - ICT Solutions").category is None


def test_specific_ict_role_is_classified_as_it_operations():
    assert classify_technology_title("ICT Officer II").category == "IT Operations"


def test_domain_function_survives_seniority_and_new_title_variants():
    examples = {
        "Infrastructure & Networking SME (GCP / Apigee)": "Networking",
        "Infrastructure and Networking SME": "Networking",
        "Data Insights": "Data Science",
        "ICT Senior Analyst": "IT Operations",
        "ICT Lead Analyst - Data and Business Intelligence": "Data Science",
        "Cloud Principal Engineer": "Cloud",
    }
    for title, category in examples.items():
        assert classify_technology_title(title).category == category


def test_missing_google_technical_variants_are_included():
    titles = [
        "Mobile App Developer in Nairobi",
        "Senior Mobile IOS Engineer",
        "Software Engineering Trainer",
        "Software Engineering Interns",
        "Software Engineering Internship (AI)",
        "Strong Junior .NET Developer (Business Process Automation)",
        "Senior Full-Stack Engineer",
        "Group Head: Platform Engineering",
        "Software Developers Job Vacancies at The Pharmacy and Poisons Board (PPB)",
        "ML Developer Intern, Community of Practice",
        "Cloud Infrastructure Developer",
        "Enterprise Solution Engineer",
        "Hardware Engineer (Network & RF)",
        "System Engineer",
        "IT Specialist",
    ]
    for title in titles:
        assert classify_technology_title(title).category, title


def test_broad_engineer_search_does_not_admit_unrelated_engineering():
    for title in [
        "Civil Engineer",
        "Mechanical Engineer",
        "Electrical Engineer",
        "Sales Officer - Software Developers",
        "HR Officer - Platform Engineering",
    ]:
        assert classify_technology_title(title).category is None, title
