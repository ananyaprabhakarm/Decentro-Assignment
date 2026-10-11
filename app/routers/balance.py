from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Expense, ExpenseSplit, Group, GroupMember, Settlement, User
from app.schema.balance import GroupBalanceResponse


router = APIRouter(tags=["Balances"])


@router.get("/groups/{group_id}/balances", response_model=GroupBalanceResponse)
def get_group_balances(group_id: int, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    # Include former members too: their historical expenses can leave balances due.
    memberships = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group_id)
        .order_by(GroupMember.user_id)
        .all()
    )
    member_ids = [membership.user_id for membership in memberships]
    users = db.query(User).filter(User.id.in_(member_ids)).all() if member_ids else []
    names = {user.id: user.name for user in users}
    net = defaultdict(Decimal)
    for user_id in member_ids:
        net[user_id] = Decimal("0.00")

    expenses = db.query(Expense).filter(Expense.group_id == group_id).all()
    expense_ids = [expense.id for expense in expenses]
    for expense in expenses:
        net[expense.paid_by] += Decimal(expense.amount)

    splits = (
        db.query(ExpenseSplit).filter(ExpenseSplit.expense_id.in_(expense_ids)).all()
        if expense_ids
        else []
    )
    for split in splits:
        net[split.user_id] -= Decimal(split.amount)

    # A settlement is money transferred from paid_by to paid_to.
    settlements = db.query(Settlement).filter(Settlement.group_id == group_id).all()
    for settlement in settlements:
        net[settlement.paid_by] += Decimal(settlement.amount)
        net[settlement.paid_to] -= Decimal(settlement.amount)

    # Match debtors to creditors to produce a compact set of suggested payments.
    debtors = [[uid, -amount] for uid, amount in net.items() if amount < 0]
    creditors = [[uid, amount] for uid, amount in net.items() if amount > 0]
    debtors.sort(key=lambda entry: entry[0])
    creditors.sort(key=lambda entry: entry[0])
    owes = defaultdict(list)
    owed_by = defaultdict(list)

    debtor_index = creditor_index = 0
    while debtor_index < len(debtors) and creditor_index < len(creditors):
        debtor_id, debt_amount = debtors[debtor_index]
        creditor_id, credit_amount = creditors[creditor_index]
        transfer = min(debt_amount, credit_amount)
        owes[debtor_id].append({"user_id": creditor_id, "name": names.get(creditor_id, "Unknown"), "amount": transfer})
        owed_by[creditor_id].append({"user_id": debtor_id, "name": names.get(debtor_id, "Unknown"), "amount": transfer})
        debtors[debtor_index][1] -= transfer
        creditors[creditor_index][1] -= transfer
        if debtors[debtor_index][1] == 0:
            debtor_index += 1
        if creditors[creditor_index][1] == 0:
            creditor_index += 1

    return {
        "group_id": group_id,
        "members": [
            {
                "user_id": user_id,
                "name": names.get(user_id, "Unknown"),
                "net_balance": net[user_id],
                "owes": owes[user_id],
                "owed_by": owed_by[user_id],
            }
            for user_id in member_ids
        ],
    }
