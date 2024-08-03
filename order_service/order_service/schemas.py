# schemas.py
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    product_id: int
    quantity: int
    status: str = Field(default="pending")
    order_date: datetime = Field(default_factory=datetime.utcnow)
    
class CartItem(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: int
    product_id: int
    quantity: int
    added_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class CartItemCreate(SQLModel):
    user_id: int
    product_id: int
    quantity: int

class CartItemUpdate(SQLModel):
    quantity: int