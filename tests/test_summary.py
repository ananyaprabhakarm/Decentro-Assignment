from decimal import Decimal

from app.services import summary_service
from tests.conftest import test_group


def _create_expense(client, group, payer, amount="1000.00"):
    return client.post(
        "/expenses",
        json={
            "group_id": group.id,
            "paid_by": payer.id,
            "amount": amount,
            "description": "Dinner",
        },
    )


def test_group_summary_uses_gemini_and_returns_python_statistics(
    client, test_group, monkeypatch
):
    group, user1, user2 = test_group
    expense_response = _create_expense(client, group, user1, "100.01")
    assert expense_response.status_code == 201

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    calls = {}

    def fake_gemini_summary(prompt, api_key):
        calls["prompt"] = prompt
        calls["api_key"] = api_key
        return "The group spent ₹100.01 on one recorded expense."

    monkeypatch.setattr(
        summary_service,
        "_generate_gemini_summary",
        fake_gemini_summary,
    )

    response = client.get(f"/groups/{group.id}/summary")

    assert response.status_code == 200
    data = response.json()
    assert data["summary"] == "The group spent ₹100.01 on one recorded expense."
    assert data["statistics"]["expense_count"] == 1
    assert Decimal(data["statistics"]["total_spending"]) == Decimal("100.01")
    assert data["statistics"]["largest_expenses"][0]["description"] == "Dinner"
    assert data["statistics"]["largest_expenses"][0]["paid_by"] == user1.name

    member_balances = {
        member["user_id"]: Decimal(member["net_balance"])
        for member in data["statistics"]["member_balances"]
    }
    assert member_balances[user1.id] == Decimal("50.00")
    assert member_balances[user2.id] == Decimal("-50.00")
    assert calls["api_key"] == "test-key"
    assert '"total_spending": "100.01"' in calls["prompt"]


def test_group_summary_without_expenses_does_not_call_gemini(
    client, test_group, monkeypatch
):
    group, _, _ = test_group
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    def unexpected_gemini_call(*args, **kwargs):
        raise AssertionError("Gemini should not be called for an empty group")

    monkeypatch.setattr(
        summary_service,
        "_generate_gemini_summary",
        unexpected_gemini_call,
    )

    response = client.get(f"/groups/{group.id}/summary")

    assert response.status_code == 200
    assert response.json()["summary"] == "No expenses have been recorded for this group yet."
    assert response.json()["statistics"]["expense_count"] == 0
    assert Decimal(response.json()["statistics"]["total_spending"]) == Decimal("0.00")


def test_group_summary_returns_404_for_missing_group(client):
    response = client.get("/groups/999/summary")

    assert response.status_code == 404
    assert response.json()["detail"] == "Group not found"


def test_group_summary_returns_503_when_api_key_is_missing(
    client, test_group, monkeypatch
):
    group, user, _ = test_group
    assert _create_expense(client, group, user).status_code == 201
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    response = client.get(f"/groups/{group.id}/summary")

    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.json()["detail"]


def test_group_summary_handles_gemini_failure(client, test_group, monkeypatch):
    group, user, _ = test_group
    assert _create_expense(client, group, user).status_code == 201
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    def failed_gemini_call(prompt, api_key):
        raise RuntimeError("mock Gemini failure")

    monkeypatch.setattr(
        summary_service,
        "_generate_gemini_summary",
        failed_gemini_call,
    )

    response = client.get(f"/groups/{group.id}/summary")

    assert response.status_code == 502
    assert response.json()["detail"] == "Could not generate the expense summary right now"
