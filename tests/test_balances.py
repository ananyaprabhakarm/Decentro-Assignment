from tests.conftest import test_group


def test_balance_calculation(client, test_group):
    group, user1, user2 = test_group

    # User 1 pays ₹1000, split equally between two members.
    response = client.post(
        "/expenses",
        json={
            "group_id": group.id,
            "paid_by": user1.id,
            "amount": "1000.00",
            "description": "Dinner",
        },
    )
    assert response.status_code == 201

    # Retrieve the calculated balances.
    response = client.get(f"/groups/{group.id}/balances")
    assert response.status_code == 200

    data = response.json()
    members = {member["user_id"]: member for member in data["members"]}

    assert float(members[user1.id]["net_balance"]) == 500.0
    assert float(members[user2.id]["net_balance"]) == -500.0
