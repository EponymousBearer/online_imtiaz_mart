from fastapi import FastAPI, Depends, HTTPException
from inventory_service import settings
from sqlmodel import Field, Session, SQLModel, create_engine, select, Sequence
from contextlib import asynccontextmanager
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import asyncio
from datetime import datetime
from inventory_service.schemas import Inventory
from typing import List, Annotated, AsyncGenerator
from inventory_service import inventory_pb2
from inventory_service.schemas import Inventory

# connection_string = str(settings.DATABASE_URL).replace(
#     "postgresql", "postgresql+psycopg"
# )

# engine = create_engine(
#     connection_string, connect_args={}, pool_recycle=300
# )

# def create_db_and_tables()->None:
#     SQLModel.metadata.create_all(engine)
    
# async def get_kafka_producer():
#     producer = AIOKafkaProducer(bootstrap_servers='broker:19092')
#     await producer.start()
#     try:
#         yield producer
#     finally:
#         await producer.stop()
        
# @asynccontextmanager
# async def lifespan(app: FastAPI)-> AsyncGenerator[None, None]:
#     print("Creating tables..")
#     create_db_and_tables()
#     yield

# app = FastAPI(lifespan=lifespan,
#               title="Hello Kafka With FastAPI",
#               version="0.0.1",
#               root_path="/inventory-service",
#               root_path_in_servers=True
#               )

# def get_session():
#     with Session(engine) as session:
#         yield session

# @app.post("/inventories/", response_model=Inventory)
# async def create_inventory(
#     inventory: Inventory,
#     session: Annotated[Session, Depends(get_session)],
#     producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]
# ) -> Inventory:
#     session.add(inventory)
#     session.commit()
#     session.refresh(inventory)

#     # Convert to protobuf
#     inventory_protobuf = inventory_pb2.Inventory(
#         id=inventory.id,
#         product_id=inventory.product_id,
#         stock_level=inventory.stock_level,
#         last_updated=inventory.last_updated.isoformat()  # Convert datetime to ISO format string
#     )
#     serialized_inventory = inventory_protobuf.SerializeToString()
#     await producer.send_and_wait("InventoryCreated", serialized_inventory)

#     return inventory

# @app.get("/inventories/{product_id}", response_model=Inventory)
# async def read_inventory(product_id: int, session: Annotated[Session, Depends(get_session)]) -> Inventory:
#     product_inventory = session.get(Inventory, product_id)
#     if not product_inventory:
#         raise HTTPException(status_code=404, detail="Product Inventory not found")
#     return product_inventory

# @app.get("/inventories/", response_model=List[Inventory])
# async def read_inventories(session: Annotated[Session, Depends(get_session)]) -> List[Inventory]:
#     inventories = session.exec(select(Inventory)).all()
#     return inventories

# @app.put("/inventories/{product_id}", response_model=Inventory)
# async def update_inventory(
#     product_id: int,
#     updated_inventory: Inventory,
#     session: Annotated[Session, Depends(get_session)],
#     producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]
# ) -> Inventory:
#     statement = select(Inventory).where(Inventory.product_id == product_id)
#     inventory = session.exec(statement).first()
#     if not inventory:
#         raise HTTPException(status_code=404, detail="Inventory not found")

#     inventory.stock_level = updated_inventory.stock_level
#     inventory.last_updated = datetime.utcnow()

#     session.add(inventory)
#     session.commit()
#     session.refresh(inventory)

#     # Convert to protobuf
#     inventory_protobuf = inventory_pb2.InventoryUpdate(
#         product_id=product_id,
#         new_stock=inventory.stock_level,
#     )
#     serialized_inventory = inventory_protobuf.SerializeToString()
    
#     await producer.send_and_wait("InventoryUpdated", serialized_inventory)

#     return inventory

# @app.delete("/inventories/{product_id}", response_model=Inventory)
# async def delete_inventory(
#     product_id: int,
#     session: Annotated[Session, Depends(get_session)],
#     producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]
# ) -> Inventory:
#     statement = select(Inventory).where(Inventory.product_id == product_id)
#     inventory = session.exec(statement).first()
#     if not inventory:
#         raise HTTPException(status_code=404, detail="Inventory not found")

#     session.delete(inventory)
#     session.commit()

#     # Convert to protobuf
#     inventory_protobuf = inventory_pb2.Inventory(
#         id=inventory.id,
#         product_id=inventory.product_id,
#         stock_level=inventory.stock_level,
#         last_updated=inventory.last_updated.isoformat()  # Convert datetime to ISO format string
#     )
#     serialized_inventory = inventory_protobuf.SerializeToString()
#     await producer.send_and_wait("InventoryDeleted", serialized_inventory)

#     return inventory

@app.get("/")
async def root():
    return {"message": "Inventory Service is running..."}