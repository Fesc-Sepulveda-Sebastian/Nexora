import json
from datetime import datetime, timedelta, timezone


def _register_and_login(
    client,
    email: str,
    role: str,
    display_name: str,
    password: str = "SecretPass123!",
):
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "role": role,
            "display_name": display_name,
            "terms_accepted": True,
        },
    )
    assert reg.status_code == 201, reg.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    data = login.json()["data"]
    return data["access_token"], data["user_id"]


def test_h14_recommender_no_cucuta_bias_and_zero_initial_rating(client):
    brand_token, _ = _register_and_login(
        client,
        "brand_rec@test.com",
        "marca",
        "Marca Medellin",
    )

    # Creator 1: Medellín, matches niche, matching portfolio format, unreviewed (0.0)
    c1_token, c1_id = _register_and_login(
        client,
        "creator_med@test.com",
        "creador",
        "Creador Medellin",
    )
    res_p1 = client.put(
        "/api/v1/users/me/profile",
        headers={"Authorization": f"Bearer {c1_token}"},
        json={
            "location_declared": "Medellín, Colombia",
            "niche": "Tecnología",
            "portfolio_samples": json.dumps([
                {"title": "Review Tech", "format": "Reel", "url": "https://example.com/1"}
            ]),
        },
    )
    assert res_p1.status_code == 200
    assert res_p1.json()["data"]["average_rating"] == 0.0
    assert res_p1.json()["data"]["verified_reviews_count"] == 0

    # Creator 2: Cúcuta, different niche, no matching portfolio formats, unreviewed
    c2_token, c2_id = _register_and_login(
        client,
        "creator_cuc@test.com",
        "creador",
        "Creador Cucuta",
    )
    res_p2 = client.put(
        "/api/v1/users/me/profile",
        headers={"Authorization": f"Bearer {c2_token}"},
        json={
            "location_declared": "Cúcuta, Colombia",
            "niche": "Moda",
        },
    )
    assert res_p2.status_code == 200

    # Verify new creator Media Kit exposes 0.0 initial rating (not inflated 5.0)
    mk_res = client.get(f"/api/v1/users/{c1_id}/media-kit")
    assert mk_res.status_code == 200
    assert mk_res.json()["data"]["average_rating"] == 0.0
    assert mk_res.json()["data"]["verified_reviews_count"] == 0

    # Brand creates campaign targeting Medellín + Tecnología + Reel
    now = datetime.now(timezone.utc)
    camp_res = client.post(
        "/api/v1/campaigns",
        headers={"Authorization": f"Bearer {brand_token}"},
        json={
            "title": "Lanzamiento App Medellín",
            "objective": "Awareness regional",
            "niche": "Tecnología",
            "compensation_type": "pago_fijo",
            "budget": 500000,
            "start_date": now.isoformat(),
            "end_date": (now + timedelta(days=15)).isoformat(),
            "deliverables": [{"format": "Reel", "qty": 1, "specs": "30s demo"}],
            "selection_criteria": {"location": "Medellín", "platforms": ["Instagram"]},
        },
    )
    assert camp_res.status_code == 201
    camp_id = camp_res.json()["data"]["id"]
    pub_res = client.post(
        f"/api/v1/campaigns/{camp_id}/publish",
        headers={"Authorization": f"Bearer {brand_token}"},
    )
    assert pub_res.status_code == 200

    # Personalized recommendations
    rec_res = client.get(
        f"/api/v1/recommendations/campaigns/{camp_id}/creators?personalization=true",
        headers={"Authorization": f"Bearer {brand_token}"},
    )
    assert rec_res.status_code == 200
    items = rec_res.json()["data"]["items"]
    by_id = {item["creator_id"]: item for item in items}

    rec_med = by_id[c1_id]
    rec_cuc = by_id[c2_id]

    # Medellin creator matched niche (35) + location (25) + format (12) = 72.0; 0 reputation pts since unreviewed
    assert rec_med["average_rating"] == 0.0
    assert rec_med["total_score"] == 72.0
    med_criteria = {c["criterion"]: c["weight_score"] for c in rec_med["matching_criteria"]}
    assert med_criteria["nicho"] == 35.0
    assert med_criteria["ubicacion"] == 25.0
    assert med_criteria["formato_audiencia"] == 12.0
    assert "reputacion" not in med_criteria

    # Cucuta creator should receive 0.0 (no hardcoded Cucuta bonus, no unconditional 18.0 format bonus)
    assert rec_cuc["average_rating"] == 0.0
    assert rec_cuc["total_score"] == 0.0
    assert rec_cuc["matching_criteria"] == []

    # Non-personalized mode must also keep real 0.0 rating
    rec_off = client.get(
        f"/api/v1/recommendations/campaigns/{camp_id}/creators?personalization=false",
        headers={"Authorization": f"Bearer {brand_token}"},
    )
    assert rec_off.status_code == 200
    for item in rec_off.json()["data"]["items"]:
        if item["creator_id"] in (c1_id, c2_id):
            assert item["average_rating"] == 0.0

    # Guía 06: Creator with active infractions must be excluded from recommendations (`continue`)
    inf_resp = client.put(
        "/api/v1/users/me/profile",
        headers={"Authorization": f"Bearer {c1_token}"},
        json={"has_infractions": True},
    )
    assert inf_resp.status_code == 200
    rec_after_inf = client.get(
        f"/api/v1/recommendations/campaigns/{camp_id}/creators?personalization=true",
        headers={"Authorization": f"Bearer {brand_token}"},
    )
    assert rec_after_inf.status_code == 200
    ids_after_inf = [i["creator_id"] for i in rec_after_inf.json()["data"]["items"]]
    assert c1_id not in ids_after_inf
    assert c2_id in ids_after_inf
