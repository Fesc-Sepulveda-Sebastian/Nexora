import json
import logging
from datetime import datetime, timedelta
from app.database import SessionLocal, init_db
from app.models.user import User, Profile, OAuthConsent, UserRole
from app.models.campaign import Campaign, CampaignStatus, CompensationType
from app.models.application import Application, ApplicationStatus, DeliverableEvidence, DeliverableStatus
from app.models.collaboration import CollaborationAgreement, CollaborationStatus
from app.models.rating import Rating
from app.core.security import get_password_hash
from app.services.metrics_service import metrics_service

logger = logging.getLogger(__name__)

def seed():
    init_db()
    db = SessionLocal()

    try:
        # Check if already seeded
        existing_admin = db.query(User).filter(User.email == "admin@nexora.co").first()
        if existing_admin:
            logger.info("Database already seeded. Skipping.")
            return

        logger.info("Seeding realistic Nexora MVP demo data...")

        # 1. Admin
        admin = User(
            email="admin@nexora.co",
            hashed_password=get_password_hash("AdminPass123!"),
            role=UserRole.ADMINISTRADOR.value,
            is_active=True
        )
        db.add(admin)
        db.flush()

        admin_profile = Profile(
            user_id=admin.id,
            display_name="Director de Calidad Nexora",
            bio="Auditoría, resolución de controversias y supervisión de cumplimiento.",
            location_declared="Cúcuta, Colombia",
            niche="Operaciones B2B"
        )
        db.add(admin_profile)

        # 2. Brand (Cúcuta Gourmet)
        brand = User(
            email="marca@cucutagourmet.com",
            hashed_password=get_password_hash("BrandPass123!"),
            role=UserRole.MARCA.value,
            is_active=True
        )
        db.add(brand)
        db.flush()

        brand_profile = Profile(
            user_id=brand.id,
            display_name="Cúcuta Gourmet & Café",
            bio="Cadena gastronómica local especializada en experiencias culinarias tradicionales de Norte de Santander.",
            location_declared="Cúcuta, Colombia",
            niche="Gastronomía",
            avatar_url="https://images.unsplash.com/photo-1555396273-367ea4eb4db5?auto=format&fit=crop&w=400&q=80",
            average_rating=4.9,
            verified_reviews_count=8
        )
        db.add(brand_profile)

        # 3. Creator 1 (Sofia - Gastronomy Nano-influencer)
        creator1 = User(
            email="sofia@cucutafoodie.com",
            hashed_password=get_password_hash("CreatorPass123!"),
            role=UserRole.CREADOR.value,
            is_active=True
        )
        db.add(creator1)
        db.flush()

        samples_c1 = [
            {"title": "Degustación Pastel de Garbanzo Gourmet", "url": "https://instagram.com/p/sample1", "format": "Reel", "views": 14200},
            {"title": "Tour Callejero de Postres en Cúcuta", "url": "https://instagram.com/p/sample2", "format": "TikTok", "views": 28500}
        ]

        creator1_profile = Profile(
            user_id=creator1.id,
            display_name="Sofía Castro | Foodie Cúcuta",
            bio="Narrando historias a través de sabores locales. Nano-influenciadora apasionada por la gastronomía nortesantandereana.",
            location_declared="Cúcuta, Colombia",
            niche="Gastronomía",
            languages="Español, Inglés",
            avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=400&q=80",
            portfolio_samples=json.dumps(samples_c1),
            average_rating=5.0,
            verified_reviews_count=12,
            current_media_kit_version=3
        )
        db.add(creator1_profile)

        # Connect official OAuth mock for Creator 1
        oauth_c1 = OAuthConsent(
            user_id=creator1.id,
            platform="INSTAGRAM",
            account_id="ig_sofiacastro_food",
            account_username="@sofiacastro_food",
            encrypted_token="enc_tok_sample_c1_2026",
            scopes="user_profile,user_media,user_insights",
            is_active=True,
            expires_at=datetime.utcnow() + timedelta(days=90)
        )
        db.add(oauth_c1)

        # Save connected metric snapshot in Mongo / fallback
        snap1 = metrics_service.create_mock_connected_snapshot(
            cuenta_id="ig_sofiacastro_food",
            plataforma="INSTAGRAM",
            followers=8650,
            engagement_pct=6.84,
            city="Cúcuta"
        )
        metrics_service.save_snapshot(snap1)

        # 4. Creator 2 (Carlos - Fitness & Lifestyle)
        creator2 = User(
            email="carlos@cucutafit.com",
            hashed_password=get_password_hash("CreatorPass123!"),
            role=UserRole.CREADOR.value,
            is_active=True
        )
        db.add(creator2)
        db.flush()

        creator2_profile = Profile(
            user_id=creator2.id,
            display_name="Carlos Méndez | Fitness & Vida Sana",
            bio="Rutinas al aire libre, alimentación saludable y hábitos sostenibles.",
            location_declared="Cúcuta, Colombia",
            niche="Fitness & Salud",
            avatar_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=400&q=80",
            average_rating=4.8,
            verified_reviews_count=9,
            current_media_kit_version=1
        )
        db.add(creator2_profile)

        # 5. Campaigns for Cúcuta Gourmet
        # Campaign 1: Published & Active
        delivs_c1 = [
            {"format": "Reel", "qty": 1, "specs": "Video dinámico de 30 a 60 seg en restaurante destacando menú de autor y ambiente."},
            {"format": "Story", "qty": 3, "specs": "Secuencia con sticker de ubicación en Cúcuta y enlace a menú digital."}
        ]
        crit_c1 = {
            "min_followers": 2000,
            "location": "Cúcuta",
            "platforms": ["Instagram", "TikTok"]
        }

        campaign1 = Campaign(
            brand_id=brand.id,
            title="Ruta de Sabores Tradicionales 2026",
            objective="Promocionar el nuevo menú típico regional de temporada entre jóvenes profesionales y turistas de Cúcuta.",
            niche="Gastronomía",
            status=CampaignStatus.PUBLICADA,
            version_id=1,
            start_date=datetime.utcnow() - timedelta(days=2),
            end_date=datetime.utcnow() + timedelta(days=28),
            compensation_type=CompensationType.PAGO_FIJO,
            budget=450000.0,  # COP
            compensation_notes="Pago de 450.000 COP + consumo de cortesía para 2 personas.",
            deliverables=json.dumps(delivs_c1),
            selection_criteria=json.dumps(crit_c1),
            total_cost=450000.0,
            attributable_benefit=1350000.0
        )
        db.add(campaign1)
        db.flush()

        # Campaign 2: Draft
        campaign2 = Campaign(
            brand_id=brand.id,
            title="Lanzamiento Brunch Dominical & Café Especial",
            objective="Generar expectativa del nuevo servicio de brunch dominical con música en vivo.",
            niche="Gastronomía",
            status=CampaignStatus.BORRADOR,
            version_id=1,
            start_date=datetime.utcnow() + timedelta(days=10),
            end_date=datetime.utcnow() + timedelta(days=40),
            compensation_type=CompensationType.CANJE,
            budget=0.0,
            compensation_notes="Experiencia gastronómica VIP de degustación para 4 personas valorada en $300.000 COP.",
            deliverables=json.dumps([{"format": "Reel", "qty": 1, "specs": "Experiencia en vivo"}]),
            selection_criteria=json.dumps({"min_followers": 1500, "location": "Cúcuta", "platforms": ["Instagram"]})
        )
        db.add(campaign2)
        db.flush()

        # 6. Application from Sofia to Campaign 1 (Aceptada)
        frozen_mk = {
            "creator_id": creator1.id,
            "display_name": creator1_profile.display_name,
            "niche": "Gastronomía",
            "location": "Cúcuta, Colombia",
            "followers": 8650,
            "engagement": 6.84,
            "version": 3,
            "frozen_at_utc": datetime.utcnow().isoformat()
        }

        app1 = Application(
            campaign_id=campaign1.id,
            creator_id=creator1.id,
            creative_proposal="Propondré una historia visual que empiece con el aroma del café recién tostado y luego un close-up cinemático al pastel de garbanzo con salsa de la casa, utilizando audio trending de comida.",
            media_kit_snapshot_version=3,
            media_kit_data=json.dumps(frozen_mk),
            status=ApplicationStatus.ACEPTADA,
            idempotency_key="seed-app-key-001"
        )
        db.add(app1)
        db.flush()

        # Deliverable Evidence uploaded by Sofia
        evidence1 = DeliverableEvidence(
            application_id=app1.id,
            deliverable_name="Reel Principal de 45s",
            file_url="https://storage.nexora.co/deliverables/sample_cucuta_gourmet_reel.mp4",
            file_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            file_size_mb=4.8,
            external_live_url="https://instagram.com/reel/CucutaSabor2026",
            status=DeliverableStatus.EN_REVISION,
            submitted_at=datetime.utcnow() - timedelta(hours=5)
        )
        db.add(evidence1)

        # 7. Collaboration Agreement between Brand and Sofia
        agreement1 = CollaborationAgreement(
            application_id=app1.id,
            campaign_id=campaign1.id,
            brand_id=brand.id,
            creator_id=creator1.id,
            version_id=1,
            scope_description="Creación y publicación de 1 Reel y 3 Stories promocionando el menú típico de Cúcuta Gourmet.",
            deliverables_terms=json.dumps(delivs_c1),
            compensation_amount=450000.0,
            deadline=datetime.utcnow() + timedelta(days=15),
            brand_accepted=True,
            brand_accepted_at=datetime.utcnow() - timedelta(days=1),
            creator_accepted=True,
            creator_accepted_at=datetime.utcnow() - timedelta(days=1),
            status=CollaborationStatus.EN_EJECUCION
        )
        db.add(agreement1)

        db.commit()
        logger.info("Demo data successfully seeded for Nexora MVP!")

    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
