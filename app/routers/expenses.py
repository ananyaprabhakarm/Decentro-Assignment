from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Expense, ExpenseSplit, Group, GroupMember
from app.schema.expense import ExpenseCreate, ExpenseResponse


router = APIRouter(tags=["Expenses"])


@router.post("/expenses", response_model=ExpenseResponse, status_code=status.HTTP_201_CREATED)
def create_expense(expense_data: ExpenseCreate, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == expense_data.group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    members = (
        db.query(GroupMember)
        .filter(
            GroupMember.group_id == expense_data.group_id,
            GroupMember.is_active.is_(True),
        )
        .order_by(GroupMember.user_id)
        .all()
    )
    if not members:
        raise HTTPException(status_code=400, detail="Cannot add an expense to a group with no active members")

    member_ids = [member.user_id for member in members]
    if expense_data.paid_by not in member_ids:
        raise HTTPException(status_code=400, detail="Payer must be an active member of the group")

    # Divide integer cents so the shares add up exactly to the expense amount.
    total_cents = int(expense_data.amount * 100)
    base_cents, remainder_cents = divmod(total_cents, len(member_ids))
    shares = [
        Decimal(base_cents + (1 if index < remainder_cents else 0)) / 100
        for index in range(len(member_ids))
    ]

    try:
        expense = Expense(
            group_id=expense_data.group_id,
            paid_by=expense_data.paid_by,
            amount=expense_data.amount,
            description=expense_data.description,
        )
        db.add(expense)
        db.flush()

        for user_id, share in zip(member_ids, shares):
            db.add(ExpenseSplit(expense_id=expense.id, user_id=user_id, amount=share))

        db.commit()
        db.refresh(expense)
    except Exception:
        db.rollback()
        raise

    return {
        "id": expense.id,
        "group_id": expense.group_id,
        "paid_by": expense.paid_by,
        "amount": expense.amount,
        "description": expense.description,
        "created_at": expense.created_at,
        "splits": db.query(ExpenseSplit).filter(ExpenseSplit.expense_id == expense.id).all(),
    }


@router.get("/groups/{group_id}/expenses", response_model=list[ExpenseResponse])
def list_group_expenses(group_id: int, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found")

    expenses = (
        db.query(Expense)
        .filter(Expense.group_id == group_id)
        .order_by(Expense.created_at.desc(), Expense.id.desc())
        .all()
    )
    return [
        {
            "id": expense.id,
            "group_id": expense.group_id,
            "paid_by": expense.paid_by,
            "amount": expense.amount,
            "description": expense.description,
            "created_at": expense.created_at,
            "splits": db.query(ExpenseSplit).filter(ExpenseSplit.expense_id == expense.id).all(),
        }
        for expense in expenses
    ]
