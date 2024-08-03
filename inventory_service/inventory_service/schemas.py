from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class Inventory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int
    stock_level: int
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    
