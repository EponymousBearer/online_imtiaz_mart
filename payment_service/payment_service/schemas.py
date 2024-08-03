# from sqlmodel import SQLModel, Field
# from datetime import datetime
# from typing import Optional

# class Transaction(SQLModel, table=True):
#     id: Optional[int] = Field(default=None, primary_key=True)
#     user_id: str
#     amount: float
#     status: str
#     transaction_date: datetime = Field(default_factory=datetime.utcnow)
#     payment_method: str
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field
from pydantic import BaseModel

class PaymentRequest(BaseModel):
    product_id: int
    quantity: int
    currency: str = "usd"
    
class Payment(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: int
    amount: float
    currency: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class PaymentReceipt(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    checkout_id: str
    user_id: int
    total_amount: float
    currency: str
    status: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class PaymentRequest(BaseModel):
    user_id: int

class PaymentCreate(BaseModel):
    user_id: int
    total_amount: float
    currency: str

class PaymentStatus(BaseModel):
    status: str

class PaymentRefund(BaseModel):
    amount: float
    
class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str
    price: float
    stock: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
class CartItem(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    user_id: int
    product_id: int
    quantity: int
    added_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
