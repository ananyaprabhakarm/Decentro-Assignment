from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator


class ExpenseCreate(BaseModel):
    group_id: PositiveInt
    paid_by: PositiveInt
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str = Field(min_length=1, max_length=500)

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Description cannot be empty")
        return value


class ExpenseSplitResponse(BaseModel):
    user_id: int
    amount: Decimal
    model_config = ConfigDict(from_attributes=True)


class ExpenseResponse(BaseModel):
    id: int
    group_id: int
    paid_by: int
    amount: Decimal
    description: str
    created_at: datetime
    splits: list[ExpenseSplitResponse]
