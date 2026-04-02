from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class Task(BaseModel):
    id: Optional[int] = None
    title: str
    description: str = ""
    completed: bool = False
    created_at: Optional[datetime] = None


class TaskCreate(BaseModel):
    title: str
    description: str = ""
