from pydantic import BaseModel


class AllergenOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class AllergenCreate(BaseModel):
    name: str


class AllergenUpdate(BaseModel):
    name: str
