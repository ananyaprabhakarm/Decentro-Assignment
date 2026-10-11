from decimal import Decimal

from pydantic import BaseModel


class OwedAmount(BaseModel):
    user_id: int
    name: str
    amount: Decimal


class MemberBalance(BaseModel):
    user_id: int
    name: str
    # Positive means the member is owed money; negative means they owe money.
    net_balance: Decimal
    owes: list[OwedAmount]
    owed_by: list[OwedAmount]


class GroupBalanceResponse(BaseModel):
    group_id: int
    members: list[MemberBalance]
