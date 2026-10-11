from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database.database import get_db
from app.database.models import Group,  GroupMember, User
from app.schema.group import GroupCreate, GroupResponse
from app.schema.user import UserResponse

router = APIRouter(prefix='/group', tags=["groups"])

@router.post("/", response_model = GroupResponse)
def createGroup(create: GroupCreate, db: Session = Depends(get_db)):
    try:
        new_group = Group(
            name = create.name
        )
        db.add(new_group)
        db.commit()
        db.refresh(new_group)
        return new_group
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Group already exists")
  

@router.get("/{group_id}", response_model = GroupResponse)
def retrieveGroup(group_id: int, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return group

@router.get("/{group_id}/members/{user_id}", response_model = UserResponse)
def addUser(group_id: int, user_id: int, db: Session = Depends(get_db)):
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    existing_member = (
        db.query(GroupMember)
        .filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id
        )
        .first()
    )

    if existing_member:
        raise HTTPException(
            status_code=409,
            detail="User is already a member of this group"
        )

    try:
        membership = GroupMember(
            group_id=group_id,
            user_id=user_id
        )
        db.add(membership)
        db.commit()
        return user

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Could not add user to group"
        )


@router.get("/{group_id}/members/{user_id}", response_model = UserResponse)
def deleteUser(group_id: int, user_id: int, db: Session = Depends(get_db)):
    membership = (
        db.query(GroupMember)
        .filter(
            GroupMember.group_id == group_id,
            GroupMember.user_id == user_id
        )
        .first()
    )

    if not membership:
        raise HTTPException(
            status_code=404,
            detail="User is not a member of this group"
        )

    db.delete(membership)
    db.commit()

    return None
