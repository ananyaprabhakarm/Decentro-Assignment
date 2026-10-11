from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import session
from app.database.database import get_db
from app.database.models import User
from app.schema import user, group

router = APIRouter(prefix='/users')

@router.get("/")
def get_users():
    


@router.get("/{user_id}")
def get_user(user_id: int):
    


@router.post("/")
def create_user(name: str):
    