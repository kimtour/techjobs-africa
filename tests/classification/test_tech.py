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


def test_expertini_technical_title_variants():
    examples = {
        "AI Automation Engineer": "AI / Machine Learning",
        "AI Prompt Engineer": "AI / Machine Learning",
        "SEO Automation Engineer": "Software Engineering",
        "Front End Engineer Lead": "Software Engineering",
        "Back End Developer": "Software Engineering",
        "Tech Lead - Android Experience Engineering": "Software Engineering",
        "QA Chapter Lead": "QA / Testing",
        "Data and Automation Systems Builder": "Data Engineering",
    }
    for title, category in examples.items():
        assert classify_technology_title(title).category == category, title


def test_automation_titles_do_not_admit_industrial_or_uncertain_roles():
    for title in [
        "Industrial Automation Engineer",
        "Senior Process Automation Engineer",
        "Water Engineer",
        "Sales Engineer (Industrial Equipments)",
        "Chief Engineer",
        "Senior Petroleum/Production Engineer",
    ]:
        assert classify_technology_title(title).category is None, title


def test_linkedin_comparison_titles_and_punctuation():
    examples = {
        "Senior Backend Engineer - Mobility (12 month FTC)": "Software Engineering",
        "GCP Cloud Platform Administrator": "Cloud",
        "Software Developer Trainee": "Software Engineering",
        "Product Manager": "Technical Product",
        "Project Manager": "Technical Product",
        "Technical Project Manager": "Technical Product",
        "Manager,Technology": "Technology Leadership",
        "Manager / Technology": "Technology Leadership",
    }
    for title, category in examples.items():
        assert classify_technology_title(title).category == category, title
    for title in [
        "Manager,Sales",
        "Cloud Sales Officer",
    ]:
        assert classify_technology_title(title).category is None, title


def test_missing_myjobmag_functions_are_classified_without_trusting_the_source_category():
    examples = {
        "Structured Cabling Installers and Fiber Specialists": "Networking",
        "User Manager/Access Management Specialist": "Cybersecurity",
        "Senior Manager IT Applications & Asset Management": "Application Support",
        "Software Architect": "Solutions Architecture",
        "Associate II: Systems Support Analyst": "Application Support",
        "Head of Artificial Intelligence": "AI / Machine Learning",
        "ICT Security Manager": "Cybersecurity",
        "Lead Analyst - Data Operations": "Data Science",
        "Internal IT Auditor": "Cybersecurity",
        "Systems Librarian": "IT Operations",
        "SSA KE - IT Support Specialist": "Technical Support",
        "Intern - ICT": "IT Operations",
        "Information Communication Technology Officer III": "IT Operations",
        "ICT & Systems Manager": "IT Operations",
        "Manager IT Risk": "Cybersecurity",
        "Programmer": "Software Engineering",
        "Senior Developer": "Software Engineering",
        "Officer – Network Administration": "Networking",
        "Technical Program Manager": "Technical Product",
        "Digital Workplace & Microsoft 365 Technical Expert": "IT Operations",
        "Information Systems Audit Intern": "Cybersecurity",
        "Salesforce Administrator": "ERP / Enterprise Systems",
        "ICT Trainer": "IT Operations",
        "Data Engineering Advisor": "Data Engineering",
        "Cyber Security Administrator (Operations)": "Cybersecurity",
        "End User Support Consultant": "Application Support",
        "Platform Architect – Security": "Solutions Architecture",
    }
    for title, category in examples.items():
        assert classify_technology_title(title + " at Example Company").category == category, title


def test_employer_name_is_not_technical_or_non_technical_role_evidence():
    assert (
        classify_technology_title("Office Clerk at Artificial Intelligence Labs").category is None
    )
    assert classify_technology_title("Software Architect at Human Resources Partners").category


def test_ambiguous_and_unrelated_myjobmag_titles_still_need_evidence():
    for title in [
        "Accounts Assistant",
        "Post Graduate Program Coordinator - Information Communication Technology",
        "Programme Officer (Monitoring and Evaluation)",
        "Senior Product Analyst, DELTA",
        "Head of Payments and Platform",
        "Digital Health Systems Strengthening Officers",
        "Engineer Service Delivery",
        "Data Entry Clerk",
        "Network Development Associate-Africa",
        "CNC Programmer",
        "Property Developer",
    ]:
        assert classify_technology_title(title).category is None, title


def test_access_management_is_technical_but_generic_user_manager_is_not():
    assert classify_technology_title("User Manager/Access Management Specialist").category
    assert classify_technology_title("User Manager").category is None


def test_more_technical_families_found_in_the_thirty_day_audit():
    for title in [
        "Genesys Cloud CX Developer",
        "M-Pesa Africa: Senior Data Architect",
        "Trainer-ICT",
        "TVET Trainers - Information and Communication Technology (ICT)",
        "Subject Matter Expert - Networking & Infrastructure",
        "I.T Specialist",
        "I.T Services & Infrastructure Officer",
        "Tech Lead, Payments & Financial Infrastructure",
        "ERPNext / Frappe Developer",
        "Sacco ICT Assistant",
        "Data Labelers- AV/ADAS",
        "Associate Data Custodian/Steward",
        "IT Clerks",
        "Team Leader, SRE",
        "Senior Data & Information Governance Specialist",
        "IT Executive (Odoo ERP & IT Infrastructure)",
        "Senior EDI Applications Engineer",
        "AI Domain Architect",
        "Server & Systems Security Administrator",
        "AI Specialist",
        "Software QA",
        "SD-WAN L2 Engineer",
        "Director, Information, Communication & Technology (ICT)",
    ]:
        assert classify_technology_title(title).category, title


def test_shared_title_rules_cover_variants_found_on_other_boards():
    for title in [
        "IT and Digital Systems Lead",
        "Machine Learning Specialist",
        "Product Owner",
        "Agile Product Owner - Cigna Healthcare",
        "Zendesk Implementation Consultant",
        "Networking Engineer",
        "Manager, Database Administration",
        "User Interface and User Experience (UI/UX) Designer",
        "Officer Enterprise Applications Support",
        "System Integration Officer",
        "IT Internship Opportunity",
        "Senior System Analyst",
        "AI & Data Transformations Lead",
        "QA / Integration Tester",
        "Onsite Technology Support Associate",
        "Teacher of Computer Science and ICT/Physics",
        "Head of Product, Merchant Solutions",
        "Analyst Programmer",
        "Network Infrastructure Technician",
        "SAP Basis Consultant",
        "Quality Associate - ICT",
    ]:
        assert classify_technology_title(title).category, title
    for title in [
        "Teacher of Mathematics",
        "Programme Coordinator ICT",
        "Data Entry Clerk",
        "Civil Engineering Lecturer",
        "Finance Manager at Software Engineering Ltd",
    ]:
        assert classify_technology_title(title).category is None, title


def test_domain_and_function_patterns_cover_the_cross_board_audit():
    for title in [
        "IT, Data & Systems Officer",
        "Ceph Storage Engineer",
        "ICT Teachers",
        "Attachee -ICT",
        "Senior Officer – IT, AIM",
        "Local Information Systems Officer",
        "IT Service Delivery Manager",
        "ICT & Data Officer",
        "Head Data Applications & Integration",
        "Computer Technologist",
        "RPA Developer",
        "Information Systems Assistant, G5",
        "IT Specialists",
        "IT Administrator",
        "Mid-Level Developer",
        "Fullstack Developer",
        "Fineract Developer",
        "Data Annotation Specialist",
        "IT Infrastructure Lead",
        "IT Operations Specialist",
        "Systems Admin Associate",
        "AI Orchestration Engineer",
        "Data & Analytics Manager",
        "Springboot Engineer",
        "Cloud Solutions Developer – Integrations & Platforms",
        "UI/UX Engineer",
        "Engineer – IT Assets Management & Compliance",
        "React Developer",
        "DevSecOps Engineer",
        "Cloud Support Associate Intern",
        "Integrations Developer",
        "Network & Infrastructure Officer",
        "IT Project Associate",
        "Senior Associate -ICT Governance",
        "IP Network Planner",
        "Senior Internal Auditor – IT Audits & Analytics",
        "Systems & Infrastructure Officer",
        "Network Operations Lead (Fibre / FTTH)",
        "Fiber Optic Technician",
        "IT Techno Functional Manager - SAP S/4HANA ABAP development",
        "ICT & Graphic Design Officer",
        "Applications & Software Officer",
        "Information Systems Security Manager",
        "IT Suport Specialist",
        "Senior Web Engineer",
        "Usability Engineer - User Science",
        "Internship- IT",
        "RPA Tester",
        "Senior Business Analyst, Core Banking",
        "Head Data Applications & Integration",
        "Java Backend Engineering Team Lead",
        "Systems & App Developer",
        "Lead Systems Integrator & Developer",
        "Specialist, BI Developer",
        "API & Developer Market Place Lead",
    ]:
        assert classify_technology_title(title).category, title
    for title in [
        "Driver – Digital IT",
        "IT Sales Manager",
        "ICT Sales Executive",
        "Sales Executive – Web Design & Web Services",
        "Property Developer",
        "Mechanical Maintenance Technician",
        "Junior School Music Teacher",
        "Electrical Technician – Power Generation Systems",
        "Data Entry Clerks",
        "Graduate Intern – MEL (Business Engagement Market Systems)",
    ]:
        assert classify_technology_title(title).category is None, title


def test_physical_and_logistics_network_jobs_are_not_computer_networking():
    for title in (
        "Network Facilities Electrical Engineer",
        "Logistics Network & Operations Manager",
        "Electrical Network Engineer",
    ):
        assert classify_technology_title(title).category is None, title
    assert classify_technology_title("Network Engineer").category == "Networking"
    assert classify_technology_title("IT Manager - Logistics Network").category


def test_project_delivery_and_fintech_sector_do_not_prove_technical_function():
    for title in (
        "Finance Analyst: Data Governance & Accounting",
        "Shelter & Wash Project Manager Chad Iriba (national only)",
        "ICLA Project Manager CAR Bouar",
        "Carbon Project Manager - Senegal",
        "Cash and Markets Project Manager Sudan Khartoum",
        "Regulatory & Licensing Officer – Middle East and North Africa (Payments/ Fintech)",
    ):
        assert classify_technology_title(title).category is None, title
    for title in ("IT Project Manager", "Software Project Manager", "Technical Project Manager"):
        assert classify_technology_title(title).category == "Technical Product", title
