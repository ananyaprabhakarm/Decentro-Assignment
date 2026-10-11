from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.database.models import Expense, ExpenseSplit, Group, GroupMember
from app.schema.expense import ExpenseSplitCreate


class GroupNotFoundError(Exception):
    pass


class NoActiveMembersError(Exception):
    pass


class PayerNotActiveMemberError(Exception):
    pass


def create_expense(
    db: Session,
    group_id: int,
    paid_by: int,
    amount: Decimal,
    description: str,
    splits: Optional[list[ExpenseSplitCreate]] = None,
) -> dict:
    group = db.query(Group).filter(Group.id == group_id).first()
    if group is None:
        raise GroupNotFoundError

    members = (
        db.query(GroupMember)
        .filter(
            GroupMember.group_id == group_id,
            GroupMember.is_active.is_(True),
        )
        .order_by(GroupMember.user_id)
        .all()
    )
    if not members:
        raise NoActiveMembersError

    member_ids = [member.user_id for member in members]
    if paid_by not in member_ids:
        raise PayerNotActiveMemberError

    # Work in paise so uneven divisions still add up to the exact total.
    
    if splits is None:
        # Default: split equally among active members.
        total_paise = int(amount * 100)
        base_paise, remainder_paise = divmod(
            total_paise, len(member_ids)
        )

        split_records = [
            (
                user_id,
                Decimal(
                    base_paise + (1 if index < remainder_paise else 0)
                ) / 100,
            )
            for index, user_id in enumerate(member_ids)
        ]

    else:
        # Custom: validate and use the provided shares.
        split_user_ids = [split.user_id for split in splits]

        if len(split_user_ids) != len(set(split_user_ids)):
            raise ValueError("Duplicate users in splits")

        if any(user_id not in member_ids for user_id in split_user_ids):
            raise ValueError("All split users must be active group members")

        split_total = sum(
            (split.amount for split in splits), Decimal("0")
        )

        if split_total != amount:
            raise ValueError("Split amounts must equal expense amount")

        split_records = [
            (split.user_id, split.amount)
            for split in splits
        ]


    try:
        expense = Expense(
            group_id=group_id,
            paid_by=paid_by,
            amount=amount,
            description=description,
        )
        db.add(expense)
        db.flush()

        for user_id, split_amount in split_records:
            db.add(
                ExpenseSplit(
                    expense_id=expense.id,
                    user_id=user_id,
                    amount=split_amount,
                )
            )

        db.commit()
        db.refresh(expense)
    except Exception:
        db.rollback()
        raise

    splits = (
        db.query(ExpenseSplit)
        .filter(ExpenseSplit.expense_id == expense.id)
        .order_by(ExpenseSplit.user_id)
        .all()
    )
    return _expense_response_data(expense, splits)


def list_group_expenses(db: Session, group_id: int) -> list[dict]:
    group = db.query(Group).filter(Group.id == group_id).first()
    if group is None:
        raise GroupNotFoundError

    expenses = (
        db.query(Expense)
        .filter(Expense.group_id == group_id)
        .order_by(Expense.created_at.desc(), Expense.id.desc())
        .all()
    )
    if not expenses:
        return []

    expense_ids = [expense.id for expense in expenses]
    splits = (
        db.query(ExpenseSplit)
        .filter(ExpenseSplit.expense_id.in_(expense_ids))
        .order_by(ExpenseSplit.user_id)
        .all()
    )
    splits_by_expense = {expense_id: [] for expense_id in expense_ids}
    for split in splits:
        splits_by_expense[split.expense_id].append(split)

    return [
        _expense_response_data(expense, splits_by_expense[expense.id])
        for expense in expenses
    ]


def _expense_response_data(expense: Expense, splits: list[ExpenseSplit]) -> dict:
    return {
        "id": expense.id,
        "group_id": expense.group_id,
        "paid_by": expense.paid_by,
        "amount": expense.amount,
        "description": expense.description,
        "created_at": expense.created_at,
        "splits": splits,
    }
