
from app.database.models import User, Group, GroupMember


def test_create_expense(client, db_session):
    # Create two users
    user1 = User(name="Ananya", email="ananya1@example.com")
    user2 = User(name="Rahul", email="rahul1@example.com")

    db_session.add_all([user1, user2])
    db_session.commit()
    db_session.refresh(user1)
    db_session.refresh(user2)

    # Create a group
    group = Group(name="Trip")
    db_session.add(group)
    db_session.commit()
    db_session.refresh(group)

    # Add both users to the group
    db_session.add_all([
        GroupMember(group_id=group.id, user_id=user1.id),
        GroupMember(group_id=group.id, user_id=user2.id),
    ])
    db_session.commit()

    # Create an expense through the API
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

    data = response.json()
    assert data["group_id"] == group.id
    assert data["paid_by"] == user1.id
    assert data["amount"] == "1000.00"
    assert data["description"] == "Dinner"
    assert len(data["splits"]) == 2
