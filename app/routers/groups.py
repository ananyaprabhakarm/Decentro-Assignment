from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database.database import get_db
from app.database.models import Group,  GroupMember
from app.schema.group import GroupCreate, GroupResponse
from app.schema.user import UserResponse

router = APIRouter(prefix='/group', tags=["groups"])

@router.post("/", response_model = list[GroupResponse])
def createGroup():


@router.get("/{group_id}", response_model = GroupResponse)
def retrieveGroup():


@router.get("/{group_id}/members/{user_id}", response_model = UserResponse)
def addUser():


@router.get("/{group_id}/members/{user_id}", response_model = UserResponse)
def deleteUser():
    
