from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.schema.balance import GroupBalanceResponse
from app.services.balance_service import (
    GroupNotFoundError,
    calculate_group_balances,
)


router = APIRouter(tags=["Balances"])


@router.get(
    "/groups/{group_id}/balances",
    response_model=GroupBalanceResponse,
)
def get_group_balances(group_id: int, db: Session = Depends(get_db)):
    try:
        return calculate_group_balances(db=db, group_id=group_id)
    except GroupNotFoundError:
        raise HTTPException(status_code=404, detail="Group not found")
