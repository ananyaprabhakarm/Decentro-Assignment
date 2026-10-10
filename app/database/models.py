from datetime import datetime, timezone
from sqlalchemy import DateTime, Column, Integer, String, Numeric, Boolean, ForeignKey, UniqueConstraint
from app.database.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

class GroupMember(Base):
    __tablename__ = "group_members"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    __table_args__ = (
        UniqueConstraint("group_id", "user_id"),
    )
    is_active = Column(Boolean, default=True)
    joined_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    left_at = Column(DateTime, nullable=True)

class Expense(Base):
    __tablename__ = "expenses"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    paid_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    
class ExpenseSplit(Base):
    __tablename__ = "expenseSplits"
    id = Column(Integer, primary_key=True)
    expense_id = Column(Integer, ForeignKey("expenses.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Numeric(12, 2), nullable=False)

class Settlement(Base):
    __tablename__ = "settlements"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"))
    paid_by = Column(Integer, ForeignKey("users.id"))
    paid_to = Column(Integer, ForeignKey("users.id"))
    amount = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


