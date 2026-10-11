from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database.database import get_db
from app.database.models import User
from app.schema.user import UserCreate, UserResponse

router = APIRouter(prefix='/users', tags=["Users"])

@router.get("/", response_model = list[UserResponse])
def get_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@router.get("/{user_id}", response_model = UserResponse)
def get_user(user_id: int,  db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
    


@router.post("/", response_model = UserResponse, status_code=201)
def create_user(create: UserCreate, db: Session = Depends(get_db)):
    try: 
        user_data = User(
            name = create.name,
            email = create.email
        )
        db.add(user_data)
        db.commit()
        db.refresh(user_data)
        return user_data
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Email already registered")

        
