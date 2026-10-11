from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.schema.expense import ExpenseCreate, ExpenseResponse
from app.services.expense_service import (
    GroupNotFoundError,
    NoActiveMembersError,
    PayerNotActiveMemberError,
    create_expense as create_expense_record,
    list_group_expenses as get_group_expenses,
)


router = APIRouter(tags=["Expenses"])


@router.post(
    "/expenses",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_expense(expense_data: ExpenseCreate, db: Session = Depends(get_db)):
    try:
        return create_expense_record(
            db=db,
            group_id=expense_data.group_id,
            paid_by=expense_data.paid_by,
            amount=expense_data.amount,
            description=expense_data.description,
            splits=expense_data.splits,
        )
    except GroupNotFoundError:
        raise HTTPException(status_code=404, detail="Group not found")
    except NoActiveMembersError:
        raise HTTPException(
            status_code=400,
            detail="Cannot add an expense to a group with no active members",
        )
    except PayerNotActiveMemberError:
        raise HTTPException(
            status_code=400,
            detail="Payer must be an active member of the group",
        )


@router.get(
    "/groups/{group_id}/expenses",
    response_model=list[ExpenseResponse],
)
def list_group_expenses(group_id: int, db: Session = Depends(get_db)):
    try:
        return get_group_expenses(db=db, group_id=group_id)
    except GroupNotFoundError:
        raise HTTPException(status_code=404, detail="Group not found")
