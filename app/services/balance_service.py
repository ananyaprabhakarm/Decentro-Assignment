from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session

from app.database.models import Expense, ExpenseSplit, Group, GroupMember, Settlement, User


class GroupNotFoundError(Exception):
    pass


def calculate_group_balances(db: Session, group_id: int) -> dict:
    group = db.query(Group).filter(Group.id == group_id).first()
    if group is None:
        raise GroupNotFoundError

    # Keep former members in the calculation so balances from past expenses remain visible.
    memberships = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group_id)
        .order_by(GroupMember.user_id)
        .all()
    )
    member_ids = [membership.user_id for membership in memberships]
    users = db.query(User).filter(User.id.in_(member_ids)).all() if member_ids else []
    names_by_user_id = {user.id: user.name for user in users}

    net_balances = defaultdict(Decimal)
    for user_id in member_ids:
        net_balances[user_id] = Decimal("0.00")

    expenses = db.query(Expense).filter(Expense.group_id == group_id).all()
    expense_ids = [expense.id for expense in expenses]
    for expense in expenses:
        net_balances[expense.paid_by] += Decimal(expense.amount)

    if expense_ids:
        splits = (
            db.query(ExpenseSplit)
            .filter(ExpenseSplit.expense_id.in_(expense_ids))
            .all()
        )
        for split in splits:
            net_balances[split.user_id] -= Decimal(split.amount)

    # A recorded settlement is money transferred from paid_by to paid_to.
    settlements = db.query(Settlement).filter(Settlement.group_id == group_id).all()
    for settlement in settlements:
        net_balances[settlement.paid_by] += Decimal(settlement.amount)
        net_balances[settlement.paid_to] -= Decimal(settlement.amount)

    suggested_payments = _suggest_payments(net_balances)
    owes_by_user_id = defaultdict(list)
    owed_by_user_id = defaultdict(list)
    for payment in suggested_payments:
        debtor_id = payment["from_user_id"]
        creditor_id = payment["to_user_id"]
        amount = payment["amount"]
        owes_by_user_id[debtor_id].append(
            {
                "user_id": creditor_id,
                "name": names_by_user_id.get(creditor_id, "Unknown"),
                "amount": amount,
            }
        )
        owed_by_user_id[creditor_id].append(
            {
                "user_id": debtor_id,
                "name": names_by_user_id.get(debtor_id, "Unknown"),
                "amount": amount,
            }
        )

    return {
        "group_id": group_id,
        "members": [
            {
                "user_id": user_id,
                "name": names_by_user_id.get(user_id, "Unknown"),
                "net_balance": net_balances[user_id],
                "owes": owes_by_user_id[user_id],
                "owed_by": owed_by_user_id[user_id],
            }
            for user_id in member_ids
        ],
    }


def _suggest_payments(
    net_balances: dict[int, Decimal],
) -> list[dict]:
    debtors = [
        [user_id, -balance]
        for user_id, balance in net_balances.items()
        if balance < 0
    ]
    creditors = [
        [user_id, balance]
        for user_id, balance in net_balances.items()
        if balance > 0
    ]
    debtors.sort(key=lambda entry: entry[0])
    creditors.sort(key=lambda entry: entry[0])

    payments = []
    debtor_index = 0
    creditor_index = 0

    while debtor_index < len(debtors) and creditor_index < len(creditors):
        debtor_id, debt_amount = debtors[debtor_index]
        creditor_id, credit_amount = creditors[creditor_index]
        amount = min(debt_amount, credit_amount)

        payments.append(
            {
                "from_user_id": debtor_id,
                "to_user_id": creditor_id,
                "amount": amount,
            }
        )

        debtors[debtor_index][1] -= amount
        creditors[creditor_index][1] -= amount

        if debtors[debtor_index][1] == 0:
            debtor_index += 1
        if creditors[creditor_index][1] == 0:
            creditor_index += 1

    return payments
