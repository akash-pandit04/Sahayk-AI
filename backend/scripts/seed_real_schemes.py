import asyncio
import os
import sys
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.scheme_data.models import (
    ApplicationStep,
    DataType,
    EligibilityRule,
    OperatorType,
    RequiredDocument,
    Scheme,
    SchemeBenefit,
    SchemeEmbedding,
    SchemeSource,
    SchemeStatus,
    SourceType,
    VerificationStatus,
)
from app.services.ai.providers.factory import get_embedding_provider


SCHEMES_DATA = [
    {
        "name": "Indira Gandhi National Old Age Pension Scheme (IGNOAPS)",
        "short_description": "A non-contributory old age pension scheme providing monthly financial assistance to elderly persons living below the poverty line.",
        "detailed_description": "The Indira Gandhi National Old Age Pension Scheme (IGNOAPS) is part of the National Social Assistance Programme (NSAP) under the Ministry of Rural Development, Government of India.",
        "target_group": "Senior Citizens (Below Poverty Line)",
        "application_mode": "Both",
        "official_application_url": "https://nsap.nic.in/",
        "source": ("Official NSAP Portal", "https://nsap.nic.in/"),
        "benefits": [("FINANCIAL", "Rs 200-500+ per month", "Central monthly old-age pension (plus applicable state top-up).")],
        "rules": [
            ("age", OperatorType.GREATER_THAN_EQUALS, "60", DataType.NUMBER, "Applicant must be 60 years or older."),
            ("bpl_status", OperatorType.EQUALS, "true", DataType.BOOLEAN, "Applicant household must belong to BPL category."),
        ],
        "documents": [("Aadhaar Card", True), ("Age Proof", True), ("BPL Card", True)],
        "steps": [(1, "Submit Application", "Apply via local Gram Panchayat / Urban Local Body or UMANG portal.", "Both")],
    },
    {
        "name": "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
        "short_description": "Provides income support of ₹6,000 per year to eligible landholding farmer families.",
        "detailed_description": "PM-KISAN is a Central Sector scheme with 100% Government of India funding providing ₹6,000 per year in three equal four-monthly installments.",
        "target_group": "Farmers",
        "application_mode": "Online",
        "official_application_url": "https://pmkisan.gov.in/",
        "source": ("PM-KISAN Portal", "https://pmkisan.gov.in/"),
        "benefits": [("FINANCIAL", "Rs 6000/year", "Direct Benefit Transfer of ₹6,000 annually in three installments.")],
        "rules": [
            ("occupation", OperatorType.EQUALS, "farmer", DataType.STRING, "Applicant must be engaged in farming."),
            ("has_agricultural_land", OperatorType.EQUALS, "true", DataType.BOOLEAN, "Family must hold cultivable agricultural land."),
        ],
        "documents": [("Aadhaar Card", True), ("Landholding Records", True), ("Bank Account Details", True)],
        "steps": [(1, "Register on PM-KISAN", "Register via pmkisan.gov.in or Common Service Centre (CSC) with Aadhaar e-KYC.", "Online")],
    },
    {
        "name": "Pradhan Mantri Awas Yojana - Urban 2.0 (PMAY-U)",
        "short_description": "Provides central assistance for affordable housing to eligible urban families.",
        "detailed_description": "PMAY-U 2.0 addresses affordable housing in urban areas for EWS/LIG/MIG families who do not own a pucca house anywhere in India.",
        "target_group": "Urban Poor (EWS/LIG)",
        "application_mode": "Online",
        "official_application_url": "https://pmay-urban.gov.in/",
        "source": ("PMAY-U Portal", "https://pmay-urban.gov.in/"),
        "benefits": [("FINANCIAL", "Central Assistance / Subsidy", "Financial assistance for construction or purchase of a pucca urban house.")],
        "rules": [
            ("location_type", OperatorType.EQUALS, "urban", DataType.STRING, "Beneficiary household must reside in an urban area."),
            ("owns_pucca_house", OperatorType.EQUALS, "false", DataType.BOOLEAN, "Family must not own a pucca house anywhere in India."),
        ],
        "documents": [("Aadhaar Card", True), ("Income Certificate", True), ("Address Proof", True)],
        "steps": [(1, "Apply Online", "Submit application through the official PMAY-U 2.0 portal or ULB.", "Online")],
    },
    {
        "name": "Ayushman Bharat Pradhan Mantri Jan Arogya Yojana (AB PM-JAY)",
        "short_description": "Provides health cover of ₹5 lakhs per family per year for secondary and tertiary care hospitalization.",
        "detailed_description": "AB PM-JAY is a government-financed health assurance scheme providing cashless coverage up to ₹5 lakh per family per year at empanelled hospitals.",
        "target_group": "Low-income Families (SECC 2011)",
        "application_mode": "Both",
        "official_application_url": "https://pmjay.gov.in/",
        "source": ("PM-JAY Portal", "https://pmjay.gov.in/"),
        "benefits": [("SERVICE", "Rs 5,00,000/family/year", "Cashless secondary and tertiary hospitalization coverage.")],
        "rules": [
            ("income_group", OperatorType.EQUALS, "low", DataType.STRING, "Household must meet SECC/eligible low-income criteria."),
        ],
        "documents": [("Aadhaar Card", True), ("Ration Card / SECC Eligibility Proof", True)],
        "steps": [(1, "Verify & Get Ayushman Card", "Verify eligibility on beneficiary.nha.gov.in and generate Ayushman Card.", "Both")],
    },
    {
        "name": "Sukanya Samriddhi Account (SSA)",
        "short_description": "A small deposit savings scheme for the girl child under Beti Bachao Beti Padhao.",
        "detailed_description": "Sukanya Samriddhi Account allows a natural or legal guardian to open a savings account in the name of a girl child from birth until she turns 10.",
        "target_group": "Girl Child (Under 10)",
        "application_mode": "Offline",
        "official_application_url": "https://www.indiapost.gov.in/",
        "source": ("India Post SSA Info", "https://www.indiapost.gov.in/Financial/Pages/Content/Post-Office-Saving-Schemes.aspx"),
        "benefits": [("FINANCIAL", "Government-backed Savings Interest", "High-interest tax-advantaged savings account for girl child education and future.")],
        "rules": [
            ("gender", OperatorType.EQUALS, "female", DataType.STRING, "Account beneficiary must be a girl child."),
            ("age", OperatorType.LESS_THAN, "10", DataType.NUMBER, "Girl child must be under 10 years of age at account opening."),
        ],
        "documents": [("Girl Child Birth Certificate", True), ("Guardian Aadhaar / ID Proof", True)],
        "steps": [(1, "Visit Post Office / Bank", "Submit SSA account opening form with birth certificate and guardian KYC.", "Offline")],
    },
]


async def seed_real_schemes() -> None:
    db = SessionLocal()
    embedding_provider = get_embedding_provider()
    created_count = 0

    try:
        for item in SCHEMES_DATA:
            if db.query(Scheme).filter(Scheme.name == item["name"]).first():
                continue

            scheme = Scheme(
                id=str(uuid.uuid4()),
                name=item["name"],
                short_description=item["short_description"],
                detailed_description=item["detailed_description"],
                status=SchemeStatus.PUBLISHED,
                target_group=item["target_group"],
                application_mode=item["application_mode"],
                official_application_url=item["official_application_url"],
                version=1,
            )
            db.add(scheme)
            db.flush()

            src_title, src_url = item["source"]
            db.add(
                SchemeSource(
                    scheme_id=scheme.id,
                    title=src_title,
                    url=src_url,
                    source_type=SourceType.OFFICIAL_GOVERNMENT,
                    verification_status=VerificationStatus.VERIFIED,
                )
            )
            for b_type, amt, desc in item["benefits"]:
                db.add(SchemeBenefit(scheme_id=scheme.id, benefit_type=b_type, amount_value=amt, description=desc))

            rule_nodes = []
            for field, op, val, dtype, expl in item["rules"]:
                rule = EligibilityRule(
                    id=str(uuid.uuid4()),
                    scheme_id=scheme.id,
                    field=field,
                    operator=op,
                    value=val,
                    data_type=dtype,
                    explanation=expl,
                )
                db.add(rule)
                rule_nodes.append({"rule_id": rule.id})
            scheme.rule_logic = {"operator": "AND", "rules": rule_nodes}

            for idx, (doc_name, mandatory) in enumerate(item["documents"]):
                db.add(RequiredDocument(scheme_id=scheme.id, document_name=doc_name, is_mandatory=mandatory, display_order=idx))

            for step_num, title, desc, mode in item["steps"]:
                db.add(ApplicationStep(scheme_id=scheme.id, step_number=step_num, title=title, description=desc, application_mode=mode))

            text_to_embed = f"{scheme.name}. {scheme.short_description}. {scheme.detailed_description}"
            emb = await embedding_provider.generate_embedding(text_to_embed)
            db.add(
                SchemeEmbedding(
                    scheme_id=scheme.id,
                    model_name=embedding_provider.model_name,
                    dimension=embedding_provider.dimension,
                    content_hash="seed",
                    embedding=emb,
                )
            )
            created_count += 1

        db.commit()
        print(f"Seeded {created_count} new verified schemes (idempotent check complete).")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(seed_real_schemes())
