from fastapi import FastAPI, Depends, HTTPException
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from typing import Annotated, Optional
from user_service import settings
from datetime import datetime
from sqlmodel import Field, Session, SQLModel, create_engine, select, Sequence
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from passlib.context import CryptContext
from user_service import user_pb2
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import asyncio
from user_service.schema import User, InvalidToken

# CryptContext for password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

connection_string = str(settings.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg"
)

engine = create_engine(
    connection_string, connect_args={}, pool_recycle=300
)

def create_db_and_tables()->None:
    SQLModel.metadata.create_all(engine)
    
async def consume_messages(topic, bootstrap_servers):
    # Create a consumer instance.
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id="my-user-group",
        auto_offset_reset='earliest'
    )

    # Start the consumer.
    await consumer.start()
    try:
        # Continuously listen for messages.
        async for message in consumer:
            print(f"\n\n Consumer Raw message Vaue: {message.value}")

            new_todo = user_pb2.User()
            new_todo.ParseFromString(message.value)
            print(f"\n\n Consumer Deserialized data: {new_todo}")
                
        # Here you can add code to process each message.
        # Example: parse the message, store it in a database, etc.
    finally:
        # Ensure to close the consumer when done.
        await consumer.stop()


invalidated_tokens = set()

async def consume_invalidated_tokens(topic, bootstrap_servers):
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        group_id="invalidated-token-group",
        auto_offset_reset='earliest'
    )

    await consumer.start()
    try:
        async for message in consumer:
            token = message.value.decode("utf-8")
            invalidated_tokens.add(token)
    finally:
        await consumer.stop()

@asynccontextmanager
async def lifespan(app: FastAPI)-> AsyncGenerator[None, None]:
    print("Creating tables..")
    create_db_and_tables()
    # asyncio.create_task(consume_messages('user', 'broker:19092'))
    asyncio.create_task(consume_invalidated_tokens('InvalidatedTokens', 'broker:19092'))
    yield

app = FastAPI(lifespan=lifespan,
              title="Hello Kafka With FastAPI",
              version="0.0.1",
              root_path="/user-service",
              root_path_in_servers=True
              )

def get_session():
    with Session(engine) as session:
        yield session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    encode = {"sub": subject}
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    encode.update({"exp": expire})
    encoded_jwt = jwt.encode(encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_access_token(access_token: str):
    decoded_jwt = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    return decoded_jwt

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def get_kafka_producer():
    producer = AIOKafkaProducer(bootstrap_servers=settings.BOOTSTRAP_SERVER)
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()

def is_token_invalidated(token: str) -> bool:
    return token in invalidated_tokens

@app.post("/signup/", response_model=User)
async def signup(user: User, session: Annotated[Session, Depends(get_session)], producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)])->dict:
    existing_user = session.exec(select(User).where(User.email == user.email)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user_protbuf = user_pb2.User(id=user.id, username=user.username, email=user.email)
    print(f"Todo Protobuf: {user_protbuf}")
    # Serialize the message to a byte string
    serialized_todo = user_protbuf.SerializeToString()
    print(f"Serialized data: {serialized_todo}")
    # Produce message
    await producer.send_and_wait("SignupUser", serialized_todo)
    
    user.hashed_password = get_password_hash(user.hashed_password)
    session.add(user)
    session.commit()
    session.refresh(user)
    access_token = create_access_token(subject=user.username)
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@app.post("/login")
async def login_request(
    data_from_user: Annotated[OAuth2PasswordRequestForm, Depends(OAuth2PasswordRequestForm)],
    session: Annotated[Session, Depends(get_session)],
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]
):
    # Fetch user from database
    statement = select(User).where(User.username == data_from_user.username)
    user_in_db = session.exec(statement).first()

    if user_in_db is None:
        raise HTTPException(status_code=400, detail='Incorrect username')

    if not verify_password(data_from_user.password, user_in_db.hashed_password):
        raise HTTPException(status_code=400, detail='Incorrect password')

    access_token_expiry_minutes = timedelta(minutes=15)
    generated_token = create_access_token(subject=data_from_user.username, expires_delta=access_token_expiry_minutes)
    
    user_protbuf = user_pb2.User(
        id=user_in_db.id,
        username=user_in_db.username,
        email=user_in_db.email
    )
    print(f"Todo Protobuf Login: {user_protbuf}")
    # Serialize the message to a byte string
    serialized_todo = user_protbuf.SerializeToString()
    print(f"Serialized data Login: {serialized_todo}")
    # Produce message
    await producer.send_and_wait("LoginUser", serialized_todo)
    
    return {"access_token": generated_token, "token_type": "bearer"}

@app.get("/profile", response_model=User)
async def read_users_me(
    token: Annotated[str, Depends(oauth2_scheme)], 
    session: Annotated[Session, Depends(get_session)], 
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]
):
    # Check if the token is in the list of invalidated tokens
    if is_token_invalidated(token):
        raise HTTPException(status_code=401, detail="Token has been invalidated")

    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()
    if user is None:
        raise credentials_exception
    
    user_protbuf = user_pb2.User(
        id=user.id,
        username=user.username,
        email=user.email,
    )
    serialized_todo = user_protbuf.SerializeToString()
    await producer.send_and_wait("UserProfile", serialized_todo)
    
    return user

@app.post("/logout")
async def logout(
    token: Annotated[str, Depends(oauth2_scheme)], 
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]
):
    # Publish the invalidated token to Kafka
    await producer.send_and_wait("InvalidatedTokens", token.encode("utf-8"))
    return {"message": "Successfully logged out"}

@app.delete("/delete_user")
async def delete_user(
    token: Annotated[str, Depends(oauth2_scheme)], 
    session: Annotated[Session, Depends(get_session)],
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]
):
    payload = decode_access_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    statement = select(User).where(User.username == username)
    user = session.exec(statement).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    session.delete(user)
    session.commit()
    
    user_protbuf = user_pb2.User(
        id=user.id,
        username=user.username,
        email=user.email
    )
    serialized_todo = user_protbuf.SerializeToString()
    await producer.send_and_wait("DeleteUser", serialized_todo)

    return {"message": "User deleted successfully"}

@app.put("/update_user", response_model=User)
async def update_user(
    user: User, 
    token: Annotated[str, Depends(oauth2_scheme)], 
    session: Annotated[Session, Depends(get_session)],
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]
):
    payload = decode_access_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    statement = select(User).where(User.username == username)
    existing_user = session.exec(statement).first()
    if existing_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    existing_user.username = user.username or existing_user.username
    existing_user.email = user.email or existing_user.email
    if user.hashed_password:
        existing_user.hashed_password = get_password_hash(user.hashed_password)

    session.add(existing_user)
    session.commit()
    session.refresh(existing_user)
    
    user_protbuf = user_pb2.User(
        id=existing_user.id,
        username=existing_user.username,
        email=existing_user.email
    )
    serialized_todo = user_protbuf.SerializeToString()
    await producer.send_and_wait("UpdateUser", serialized_todo)

    return existing_user

@app.get("/user")
async def root():
    return {"message": "User Service containg sign up, login and profile"}

