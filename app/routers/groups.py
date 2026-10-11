
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.database.models import Group, GroupMember, User
from app.schema.group import GroupCreate, GroupResponse
from app.schema.user import UserResponse

router = APIRouter(prefix="/group", tags=["groups"])


@router.get("/", response_model=list[GroupResponse])
def list_groups(db: Session = Depends(get_db)):
    return db.query(Group).order_by(Group.id).all()


@router.post(
    "/",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_group(
    create: GroupCreate,
    db: Session = Depends(get_db),
):
    group = Group(name=create.name.strip())

    if not group.name:
        raise HTTPException(
            status_code=422,
            detail="Group name cannot be empty",
        )

    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.get("/{group_id}", response_model=GroupResponse)
def retrieve_group(
    group_id: int,
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(Group.id == group_id).first()

    if group is None:
        raise HTTPException(404, "Group not found")

    return group


@router.post(
    "/{group_id}/members/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_user(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(Group.id == group_id).first()
    if group is None:
        raise HTTPException(404, "Group not found")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(404, "User not found")

    membership = (
        db.query(GroupMember)
        .filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
        )
        .first()
    )

    if membership:
        if membership.is_active:
            raise HTTPException(
                409, "User is already a member of this group"
            )

        # Reactivate an existing membership instead of
        # violating the unique group_id/user_id constraint.
        membership.is_active = True
        membership.joined_at = datetime.now(timezone.utc)
        membership.left_at = None
    else:
        membership = GroupMember(
            group_id=group_id,
            user_id=user_id,
            is_active=True,
        )
        db.add(membership)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return user


@router.get(
    "/{group_id}/members",
    response_model=list[UserResponse],
)
def list_group_members(
    group_id: int,
    db: Session = Depends(get_db),
):
    group = db.query(Group).filter(Group.id == group_id).first()
    if group is None:
        raise HTTPException(404, "Group not found")

    return (
        db.query(User)
        .join(GroupMember, GroupMember.user_id == User.id)
        .filter(
            GroupMember.group_id == group_id,
            GroupMember.is_active.is_(True),
        )
        .order_by(User.id)
        .all()
    )


@router.delete(
    "/{group_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_user(
    group_id: int,
    user_id: int,
    db: Session = Depends(get_db),
):
    membership = (
        db.query(GroupMember)
        .filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id,
            GroupMember.is_active.is_(True),
        )
        .first()
    )

    if membership is None:
        raise HTTPException(
            404, "Active group membership not found"
        )

    membership.is_active = False
    membership.left_at = datetime.now(timezone.utc)

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return None
