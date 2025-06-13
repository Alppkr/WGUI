from pydantic import BaseModel
from datetime import date

class AddItemData(BaseModel):
    data: str
    description: str | None = None
    date: date


class AddListData(BaseModel):
    name: str
    type: str
