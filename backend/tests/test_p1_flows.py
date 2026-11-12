import hashlib
from datetime import datetime, timedelta, timezone
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


def test_h05_h10_full_collaboration_flow(client):
    """
    H05 + H06 (agreement versioning) + H08 (real upload & SHA-256) + H10 (persisted closure) + RN-05 (ratings):
    Full E2E flow: brand creates/publishes campaign -> creator applies -> brand accepts ->
    terms negotiation & version history -> both accept agreement (200 OK, no 500) ->
    real PUT upload + SHA-256 evidence confirmation -> persisted closure -> bilateral rating.
    """
    brand_token, brand_id = _register_and_login(client, "flow_brand@nexora.co", "marca", "Flow Brand")
    creator_token, creator_id = _register_and_login(client, "flow_creator@nexora.co", "creador", "Flow Creator")

    now = datetime.now(timezone.utc)
    # 1. Brand creates campaign draft
    c_resp = client.post(
        "/api/v1/campaigns",
        headers={"Authorization": f"Bearer {brand_token}"},
        json={
            "title": "Campaña Flujo Completo",
            "objective": "Validar el flujo completo de colaboración extremo a extremo",
            "niche": "Gastronomía",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=20)).isoformat(),
            "compensation_type": "pago_fijo",
            "budget": 500000.0,
            "deliverables": [{"format": "Reel", "qty": 1, "specs": "Reel de 45 segundos"}],
            "selection_criteria": {"min_followers": 1000, "location": "Cúcuta", "platforms": ["Instagram"]},
        },
    )
    assert c_resp.status_code == 201, c_resp.text
    camp_id = c_resp.json()["data"]["id"]

    # 2. Brand publishes campaign
    pub_resp = client.post(
        f"/api/v1/campaigns/{camp_id}/publish",
        headers={"Authorization": f"Bearer {brand_token}"},
    )
    assert pub_resp.status_code == 200, pub_resp.text
    assert pub_resp.json()["data"]["status"] == "Publicada"

    # 3. Creator applies
    app_resp = client.post(
        f"/api/v1/campaigns/{camp_id}/apply",
        headers={"Authorization": f"Bearer {creator_token}", "Idempotency-Key": "e2e-apply-1"},
        json={"creative_proposal": "Propuesta creativa completa para el menú de temporada"},
    )
    assert app_resp.status_code == 201, app_resp.text
    app_id = app_resp.json()["data"]["id"]

    # 4. Brand accepts application -> creates CollaborationAgreement v1
    acc_app = client.patch(
        f"/api/v1/applications/{app_id}/status",
        headers={"Authorization": f"Bearer {brand_token}"},
        json={"status": "Aceptada"},
    )
    assert acc_app.status_code == 200, acc_app.text

    # List collaborations
    collabs_resp = client.get(
        f"/api/v1/collaborations?campaign_id={camp_id}",
        headers={"Authorization": f"Bearer {brand_token}"},
    )
    assert collabs_resp.status_code == 200
    collabs = collabs_resp.json()["data"]
    assert len(collabs) == 1
    collab_id = collabs[0]["id"]
    assert collabs[0]["version_id"] == 1

    # 5. Negotiate terms with optimistic concurrency (v1 -> v2) and check stale conflict
    upd_terms = client.put(
        f"/api/v1/collaborations/{collab_id}/terms",
        headers={"Authorization": f"Bearer {brand_token}"},
        json={
            "expected_version": 1,
            "scope_description": "Acuerdo actualizado: 1 Reel y 2 Stories",
            "compensation_amount": 550000.0,
        },
    )
    assert upd_terms.status_code == 200, upd_terms.text
    assert upd_terms.json()["data"]["version_id"] == 2

    stale_terms = client.put(
        f"/api/v1/collaborations/{collab_id}/terms",
        headers={"Authorization": f"Bearer {creator_token}"},
        json={"expected_version": 1, "compensation_amount": 600000.0},
    )
    assert stale_terms.status_code == 409
    assert stale_terms.json()["detail"]["server_version"] == 2

    versions_resp = client.get(
        f"/api/v1/collaborations/{collab_id}/versions",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert versions_resp.status_code == 200
    assert [v["version_id"] for v in versions_resp.json()["data"]] == [1, 2]

    # 6. Both parties accept v2 (no 500 error!)
    b_acc = client.post(
        f"/api/v1/collaborations/{collab_id}/accept",
        headers={"Authorization": f"Bearer {brand_token}"},
        json={"accepted_version_id": 2},
    )
    assert b_acc.status_code == 200, b_acc.text
    assert b_acc.json()["data"]["brand_accepted"] is True
    assert b_acc.json()["data"]["status"] == "Acuerdo_Pendiente"

    c_acc = client.post(
        f"/api/v1/collaborations/{collab_id}/accept",
        headers={"Authorization": f"Bearer {creator_token}"},
        json={"accepted_version_id": 2},
    )
    assert c_acc.status_code == 200, c_acc.text
    assert c_acc.json()["data"]["creator_accepted"] is True
    assert c_acc.json()["data"]["status"] == "En_Ejecucion"

    # 7. Real evidence upload (presigned URL -> PUT bytes -> confirm with SHA-256)
    file_bytes = b"\x89PNG\r\n\x1a\n" + b"nexora-real-evidence-payload-" * 50
    file_sha256 = hashlib.sha256(file_bytes).hexdigest()

    presign = client.post(
        "/api/v1/storage/presigned-url",
        headers={"Authorization": f"Bearer {creator_token}"},
        json={"filename": "evidencia_reel.png", "content_type": "image/png"},
    )
    assert presign.status_code == 200, presign.text
    storage_info = presign.json()["data"]

    put_res = client.put(
        storage_info["upload_url"],
        content=file_bytes,
        headers={"Content-Type": "image/png"},
    )
    assert put_res.status_code == 200, put_res.text

    ev_resp = client.post(
        f"/api/v1/applications/{app_id}/evidences",
        headers={"Authorization": f"Bearer {creator_token}"},
        json={
            "deliverable_name": "Reel Principal",
            "file_key": storage_info["file_key"],
            "file_url": storage_info["public_url"],
            "file_hash_sha256": file_sha256,
            "file_size_mb": 0.01,
            "external_live_url": "https://instagram.com/reel/test123",
        },
    )
    assert ev_resp.status_code == 200, ev_resp.text
    assert ev_resp.json()["data"]["file_hash_sha256"] == file_sha256

    # Rating before closure must fail (RN-05)
    early_rating = client.post(
        "/api/v1/ratings",
        headers={"Authorization": f"Bearer {brand_token}"},
        json={"collaboration_id": collab_id, "score": 5, "comment": "Muy pronto"},
    )
    assert early_rating.status_code == 400

    # 8. Ordinary closure persists Cerrada in DB
    close_resp = client.post(
        f"/api/v1/collaborations/{collab_id}/close",
        headers={"Authorization": f"Bearer {brand_token}"},
    )
    assert close_resp.status_code == 200, close_resp.text
    assert close_resp.json()["data"]["status"] == "Cerrada"

    # Verify persistence via GET
    persisted_collab = client.get(
        f"/api/v1/collaborations/{collab_id}",
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert persisted_collab.status_code == 200
    assert persisted_collab.json()["data"]["status"] == "Cerrada"

    # 9. Bilateral ratings now succeed (RN-05)
    r_brand = client.post(
        "/api/v1/ratings",
        headers={"Authorization": f"Bearer {brand_token}"},
        json={"collaboration_id": collab_id, "score": 5, "comment": "Excelente entrega"},
    )
    assert r_brand.status_code == 201, r_brand.text

    r_creator = client.post(
        "/api/v1/ratings",
        headers={"Authorization": f"Bearer {creator_token}"},
        json={"collaboration_id": collab_id, "score": 5, "comment": "Gran marca"},
    )
    assert r_creator.status_code == 201, r_creator.text


def test_h06_campaign_conflict_409(client):
    """
    H06: Editing a campaign with an outdated version_id must return HTTP 409
    with JSON-serializable server_version and server_data (no 500 datetime serialization error).
    """
    brand_token, _ = _register_and_login(client, "conflict_brand@nexora.co", "marca", "Conflict Brand")
    create_resp = client.post(
        "/api/v1/campaigns",
        headers={"Authorization": f"Bearer {brand_token}"},
        json={"title": "Campaña v1", "objective": "Objetivo inicial", "niche": "Moda"},
    )
    assert create_resp.status_code == 201
    camp_id = create_resp.json()["data"]["id"]

    # Update to v2
    upd_resp = client.put(
        f"/api/v1/campaigns/{camp_id}",
        headers={"Authorization": f"Bearer {brand_token}"},
        json={"title": "Campaña v2", "version_id": 1},
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["data"]["version_id"] == 2

    # Stale update with version_id=1 -> must return 409 cleanly
    conflict_resp = client.put(
        f"/api/v1/campaigns/{camp_id}",
        headers={"Authorization": f"Bearer {brand_token}"},
        json={"title": "Campaña conflictiva", "version_id": 1},
    )
    assert conflict_resp.status_code == 409, conflict_resp.text
    detail = conflict_resp.json()["detail"]
    assert detail["error"] == "VERSION_CONFLICT"
    assert detail["server_version"] == 2
    assert detail["server_data"]["title"] == "Campaña v2"
    assert isinstance(detail["server_data"]["updated_at"], str)


def test_h07_privacy_request_200(client, db_session):
    """
    H07: Privacy deletion request must return 200 with valid PrivacyRequestOut,
    anonymize user PII, revoke OAuth, and deactivate the account.
    """
    token, user_id = _register_and_login(client, "privacy_user@nexora.co", "creador", "Usuario Privacidad")

    resp = client.post(
        "/api/v1/users/me/privacy/delete-request",
        headers={"Authorization": f"Bearer {token}"},
        json={"notes": "Solicito eliminación por Habeas Data"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "completed"
    assert data["requested_at"] is not None
    assert data["processed_at"] is not None

    # Verify PII anonymization in DB
    db_session.expire_all()
    user = db_session.query(User).filter(User.id == user_id).first()
    assert user.is_active is False
    assert user.privacy_status == "deleted"
    assert user.email.startswith("deleted_")
    assert "Usuario Anonimizado" in user.profile.display_name

    # Token is now rejected
    me_after = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me_after.status_code == 401


def test_h08_evidence_hash_validation(client):
    """
    H08: Evidence confirmation with nonexistent file or fake/mismatched SHA-256 must be rejected with 400/422.
    """
    brand_token, _ = _register_and_login(client, "ev_brand@nexora.co", "marca", "EV Brand")
    creator_token, _ = _register_and_login(client, "ev_creator@nexora.co", "creador", "EV Creator")

    now = datetime.now(timezone.utc)
    camp = client.post(
        "/api/v1/campaigns",
        headers={"Authorization": f"Bearer {brand_token}"},
        json={
            "title": "Campaña Evidencias",
            "objective": "Validar hashes y existencia de objetos en storage",
            "niche": "Tecnología",
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=10)).isoformat(),
            "compensation_type": "pago_fijo",
            "budget": 300000.0,
            "deliverables": [{"format": "Post", "qty": 1, "specs": "Post reseña"}],
            "selection_criteria": {"min_followers": 500, "location": "Bogotá", "platforms": ["Instagram"]},
        },
    ).json()["data"]
    client.post(f"/api/v1/campaigns/{camp['id']}/publish", headers={"Authorization": f"Bearer {brand_token}"})

    app_id = client.post(
        f"/api/v1/campaigns/{camp['id']}/apply",
        headers={"Authorization": f"Bearer {creator_token}"},
        json={"creative_proposal": "Propuesta para validar evidencias reales"},
    ).json()["data"]["id"]
    client.patch(
        f"/api/v1/applications/{app_id}/status",
        headers={"Authorization": f"Bearer {brand_token}"},
        json={"status": "Aceptada"},
    )
    collab_id = client.get(
        f"/api/v1/collaborations?campaign_id={camp['id']}",
        headers={"Authorization": f"Bearer {brand_token}"},
    ).json()["data"][0]["id"]
    client.post(
        f"/api/v1/collaborations/{collab_id}/accept",
        headers={"Authorization": f"Bearer {brand_token}"},
        json={"accepted_version_id": 1},
    )
    client.post(
        f"/api/v1/collaborations/{collab_id}/accept",
        headers={"Authorization": f"Bearer {creator_token}"},
        json={"accepted_version_id": 1},
    )

    # 1. Nonexistent file (skipping PUT upload) -> 422
    fake_url_resp = client.post(
        f"/api/v1/applications/{app_id}/evidences",
        headers={"Authorization": f"Bearer {creator_token}"},
        json={
            "deliverable_name": "Post Falso",
            "file_key": "deliverables/nonexistent_file.jpg",
            "file_url": "/api/v1/storage/objects/deliverables/nonexistent_file.jpg",
            "file_hash_sha256": "0" * 64,
            "file_size_mb": 0.5,
        },
    )
    assert fake_url_resp.status_code in (400, 422)

    # 2. Real upload followed by fake all-zeros SHA-256 -> 422
    presign = client.post(
        "/api/v1/storage/presigned-url",
        headers={"Authorization": f"Bearer {creator_token}"},
        json={"filename": "real_pic.jpg", "content_type": "image/jpeg"},
    ).json()["data"]
    client.put(presign["upload_url"], content=b"real-image-bytes", headers={"Content-Type": "image/jpeg"})

    bad_hash_resp = client.post(
        f"/api/v1/applications/{app_id}/evidences",
        headers={"Authorization": f"Bearer {creator_token}"},
        json={
            "deliverable_name": "Post Hash Falso",
            "file_key": presign["file_key"],
            "file_url": presign["public_url"],
            "file_hash_sha256": "0" * 64,
            "file_size_mb": 0.1,
        },
    )
    assert bad_hash_resp.status_code in (400, 422)
    assert "SHA-256" in bad_hash_resp.json()["detail"]

