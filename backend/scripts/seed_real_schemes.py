import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.db.base import Base
from app.db.session import SessionLocal
from app.models.scheme_data.models import (
    Scheme, SchemeBenefit, EligibilityRule, RequiredDocument, ApplicationStep, SchemeSource, SchemeStatus,
    SourceType, VerificationStatus, OperatorType, DataType, SchemeEmbedding
)
from app.services.ai.providers.factory import get_embedding_provider
import uuid

async def seed_real_schemes():
    db = SessionLocal()
    
    # 1. IGNOAPS (Indira Gandhi National Old Age Pension Scheme)
    ignoaps = Scheme(
        id=str(uuid.uuid4()),
        name="Indira Gandhi National Old Age Pension Scheme (IGNOAPS)",
        short_description="A non-contributory old age pension scheme that provides monthly financial assistance to elderly persons living below the poverty line.",
        detailed_description="The Indira Gandhi National Old Age Pension Scheme (IGNOAPS) is a component of the National Social Assistance Programme (NSAP) implemented by the Ministry of Rural Development, Government of India. It provides social protection to eligible elderly citizens below the poverty line.",
        status=SchemeStatus.PUBLISHED,
        target_group="Senior Citizens (Below Poverty Line)",
        application_mode="Both",
        official_application_url="https://nsap.nic.in/",
        version=1,
        rule_logic={
            "condition": "AND",
            "rules": [
                {"field": "age", "operator": "GREATER_THAN_EQUALS", "value": 60, "data_type": "NUMBER"},
                {"field": "bpl_status", "operator": "EQUALS", "value": True, "data_type": "BOOLEAN"}
            ]
        }
    )
    
    ignoaps_source = SchemeSource(
        scheme_id=ignoaps.id, title="Official NSAP Portal", url="https://nsap.nic.in/",
        source_type=SourceType.OFFICIAL_GOVERNMENT, verification_status=VerificationStatus.VERIFIED
    )
    
    # 2. PM-KISAN
    pm_kisan = Scheme(
        id=str(uuid.uuid4()),
        name="Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
        short_description="Provides income support of ₹6,000 per year to all landholding farmer families across the country.",
        detailed_description="PM-KISAN is a Central Sector scheme with 100% funding from the Government of India. Under the scheme an income support of ₹6,000 per year in three equal installments will be provided to all landholding farmer families.",
        status=SchemeStatus.PUBLISHED,
        target_group="Farmers",
        application_mode="Online",
        official_application_url="https://pmkisan.gov.in/",
        version=1,
        rule_logic={
            "condition": "AND",
            "rules": [
                {"field": "occupation", "operator": "EQUALS", "value": "farmer", "data_type": "STRING"},
                {"field": "has_agricultural_land", "operator": "EQUALS", "value": True, "data_type": "BOOLEAN"}
            ]
        }
    )
    
    pm_kisan_source = SchemeSource(
        scheme_id=pm_kisan.id, title="PM-KISAN Portal", url="https://pmkisan.gov.in/",
        source_type=SourceType.OFFICIAL_GOVERNMENT, verification_status=VerificationStatus.VERIFIED
    )
    
    # 3. PMAY-U 2.0
    pmay_u = Scheme(
        id=str(uuid.uuid4()),
        name="Pradhan Mantri Awas Yojana - Urban 2.0 (PMAY-U)",
        short_description="Provides central assistance to urban local bodies and other implementing agencies for housing for all.",
        detailed_description="PMAY-U 2.0 addresses the affordable housing requirement in urban areas. Eligibility requires the family not to own a pucca house anywhere in India and to fall within specified EWS/LIG income criteria.",
        status=SchemeStatus.PUBLISHED,
        target_group="Urban Poor (EWS/LIG)",
        application_mode="Online",
        official_application_url="https://pmay-urban.gov.in/",
        version=1,
        rule_logic={
            "condition": "AND",
            "rules": [
                {"field": "location_type", "operator": "EQUALS", "value": "urban", "data_type": "STRING"},
                {"field": "owns_pucca_house", "operator": "EQUALS", "value": False, "data_type": "BOOLEAN"}
            ]
        }
    )
    
    pmay_u_source = SchemeSource(
        scheme_id=pmay_u.id, title="PMAY-U Portal", url="https://pmay-urban.gov.in/",
        source_type=SourceType.OFFICIAL_GOVERNMENT, verification_status=VerificationStatus.VERIFIED
    )
    
    # 4. Ayushman Bharat (PM-JAY)
    ayushman = Scheme(
        id=str(uuid.uuid4()),
        name="Ayushman Bharat Pradhan Mantri Jan Arogya Yojana (AB PM-JAY)",
        short_description="Provides health cover of ₹5 lakhs per family per year for secondary and tertiary care hospitalization.",
        detailed_description="AB PM-JAY is the world's largest health insurance/ assurance scheme fully financed by the government. It provides a cover of Rs. 5 lakhs per family per year for secondary and tertiary care hospitalization.",
        status=SchemeStatus.PUBLISHED,
        target_group="Low-income Families (SECC 2011)",
        application_mode="Both",
        official_application_url="https://pmjay.gov.in/",
        version=1,
        rule_logic={
            "condition": "AND",
            "rules": [
                {"field": "income_group", "operator": "EQUALS", "value": "low", "data_type": "STRING"}
            ]
        }
    )
    
    ayushman_source = SchemeSource(
        scheme_id=ayushman.id, title="PM-JAY Portal", url="https://pmjay.gov.in/",
        source_type=SourceType.OFFICIAL_GOVERNMENT, verification_status=VerificationStatus.VERIFIED
    )

    # 5. Sukanya Samriddhi Account (SSA)
    ssa = Scheme(
        id=str(uuid.uuid4()),
        name="Sukanya Samriddhi Account (SSA)",
        short_description="A small deposit scheme for the girl child launched as a part of the Beti Bachao Beti Padhao campaign.",
        detailed_description="The scheme meant to meet the education and marriage expenses of a girl child. The account can be opened by the natural or legal guardian in the name of a girl child from her birth till she attains the age of 10 years.",
        status=SchemeStatus.PUBLISHED,
        target_group="Girl Child (Under 10)",
        application_mode="Offline",
        official_application_url="https://www.indiapost.gov.in/",
        version=1,
        rule_logic={
            "condition": "AND",
            "rules": [
                {"field": "gender", "operator": "EQUALS", "value": "female", "data_type": "STRING"},
                {"field": "age", "operator": "LESS_THAN", "value": 10, "data_type": "NUMBER"}
            ]
        }
    )
    
    ssa_source = SchemeSource(
        scheme_id=ssa.id, title="India Post SSA Info", url="https://www.indiapost.gov.in/Financial/Pages/Content/Post-Office-Saving-Schemes.aspx",
        source_type=SourceType.OFFICIAL_GOVERNMENT, verification_status=VerificationStatus.VERIFIED
    )

    db.add_all([ignoaps, pm_kisan, pmay_u, ayushman, ssa])
    db.add_all([ignoaps_source, pm_kisan_source, pmay_u_source, ayushman_source, ssa_source])
    db.commit()

    # Generate Embeddings using configured provider
    embedding_provider = get_embedding_provider()
    
    for s in [ignoaps, pm_kisan, pmay_u, ayushman, ssa]:
        text_to_embed = f"{s.name}. {s.short_description}. {s.detailed_description}"
        emb = await embedding_provider.generate_embedding(text_to_embed)
        db_emb = SchemeEmbedding(
            scheme_id=s.id,
            model_name=embedding_provider.model_name,
            dimension=embedding_provider.dimension,
            content_hash="seed",
            embedding=emb
        )
        db.add(db_emb)
    db.commit()
    print("Seeded 5 verified schemes successfully.")

if __name__ == "__main__":
    asyncio.run(seed_real_schemes())
