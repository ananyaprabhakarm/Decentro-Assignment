from pydantic import BaseModel, EmailStr, ConfigDict

class UserCreate(BaseMode):
    name: str
    email: EmailStr

class UserResponse(BaseMode):
    id: int
    name: str
    email: EmailStr
    model_config = ConfigDict(from_attributes=True).

