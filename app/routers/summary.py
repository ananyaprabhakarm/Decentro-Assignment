from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.schema.summary import GroupSummaryResponse
from app.services.summary_service import (
    GeminiAPIKeyMissingError,
    GeminiSummaryError,
    GroupNotFoundError,
    create_group_summary,
)


router = APIRouter(tags=["Summaries"])


@router.get(
    "/groups/{group_id}/summary",
    response_model=GroupSummaryResponse,
)
def get_group_summary(group_id: int, db: Session = Depends(get_db)):
    try:
        return create_group_summary(db, group_id)
    except GroupNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
    except GeminiAPIKeyMissingError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Expense summaries are unavailable because GEMINI_API_KEY is not configured",
        )
    except GeminiSummaryError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not generate the expense summary right now",
        )
