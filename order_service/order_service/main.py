from fastapi import FastAPI, Depends, HTTPException
from typing import List, Annotated
from order_service import settings
from sqlmodel import Field, Session, SQLModel, create_engine, select
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from order_service import order_pb2
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import asyncio
from order_service.schemas import Order, CartItemCreate, CartItem, CartItemUpdate
from datetime import datetime

connection_string = str(settings.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg"
)

engine = create_engine(
    connection_string, connect_args={}, pool_recycle=300
)

def create_db_and_tables()->None:
    SQLModel.metadata.create_all(engine)
    
async def get_kafka_producer():
    producer = AIOKafkaProducer(bootstrap_servers='broker:19092')
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()
        
@asynccontextmanager
async def lifespan(app: FastAPI)-> AsyncGenerator[None, None]:
    print("Creating tables..")
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan,
              title="Hello Kafka With FastAPI",
              version="0.0.1",
              root_path="/order-service",
              root_path_in_servers=True
              )

def get_session():
    with Session(engine) as session:
        yield session
        
@app.post("/cart/", response_model=CartItem)
async def add_to_cart(
    cart_item: CartItemCreate,
    session: Annotated[Session, Depends(get_session)],
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]
) -> CartItem:
    new_cart_item = CartItem(
        user_id=cart_item.user_id,
        product_id=cart_item.product_id,
        quantity=cart_item.quantity
    )
    session.add(new_cart_item)
    session.commit()
    session.refresh(new_cart_item)

    # Convert to protobuf
    cart_item_protobuf = order_pb2.CartItem(
        id=int(new_cart_item.id),  # Ensure id is an integer
        user_id=int(new_cart_item.user_id),  # Ensure user_id is an integer
        product_id=int(new_cart_item.product_id),  # Ensure product_id is an integer
        quantity=int(new_cart_item.quantity),  # Ensure quantity is an integer
        added_at=new_cart_item.added_at.isoformat(),
        updated_at=new_cart_item.updated_at.isoformat() if new_cart_item.updated_at else ""
    )
    serialized_cart_item = cart_item_protobuf.SerializeToString()
    await producer.send_and_wait("CartItemAdded", serialized_cart_item)

    return new_cart_item

@app.get("/cart/{user_id}", response_model=List[CartItem])
async def get_cart_items(
    user_id: int,
    session: Annotated[Session, Depends(get_session)]
) -> List[CartItem]:
    cart_items = session.exec(select(CartItem).where(CartItem.user_id == user_id)).all()
    return cart_items

@app.put("/cart/{cart_item_id}", response_model=CartItem)
async def update_cart_item(
    cart_item_id: int,
    cart_item_update: CartItemUpdate,
    session: Annotated[Session, Depends(get_session)],
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]
) -> CartItem:
    cart_item = session.get(CartItem, cart_item_id)
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    cart_item.quantity = cart_item_update.quantity
    cart_item.updated_at = datetime.utcnow()

    session.add(cart_item)
    session.commit()
    session.refresh(cart_item)

    # Convert to protobuf
    cart_item_protobuf = order_pb2.CartItem(
        id=int(cart_item.id),
        user_id=int(cart_item.user_id),
        product_id=int(cart_item.product_id),
        quantity=int(cart_item.quantity),
        added_at=cart_item.added_at.isoformat(),
        updated_at=cart_item.updated_at.isoformat() if cart_item.updated_at else ""
    )
    serialized_cart_item = cart_item_protobuf.SerializeToString()
    await producer.send_and_wait("CartItemUpdated", serialized_cart_item)

    return cart_item

@app.delete("/cart/{cart_item_id}", response_model=CartItem)
async def remove_from_cart(
    cart_item_id: int,
    session: Annotated[Session, Depends(get_session)],
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]
) -> CartItem:
    cart_item = session.get(CartItem, cart_item_id)
    if not cart_item:
        raise HTTPException(status_code=404, detail="Cart item not found")

    session.delete(cart_item)
    session.commit()

    # Convert to protobuf
    cart_item_protobuf = order_pb2.CartItem(
        id=int(cart_item.id),
        user_id=int(cart_item.user_id),
        product_id=int(cart_item.product_id),
        quantity=int(cart_item.quantity),
        added_at=cart_item.added_at.isoformat(),
        updated_at=cart_item.updated_at.isoformat() if cart_item.updated_at else ""
    )
    serialized_cart_item = cart_item_protobuf.SerializeToString()
    await producer.send_and_wait("CartItemRemoved", serialized_cart_item)

    return cart_item

@app.delete("/orders/{orderId}", response_model=Order)
async def cancel_order(orderId: int, session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]):
    statement = select(Order).where(Order.id == orderId)
    order = session.exec(statement).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    if order.status == "canceled":
        raise HTTPException(status_code=400, detail="Order is already canceled")

    order.status = "canceled"
    order.order_date = datetime.utcnow()
    session.add(order)
    session.commit()
    session.refresh(order)
    
    order_protobuf = order_pb2.Order(
        id=order.id,
        status=order.status,
        order_date=order.order_date.isoformat()  # Convert datetime to ISO format string
    )

    serialized_order = order_protobuf.SerializeToString()
    await producer.send_and_wait("OrderCanceled", serialized_order)

    return {"status": "canceled"}

@app.get("/orders/{orderId}/track", response_model=Order)
async def track_order(orderId: int, session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]):
    statement = select(Order).where(Order.id == orderId)
    order = session.exec(statement).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order_protobuf = order_pb2.Order(
        id=order.id,
        status=order.status,
    )

    serialized_order = order_protobuf.SerializeToString()
    await producer.send_and_wait("OrderTrack", serialized_order)
    
    return order

@app.get("/")
async def root():
    return {"message": "Order Service is running"}