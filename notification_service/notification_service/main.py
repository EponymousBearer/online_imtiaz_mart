from fastapi import FastAPI, Depends, HTTPException
from typing import Annotated, List, Optional
from notification_service import settings
from sqlmodel import Field, Session, SQLModel, create_engine, select, Sequence
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from notification_service import notification_pb2
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import asyncio
from datetime import datetime
from notification_service.schemas import Notification,EmailSchema,SmsSchema,User

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import smtplib  # For sending email
import requests  # For sending SMS

connection_string = str(settings.DATABASE_URL).replace(
    "postgresql", "postgresql+psycopg"
)

engine = create_engine(
    connection_string, connect_args={}, pool_recycle=300
)

def create_db_and_tables()->None:
    SQLModel.metadata.create_all(engine)
      
async def get_kafka_consumer(topic, bootstrap_servers, group_id) -> AsyncGenerator[AIOKafkaConsumer, None]:
    consumer = AIOKafkaConsumer(topic, bootstrap_servers=bootstrap_servers, group_id=group_id)
    await consumer.start()
    try:
        yield consumer
    finally:
        await consumer.stop()

async def get_kafka_producer():
    producer = AIOKafkaProducer(bootstrap_servers='broker:19092')
    await producer.start()
    try:
        yield producer
    finally:
        await producer.stop()
 
def send_email(to_email: str, subject: str, message: str):
    smtp_server = settings.smtp_server
    smtp_port = settings.smtp_port
    smtp_username = settings.smtp_username
    smtp_password = settings.smtp_password
    
    from_email = smtp_username

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(message, "plain"))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False
 
def send_sms(to_phone_number: str, carrier_domain: str, message: str):
    smtp_server = settings.smtp_server
    smtp_port = settings.smtp_port
    smtp_username = settings.smtp_username
    smtp_password = settings.smtp_password

    from_email = smtp_username
    to_email = f"{to_phone_number}@{carrier_domain}"

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = "SMS Message"

    msg.attach(MIMEText(message, "plain"))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"Failed to send SMS: {e}")
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

async def consume_order_created():
    async for consumer in get_kafka_consumer('OrderCreated', 'broker:19092', "my-notification-group"):
        async for message in consumer:
            print(f"Received message: {message.value}")
            new_notification = notification_pb2.Notification()
            new_notification.ParseFromString(message.value)
            print(f"Parsed notification: {new_notification}")
            user_id = new_notification.user_id
            with Session(engine) as session:
                user = session.get(User, user_id)
                if not user:
                    print(f"User {user_id} not found")
                    continue

                send_email(user.email, "Order Created Notification", 'message_content')
                
                # if user.phone_number and user.carrier_domain:
                #     print(f"Sending SMS notification to user {user_id} at {user.phone_number}@{user.carrier_domain}...")
                #     send_sms(user.phone_number, user.carrier_domain, "message_content")
                # else:
                #     print(f"User {user_id} does not have valid phone number or carrier domain")

async def consume_order_cancel():
    async for consumer in get_kafka_consumer('OrderCanceled', 'broker:19092', "my-notification-group"):
        async for message in consumer:
            print(f"Received message: {message.value}")
            new_notification = notification_pb2.Notification()
            new_notification.ParseFromString(message.value)
            print(f"Parsed notification: {new_notification}")
            user_id = new_notification.user_id
            with Session(engine) as session:
                
                user = session.get(User, user_id)
                if not user:
                    print(f"User {user_id} not found")
                    continue

                # Send notification
                # if notification_type == "email":
                print(f"Sending email notification to user {user_id} at {user.email}...")
                send_email(user.email, "Order Cancel Notification", 'Order Canceled ${new_notification}')
                # elif notification_type == "sms":
                #     if user.phone_number and user.carrier_domain:
                #         print(f"Sending SMS notification to user {user_id} at {user.phone_number}@{user.carrier_domain}...")
                #         send_sms(user.phone_number, user.carrier_domain, message_content)
                #     else:
                #         print(f"User {user_id} does not have valid phone number or carrier domain")
                
async def consume_order_update():
    async for consumer in get_kafka_consumer('OrderUpdated', 'broker:19092', "my-notification-group"):
        async for message in consumer:
            print(f"Received message: {message.value}")
            new_notification = notification_pb2.Notification()
            new_notification.ParseFromString(message.value)
            print(f"Parsed notification: {new_notification}")
            user_id = new_notification.user_id
            with Session(engine) as session:

                user = session.get(User, user_id)
                if not user:
                    print(f"User {user_id} not found")
                    continue

                # Send notification
                # if notification_type == "email":
                print(f"Sending email notification to user {user_id} at {user.email}...")
                send_email(user.email, "Order Updated Notification", 'message_content ${new_notification}')
                # elif notification_type == "sms":
                #     if user.phone_number and user.carrier_domain:
                #         print(f"Sending SMS notification to user {user_id} at {user.phone_number}@{user.carrier_domain}...")
                #         send_sms(user.phone_number, user.carrier_domain, message_content)
                #     else:
                #         print(f"User {user_id} does not have valid phone number or carrier domain")
                   
@asynccontextmanager
async def lifespan(app: FastAPI)-> AsyncGenerator[None, None]:
    print("Creating tables..")
    create_db_and_tables()
    # asyncio.create_task(consume_messages('notification', 'broker:19092'))
    asyncio.create_task(consume_order_created())
    asyncio.create_task(consume_order_update())
    asyncio.create_task(consume_order_cancel())
    yield

app = FastAPI(lifespan=lifespan,
              title="Hello Kafka With FastAPI",
              version="0.0.1",
              root_path="/notification-service",
              root_path_in_servers=True
              )

def get_session():
    with Session(engine) as session:
        yield session

# oauth2_scheme = OAuth2PasswordBearer(tokenUrl='login')

# @app.post("/send-email/")
# def send_email_endpoint(email: EmailSchema):
#     if send_email(email.email, email.subject, email.message):
#         return {"message": "Email sent successfully"}
#     else:
#         raise HTTPException(status_code=500, detail="Failed to send email")

# @app.post("/send-sms/")
# def send_sms_endpoint(sms: SmsSchema):
#     if send_sms(sms.phone_number, sms.carrier_domain, sms.message):
#         return {"message": "SMS sent successfully"}
#     else:
#         raise HTTPException(status_code=500, detail="Failed to send SMS")

@app.get("/")
async def root():
    return {"message": "Notification Service is running"}