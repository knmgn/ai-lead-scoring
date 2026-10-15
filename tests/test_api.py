import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "llm_engine" in data


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "operational"


def test_webhook_lead_pipeline():
    payload = {
        "name": "Sarah Jenkins",
        "email": "sarah.jenkins@stripe.com",
        "company_domain": "stripe.com",
        "company_name": "Stripe",
        "message": "We need to automate our inbound lead triage pipeline across North America urgently."
    }
    response = client.post("/webhook/lead", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "lead_id" in data
    assert data["scoring"]["score_tier"] == "S"
    assert data["scoring"]["total_score"] >= 90
    assert data["integrations"]["hubspot_synced"] is True
    assert data["integrations"]["slack_notified"] is True


def test_simulate_demo_tiers():
    for tier in ["tier_s", "tier_a", "tier_b", "tier_c"]:
        response = client.post(f"/demo/simulate/{tier}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "scoring" in data
