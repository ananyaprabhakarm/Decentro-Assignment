from app.database.models import User
from tests.conftest import test_group


def test_expense_rejects_zero_amount(client, test_group):
    group, user1, _ = test_group

    response = client.post(
        "/expenses",
        json={
            "group_id": group.id,
            "paid_by": user1.id,
            "amount": "0.00",
            "description": "Dinner",
        },
    )

    assert response.status_code == 422


def test_expense_rejects_negative_amount(client, test_group):
    group, user1, _ = test_group

    response = client.post(
        "/expenses",
        json={
            "group_id": group.id,
            "paid_by": user1.id,
            "amount": "-100.00",
            "description": "Dinner",
        },
    )

    assert response.status_code == 422


def test_expense_rejects_blank_description(client, test_group):
    group, user1, _ = test_group

    response = client.post(
        "/expenses",
        json={
            "group_id": group.id,
            "paid_by": user1.id,
            "amount": "100.00",
            "description": "   ",
        },
    )

    assert response.status_code == 422


def test_expense_rejects_non_member_payer(client, db_session, test_group):
    group, _, _ = test_group

    outsider = User(
        name="Outsider",
        email="outsider@example.com",
    )
    db_session.add(outsider)
    db_session.commit()
    db_session.refresh(outsider)

    response = client.post(
        "/expenses",
        json={
            "group_id": group.id,
            "paid_by": outsider.id,
            "amount": "100.00",
            "description": "Dinner",
        },
    )

    assert response.status_code == 400