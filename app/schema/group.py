from pydantic import BaseModel, ConfigDict, field_validator

class GroupCreate(BaseModel):
    name: str

    @field_validator("name")
    @classmethod
    def correct_name(cls, s:str) -> str:
        s = s.strip()
        if not s:
            raise ValueError("Name cannot be empty")
        return s.title() 
        

class GroupResponse(BaseModel):
    id: int
    name: str
    
    model_config = ConfigDict(from_attributes=True)

