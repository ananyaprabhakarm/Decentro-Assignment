from decimal import Decimal
from pydantic import BaseModel, Field, PositiveInt, field_validator

class SettlementCreate(BaseModel):
    group_id: PositiveInt
    paid_by: PositiveInt
    paid_to: PositiveInt
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)

    @field_validator("paid_to")
    @classmethod
    def validate_paid_to(cls, value, info):
        if info.data.get("paid_by") == value:
            raise ValueError("Payer and receiver cannot be the same user")
        return value


class SettlementResponse(BaseModel):
    id: int
    group_id: int
    paid_by: int
    paid_to: int
    amount: Decimal
