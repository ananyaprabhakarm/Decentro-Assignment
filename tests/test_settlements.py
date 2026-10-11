from tests.conftest import test_group


def test_settlement_reduces_outstanding_balance(client, test_group):
    group, user1, user2 = test_group

    # User 1 pays ₹1000 for both members.
    expense_response = client.post(
        "/expenses",
        json={
            "group_id": group.id,
            "paid_by": user1.id,
            "amount": "1000.00",
            "description": "Dinner",
        },
    )
    assert expense_response.status_code == 201

    # User 2 pays back ₹200 to user 1.
    settlement_response = client.post(
        "/settlements/",
        json={
            "group_id": group.id,
            "paid_by": user2.id,
            "paid_to": user1.id,
            "amount": "200.00",
        },
    )
    assert settlement_response.status_code == 201

    response = client.get(f"/groups/{group.id}/balances")
    assert response.status_code == 200

    members = {
        member["user_id"]: member
        for member in response.json()["members"]
    }

    assert float(members[user1.id]["net_balance"]) == 300.0
    assert float(members[user2.id]["net_balance"]) == -300.0
