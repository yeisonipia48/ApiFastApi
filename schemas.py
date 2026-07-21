from pydantic import BaseModel, ConfigDict

class Usuarios(BaseModel):
    id: int
    name: str
    cedula: str

    model_config=ConfigDict(from_attributes=True)

class UserCreate(BaseModel):
    name: str
    cedula: str

class UserUpdate(BaseModel):
    name:str | None = None
    cedula:str | None = None