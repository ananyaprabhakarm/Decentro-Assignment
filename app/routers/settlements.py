from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.schema.settlement import SettlementCreate, SettlementResponse
from app.services.settlement_service import create_settlement

router = APIRouter(prefix="/settlements", tags=["Settlements"])


@router.post("/", response_model=SettlementResponse, status_code=status.HTTP_201_CREATED)
def add_settlement(
    settlement_data: SettlementCreate,
    db: Session = Depends(get_db),
):
    try:
        settlement = create_settlement(
            db=db,
            group_id=settlement_data.group_id,
            paid_by=settlement_data.paid_by,
            paid_to=settlement_data.paid_to,
            amount=settlement_data.amount,
        )
        return settlement

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )
