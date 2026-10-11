from decimal import Decimal

from pydantic import BaseModel

from app.schema.balance import MemberBalance


class LargestExpense(BaseModel):
    expense_id: int
    description: str
    amount: Decimal
    paid_by: str


class ExpenseSummaryStatistics(BaseModel):
    total_spending: Decimal
    expense_count: int
    largest_expenses: list[LargestExpense]
    member_balances: list[MemberBalance]


class GroupSummaryResponse(BaseModel):
    group_id: int
    group_name: str
    summary: str
    statistics: ExpenseSummaryStatistics
