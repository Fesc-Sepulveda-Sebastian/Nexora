import json
import pytest
from datetime import datetime, timedelta
from starlette.websockets import WebSocketDisconnect

from app.cli import create_admin_user
from app.models.campaign import Campaign, CampaignStatus
from app.models.application import Application, ApplicationStatus
from app.models.collaboration import CollaborationAgreement, CollaborationStatus
from app.models.user import User


def _register_and_login(client, email: str, role: str, display_name: str, password: str = "SecretPass123!"):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "role": role,
            "display_name": display_name,
            "location_declared": "Cúcuta, Colombia",
            "niche": "Gastronomía",
            "terms_accepted": True,
        },
    )
    assert reg.status_code == 201, reg.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    data = login.json()["data"]
    return data["access_token"], data["user_id"]


def test_h01_admin_registration_blocked(client, db_session):
    """
    H01: Public registration of 'administrador' must be rejected with 403/422 without creating account.
    Admin accounts can only be created via internal CLI/helper.
    """
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "evil_admin@nexora.co",
            "password": "AdminPassword123!",
            "role": "administrador",
            "display_name": "Evil Admin",
            "terms_accepted": True,
        },
    )
    assert resp.status_code in (403, 422)
    assert db_session.query(User).filter(User.email == "evil_admin@nexora.co").first() is None

    # Internal CLI helper succeeds
    admin = create_admin_user(
        db=db_session,
        email="internal_admin@nexora.co",
        password="AdminPassword123!",
        display_name="Internal Admin",
    )
    assert admin.role == "administrador"


def test_h02_unauthorized_reads_blocked(client, db_session):
    """
    H02: Anonymous and third-party reads of drafts, agreements, and messages must return 401/403.
    """
    brand_token, brand_id = _register_and_login(client, "brand1@nexora.co", "marca", "Marca Uno")
    other_brand_token, _ = _register_and_login(client, "brand2@nexora.co", "marca", "Marca Dos")
    creator1_token, creator1_id = _register_and_login(client, "creator1@nexora.co", "creador", "Creador Uno")
    creator2_token, _ = _register_and_login(client, "creator2@nexora.co", "creador", "Creador Dos")

    # Brand 1 creates a draft campaign
    draft_resp = client.post(
        "/api/v1/campaigns",
        headers={"Authorization": f"Bearer {brand_token}"},
        json={"title": "Campaña Secreta Borrador", "objective": "Objetivo privado borrador", "niche": "Moda"},
    )
    assert draft_resp.status_code == 201
    draft_id = draft_resp.json()["data"]["id"]

    # Anonymous reads of campaigns and draft
    assert client.get("/api/v1/campaigns").status_code == 401
    assert client.get(f"/api/v1/campaigns/{draft_id}").status_code == 401

    # Other brand and creator cannot read Brand 1's draft
    assert client.get(f"/api/v1/campaigns/{draft_id}", headers={"Authorization": f"Bearer {other_brand_token}"}).status_code == 403
    assert client.get(f"/api/v1/campaigns/{draft_id}", headers={"Authorization": f"Bearer {creator1_token}"}).status_code == 403
    assert client.get("/api/v1/campaigns?status_filter=Borrador", headers={"Authorization": f"Bearer {creator1_token}"}).status_code == 403

    # Other brand listing drafts only sees their own (0 drafts)
    other_drafts = client.get("/api/v1/campaigns?status_filter=Borrador", headers={"Authorization": f"Bearer {other_brand_token}"})
    assert other_drafts.status_code == 200
    assert len(other_drafts.json()["data"]["items"]) == 0

    # Owner brand can read their own draft
    assert client.get(f"/api/v1/campaigns/{draft_id}", headers={"Authorization": f"Bearer {brand_token}"}).status_code == 200

    # Create a collaboration agreement between brand1 and creator1
    now = datetime.utcnow()
    pub_camp = Campaign(
        brand_id=brand_id,
        title="Campaña Activa",
        objective="Objetivo de campaña activa de prueba",
        niche="Gastronomía",
        status=CampaignStatus.PUBLICADA,
        start_date=now,
        end_date=now + timedelta(days=10),
        budget=500000.0,
    )
    db_session.add(pub_camp)
    db_session.flush()
    app_row = Application(
        campaign_id=pub_camp.id,
        creator_id=creator1_id,
        creative_proposal="Propuesta creativa detallada de prueba",
        media_kit_snapshot_version=1,
        media_kit_data="{}",
        status=ApplicationStatus.ACEPTADA,
    )
    db_session.add(app_row)
    db_session.flush()
    collab = CollaborationAgreement(
        application_id=app_row.id,
        campaign_id=pub_camp.id,
        brand_id=brand_id,
        creator_id=creator1_id,
        scope_description="Acuerdo confidencial",
        deliverables_terms="[]",
        compensation_amount=500000.0,
        deadline=now + timedelta(days=10),
        status=CollaborationStatus.EN_EJECUCION,
    )
    db_session.add(collab)
    db_session.commit()

    # Anonymous reads of collaboration & messages -> 401
    assert client.get(f"/api/v1/collaborations/{collab.id}").status_code == 401
    assert client.get(f"/api/v1/messages/{collab.id}").status_code == 401

    # Third party (creator2 and other_brand) -> 403
    assert client.get(f"/api/v1/collaborations/{collab.id}", headers={"Authorization": f"Bearer {creator2_token}"}).status_code == 403
    assert client.get(f"/api/v1/collaborations/{collab.id}", headers={"Authorization": f"Bearer {other_brand_token}"}).status_code == 403
    assert client.get(f"/api/v1/messages/{collab.id}", headers={"Authorization": f"Bearer {creator2_token}"}).status_code == 403

    # Participants (brand1 and creator1) -> 200
    assert client.get(f"/api/v1/collaborations/{collab.id}", headers={"Authorization": f"Bearer {brand_token}"}).status_code == 200
    assert client.get(f"/api/v1/collaborations/{collab.id}", headers={"Authorization": f"Bearer {creator1_token}"}).status_code == 200
    assert client.get(f"/api/v1/messages/{collab.id}", headers={"Authorization": f"Bearer {creator1_token}"}).status_code == 200


def test_h03_websocket_auth(client, db_session):
    """
    H03: WebSockets must validate JWT and membership before accept(), closing with 1008 on failure.
    """
    brand_token, brand_id = _register_and_login(client, "ws_brand@nexora.co", "marca", "WS Brand")
    creator1_token, creator1_id = _register_and_login(client, "ws_creator1@nexora.co", "creador", "WS Creator 1")
    creator2_token, creator2_id = _register_and_login(client, "ws_creator2@nexora.co", "creador", "WS Creator 2")

    now = datetime.utcnow()
    camp = Campaign(
        brand_id=brand_id,
        title="WS Campaña",
        objective="Objetivo WS de prueba completo",
        niche="Gastronomía",
        status=CampaignStatus.PUBLICADA,
        start_date=now,
        end_date=now + timedelta(days=10),
        budget=300000.0,
    )
    db_session.add(camp)
    db_session.flush()
    app_row = Application(
        campaign_id=camp.id,
        creator_id=creator1_id,
        creative_proposal="Propuesta creativa WS para prueba",
        media_kit_snapshot_version=1,
        media_kit_data="{}",
        status=ApplicationStatus.ACEPTADA,
    )
    db_session.add(app_row)
    db_session.flush()
    collab = CollaborationAgreement(
        application_id=app_row.id,
        campaign_id=camp.id,
        brand_id=brand_id,
        creator_id=creator1_id,
        scope_description="Acuerdo WS",
        deliverables_terms="[]",
        compensation_amount=300000.0,
        deadline=now + timedelta(days=10),
        status=CollaborationStatus.EN_EJECUCION,
    )
    db_session.add(collab)
    db_session.commit()

    # 1. /ws/{user_id} without token -> rejected (1008)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/ws/{creator1_id}"):
            pass
    assert exc_info.value.code == 1008

    # 2. /ws/{user_id} with mismatched user token -> rejected (1008)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/ws/{creator1_id}?token={creator2_token}"):
            pass
    assert exc_info.value.code == 1008

    # 3. /ws/{user_id} with valid matching token -> succeeds
    with client.websocket_connect(f"/ws/{creator1_id}?token={creator1_token}") as ws:
        ws.send_text("ping")
        ack = json.loads(ws.receive_text())
        assert ack["event"] == "ack"

    # 4. /ws/collaboration/{collab_id} without token -> rejected (1008)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/ws/collaboration/{collab.id}"):
            pass
    assert exc_info.value.code == 1008

    # 5. /ws/collaboration/{collab_id} by non-participant creator2 -> rejected (1008)
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/ws/collaboration/{collab.id}?token={creator2_token}"):
            pass
    assert exc_info.value.code == 1008

    # 6. /ws/collaboration/{collab_id} by participant creator1 -> succeeds
    with client.websocket_connect(f"/ws/collaboration/{collab.id}?token={creator1_token}") as ws:
        ws.send_text("hola sala")
        msg = json.loads(ws.receive_text())
        assert msg["event"] == "room_message"


def test_h04_idempotency_isolation(client, db_session):
    """
    H04: Two creators sending the same Idempotency-Key do not cross responses/data;
    reusing the same key with a different payload by the same creator returns 409.
    """
    brand_token, brand_id = _register_and_login(client, "idem_brand@nexora.co", "marca", "Idem Brand")
    c1_token, c1_id = _register_and_login(client, "idem_c1@nexora.co", "creador", "Idem Creator 1")
    c2_token, c2_id = _register_and_login(client, "idem_c2@nexora.co", "creador", "Idem Creator 2")

    now = datetime.utcnow()
    camp = Campaign(
        brand_id=brand_id,
        title="Campaña Idempotencia",
        objective="Objetivo de campaña para probar aislamiento",
        niche="Gastronomía",
        status=CampaignStatus.PUBLICADA,
        start_date=now,
        end_date=now + timedelta(days=15),
        budget=400000.0,
    )
    db_session.add(camp)
    db_session.commit()

    shared_key = "same-client-key-001"

    # Creator 1 applies with shared_key
    r1 = client.post(
        f"/api/v1/campaigns/{camp.id}/apply",
        headers={"Authorization": f"Bearer {c1_token}", "Idempotency-Key": shared_key},
        json={"creative_proposal": "Propuesta exclusiva del creador uno para esta campaña"},
    )
    assert r1.status_code == 201, r1.text
    app1 = r1.json()["data"]
    assert app1["creator_id"] == c1_id

    # Creator 2 applies with the SAME shared_key -> must NOT receive Creator 1's response
    r2 = client.post(
        f"/api/v1/campaigns/{camp.id}/apply",
        headers={"Authorization": f"Bearer {c2_token}", "Idempotency-Key": shared_key},
        json={"creative_proposal": "Propuesta completamente diferente del creador dos"},
    )
    assert r2.status_code == 201, r2.text
    app2 = r2.json()["data"]
    assert app2["creator_id"] == c2_id
    assert app2["id"] != app1["id"]
    assert "creador dos" in app2["creative_proposal"]

    # Creator 1 retries same key & same payload -> returns cached app1
    r1_retry = client.post(
        f"/api/v1/campaigns/{camp.id}/apply",
        headers={"Authorization": f"Bearer {c1_token}", "Idempotency-Key": shared_key},
        json={"creative_proposal": "Propuesta exclusiva del creador uno para esta campaña"},
    )
    assert r1_retry.status_code == 201
    assert r1_retry.json()["data"]["id"] == app1["id"]

    # Creator 1 reuses same key with DIFFERENT payload -> 409 Conflict
    r1_conflict = client.post(
        f"/api/v1/campaigns/{camp.id}/apply",
        headers={"Authorization": f"Bearer {c1_token}", "Idempotency-Key": shared_key},
        json={"creative_proposal": "Payload alterado con la misma llave de idempotencia"},
    )
    assert r1_conflict.status_code == 409


def test_h09_oauth_demo_snapshots_not_labeled_official(client):
    """
    H09: Simulated OAuth metrics must validate state/PKCE and be labeled DEMO/SIMULADO, never API_OFICIAL.
    """
    c_token, c_id = _register_and_login(client, "oauth_c@nexora.co", "creador", "OAuth Creator")

    auth_resp = client.post(
        "/api/v1/auth/oauth/authorize?platform=instagram",
        headers={"Authorization": f"Bearer {c_token}"},
    )
    assert auth_resp.status_code == 200
    auth_data = auth_resp.json()
    assert auth_data["mode"] == "DEMO_SIMULADO"

    # Invalid state must fail
    bad_cb = client.post(
        f"/api/v1/auth/oauth/callback?platform=instagram&code=abc&state=wrong-state",
        headers={"Authorization": f"Bearer {c_token}"},
    )
    assert bad_cb.status_code == 400

    # Valid state + PKCE verifier succeeds and creates DEMO snapshot
    good_cb = client.post(
        f"/api/v1/auth/oauth/callback?platform=instagram&code=demo_code_123&state={auth_data['state']}&code_verifier={auth_data['code_verifier']}",
        headers={"Authorization": f"Bearer {c_token}"},
    )
    assert good_cb.status_code == 200, good_cb.text
    assert "DEMO" in good_cb.json()["message"]

    mk = client.get(f"/api/v1/users/{c_id}/media-kit")
    assert mk.status_code == 200
    snapshots = mk.json()["data"]["connected_metrics"]
    assert len(snapshots) == 1
    assert snapshots[0]["estado"] == "DEMO"
    assert "API_OFICIAL" not in snapshots[0]["fuente_origen"]
    assert "DEMO" in snapshots[0]["fuente_origen"]

