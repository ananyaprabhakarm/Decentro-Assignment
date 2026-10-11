from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator, model_validator

class ExpenseSplitCreate(BaseModel):
    user_id: PositiveInt
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)

class ExpenseCreate(BaseModel):
    group_id: PositiveInt
    paid_by: PositiveInt
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str = Field(min_length=1, max_length=500)
    splits: Optional[list[ExpenseSplitCreate]] = None

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Description cannot be empty")
        return value

    @model_validator(mode="after")
    def validate_splits(self):
        if self.splits is not None:
            user_ids = [split.user_id for split in self.splits]
            if len(user_ids) != len(set(user_ids)):
                raise ValueError("Duplicate users in splits")
            total = sum((split.amount for split in self.splits), Decimal("0"))
            if total != self.amount:
                raise ValueError("Split amounts must equal expense amount")
        return self

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
