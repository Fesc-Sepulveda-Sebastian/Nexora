import pytest
from datetime import datetime, timedelta
from app.models.campaign import Campaign, CampaignStatus, CompensationType
from app.models.collaboration import CollaborationAgreement, CollaborationStatus
from app.schemas.campaign import validate_campaign_for_publishing, CampaignUpdate
from app.schemas.collaboration import ROICalculatorInput
from app.schemas.rating import RatingCreate
from app.api.v1.collaborations import calculate_estimated_roi
from app.api.v1.ratings import submit_rating
from app.api.v1.campaigns import update_campaign
from fastapi import HTTPException

def test_rn01_publish_validation_failure_on_empty_fields():
    """
    RN-01: A campaign cannot be published without all mandatory fields valid.
    """
    empty_campaign = Campaign(
        title="",
        objective="",
        niche="",
        deliverables=None,
        start_date=None,
        end_date=None,
        compensation_type=CompensationType.PAGO_FIJO,
        budget=0.0,
        selection_criteria=None
    )
    errors = validate_campaign_for_publishing(empty_campaign)
    assert len(errors) > 0
    assert any("Título" in e for e in errors)
    assert any("Objetivo" in e for e in errors)
    assert any("Nicho" in e for e in errors)
    assert any("entregable" in e for e in errors)
    assert any("presupuesto" in e for e in errors)

def test_rn01_publish_validation_success():
    """
    RN-01: Valid campaign passes publication check.
    """
    now = datetime.utcnow()
    valid_campaign = Campaign(
        title="Campaña Gastronómica Cúcuta",
        objective="Posicionar el café especial nortesantandereano en redes sociales.",
        niche="Gastronomía",
        deliverables='[{"format": "Reel", "qty": 1, "specs": "Video de 30s"}]',
        start_date=now,
        end_date=now + timedelta(days=20),
        compensation_type=CompensationType.PAGO_FIJO,
        budget=350000.0,
        selection_criteria='{"min_followers": 2000, "location": "Cúcuta", "platforms": ["Instagram"]}'
    )
    errors = validate_campaign_for_publishing(valid_campaign)
    assert len(errors) == 0

def test_rn04_roi_calculation_valid():
    """
    RN-04: ((beneficio - costo) / costo) * 100.
    With total_cost = 400.000 and attributable_benefit = 1.000.000:
    Net profit = 600.000
    ROI = (600.000 / 400.000) * 100 = 150.0%
    """
    input_data = ROICalculatorInput(
        total_cost=400000.0,
        attributable_benefit=1000000.0,
        currency="COP"
    )
    response = calculate_estimated_roi(input_data)
    assert response.success is True
    data = response.data
    assert data.roi_percentage == 150.0
    assert data.net_profit == 600000.0
    assert "Estimación" in data.disclaimer

def test_rn04_roi_calculation_invalid_zero_cost():
    """
    RN-04: System only calculates ROI if total cost > 0.
    """
    input_data = ROICalculatorInput(
        total_cost=0.0,
        attributable_benefit=500000.0,
        currency="COP"
    )
    with pytest.raises(HTTPException) as exc_info:
        calculate_estimated_roi(input_data)
    assert exc_info.value.status_code == 400
    assert "RN-04" in exc_info.value.detail
