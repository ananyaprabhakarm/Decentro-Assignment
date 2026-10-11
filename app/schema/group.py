from pydantic import BaseModel, field_validator

class GroupCreate(BaseModel):
    name: str

class GroupResponse(BaseModel):
    id: int
    name: str
    
    @field_validator("name")
    @classmethod
    def correct_name(cls, s:str) -> str:
       s = s.strip()
       if not s:
        raise ValueError("Name cannot be empty")
    
       return s.title()

