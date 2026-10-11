
from decimal import Decimal

from sqlalchemy.orm import Session

from app.database.models import Group, GroupMember, Settlement


def create_settlement(db: Session, group_id: int, paid_by: int, paid_to: int, amount: Decimal):
    # Check whether the group exists
    group = db.query(Group).filter(Group.id == group_id).first()

    if not group:
        raise ValueError("Group not found")

    # Check whether both users are active members of the group
    active_members = (
        db.query(GroupMember)
        .filter(
            GroupMember.group_id == group_id,
            GroupMember.is_active == True,
        )
        .all()
    )

    active_member_ids = {member.user_id for member in active_members}

    if paid_by not in active_member_ids:
        raise ValueError("Payer is not an active member of the group")

    if paid_to not in active_member_ids:
        raise ValueError("Receiver is not an active member of the group")

    if paid_by == paid_to:
        raise ValueError("Payer and receiver cannot be the same user")

    # Save the settlement
    settlement = Settlement(
        group_id=group_id,
        paid_by=paid_by,
        paid_to=paid_to,
        amount=amount,
    )

    try:
        db.add(settlement)
        db.commit()
        db.refresh(settlement)
        return settlement
    except Exception:
        db.rollback()
        raise
