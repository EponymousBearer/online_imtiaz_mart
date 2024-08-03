from fastapi import FastAPI, Depends, HTTPException
# from jose import jwt, JWTError
# from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from typing import Annotated, List, Optional
from product_service import settings
from sqlmodel import Field, Session, SQLModel, create_engine, select, Sequence
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from product_service import product_pb2
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import asyncio
from datetime import datetime
from product_service.schema import Product

connection_string = str(settings.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg"
)

engine = create_engine(
    connection_string, connect_args={}, pool_recycle=300
)

def create_db_and_tables()->None:
    SQLModel.metadata.create_all(engine)
 
def get_session():
    with Session(engine) as session:
        yield session
        
# async def update_product_stock(product_id: int, new_stock: int):
#         print("update_product_stock is running")
#         session = get_session()
#         print("session", session)
#         stmt = select(Product).where(Product.id == product_id)
#         product = session.execute(stmt)

#         if product:
#             # Update the product stock
#             product.stock = new_stock
#             print("updatedproduct", product)
#             session.add(product)
#             session.commit()
#             session.refresh(product)
#         else:
#             print(f"Product with ID {product_id} not found")
        
async def update_product_stock(product_id: int, new_stock: int):
    print("update_product_stock is running")
    with Session(engine) as session:
        stmt = select(Product).where(Product.id == product_id)
        result = session.exec(stmt)
        product = result.one_or_none()

        if product:
            # Update the product stock
            product.stock = new_stock
            print("updated product", product)
            session.add(product)
            session.commit()
            session.refresh(product)
        else:
            print(f"Product with ID {product_id} not found")
          
async def consume_messages(topic, bootstrap_servers):
    # Create a consumer instance.
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id="my-product-group",
        auto_offset_reset='earliest'
    )
    # session = get_session()
    # Start the consumer.
    await consumer.start()
    try:
        # Continuously listen for messages.
        async for message in consumer:
            print(f"\n\n Consumer Raw message Vaue: {message.value}")

            inventory_update = product_pb2.InventoryUpdate()
            inventory_update.ParseFromString(message.value)
            print(f"\n\nConsumer Deserialized data: {inventory_update}")
            print("inventory_update.product_id", inventory_update.new_stock)
            
            # Update the product stock in the database
            # await update_product_stock(product_id, new_stock)
            await update_product_stock(inventory_update.product_id, inventory_update.new_stock)
            
            # new_product = product_pb2.Product()
            # new_product.ParseFromString(message.value)
            # print(f"\n\n Consumer Deserialized data: {new_product}")
        # Here you can add code to process each message.
        # Example: parse the message, store it in a database, etc.
    finally:
        # Ensure to close the consumer when done.
        await consumer.stop()

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
    asyncio.create_task(consume_messages('InventoryUpdated', 'broker:19092'))
    yield

app = FastAPI(lifespan=lifespan,
              title="Hello Kafka With FastAPI",
              version="0.0.1",
              root_path="/product-service",
              root_path_in_servers=True
              )

@app.get("/")
async def root():
    return {"message": "Product Service is running"}

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')


# @app.put("/update_stock/{product_id}")
# async def update_stock(
#     product_id: int,
#     new_stock: int
# ):
#     await update_product_stock(product_id, new_stock)
#     return {"message": "Product stock updated successfully"}

@app.post("/create_product/", response_model=Product)
async def create_product(
    product: Product,
    session: Annotated[Session, Depends(get_session)],
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]
) -> dict:
    # Create Protobuf message
    product_protobuf = product_pb2.Product(
        id=product.id, name=product.name, description=product.description,
        price=product.price, stock=product.stock
    )
    serialized_product = product_protobuf.SerializeToString()
    await producer.send_and_wait("product", serialized_product)

    session.add(product)
    session.commit()
    session.refresh(product)
    return product

@app.get("/products/", response_model=List[Product])
async def read_products(session: Annotated[Session, Depends(get_session)]):
    products = session.exec(select(Product)).all()
    return products

@app.get("/products/{product_id}", response_model=Product)
async def read_product(product_id: int, session: Annotated[Session, Depends(get_session)]):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.put("/update_product/{product_id}", response_model=Product)
async def update_product(
    product_id: int,
    updated_product: Product,
    session: Annotated[Session, Depends(get_session)],
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]
):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    updated_product.id = product_id
    product_data = updated_product.dict(exclude_unset=True)
    for key, value in product_data.items():
        setattr(product, key, value)
    
    session.add(product)
    session.commit()
    session.refresh(product)

    # Create Protobuf message
    product_protobuf = product_pb2.Product(
        id=product.id, name=product.name, description=product.description,
        price=product.price, stock=product.stock
    )
    serialized_product = product_protobuf.SerializeToString()
    await producer.send_and_wait("product", serialized_product)

    return product

@app.delete("/delete_product/{product_id}", response_model=Product)
async def delete_product(
    product_id: int,
    session: Annotated[Session, Depends(get_session)],
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]
):
    product = session.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    session.delete(product)
    session.commit()

    # Create Protobuf message
    product_protobuf = product_pb2.Product(
        id=product.id, name=product.name, description=product.description,
        price=product.price, stock=product.stock
    )
    serialized_product = product_protobuf.SerializeToString()
    await producer.send_and_wait("product", serialized_product)

    return product

@app.get("/products/search/", response_model=List[Product])
async def search_products(
    session: Annotated[Session, Depends(get_session)],
    name: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
) -> List[Product]:
    statement = select(Product)
    
    if name:
        statement = statement.where(Product.name.contains(name))
    if min_price:
        statement = statement.where(Product.price >= min_price)
    if max_price:
        statement = statement.where(Product.price <= max_price)
    
    products = session.exec(statement).all()
    return products


