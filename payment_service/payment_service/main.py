# from fastapi import FastAPI, Depends, HTTPException
# # from jose import jwt, JWTError
# # from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from typing import Annotated, List, Optional, AsyncGenerator
from payment_service import settings
from sqlmodel import Field, Session, SQLModel, create_engine, select, Sequence
from contextlib import asynccontextmanager
from payment_service import payment_pb2
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
import asyncio
import stripe
from fastapi import HTTPException, Request, FastAPI,Depends
from fastapi.responses import JSONResponse
from payment_service.schemas import PaymentRequest, Payment, PaymentCreate, PaymentStatus, PaymentRefund, Product,CartItem, PaymentReceipt
from datetime import datetime

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
        group_id="my-transaction-group",
        auto_offset_reset='earliest'
    )

    # Start the consumer.
    await consumer.start()
    try:
        # Continuously listen for messages.
        async for message in consumer:
            print(f"\n\n Consumer Raw message Vaue: {message.value}")

            new_transaction = payment_pb2.Transaction()
            new_transaction.ParseFromString(message.value)
            print(f"\n\n Consumer Deserialized data: {new_transaction}")
        # Here you can add code to process each message.
        # Example: parse the message, store it in a database, etc.
    finally:
        # Ensure to close the consumer when done.
        await consumer.stop()

def create_or_update_cart_item(cart_item):
    with Session(engine) as session:
        existing_cart_item = session.exec(
            select(CartItem).where(
                (CartItem.user_id == cart_item.user_id) &
                (CartItem.product_id == cart_item.product_id)
            )
        ).first()

        if existing_cart_item:
            existing_cart_item.quantity += cart_item.quantity
            existing_cart_item.updated_at = datetime.utcnow()
            session.add(existing_cart_item)
        else:
            new_cart_item = CartItem(
                user_id=cart_item.user_id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity
            )
            session.add(new_cart_item)
        session.commit()
  
async def consume_cart_products():
    consumer = AIOKafkaConsumer(
        'CartProducts',
        bootstrap_servers='broker:19092',
        group_id="cart-group",
        auto_offset_reset='earliest'
    )

    await consumer.start()
    try:
        async for message in consumer:
            cart_item = payment_pb2.CartItem()
            cart_item.ParseFromString(message.value)
            create_or_update_cart_item(cart_item)
    finally:
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
    asyncio.create_task(consume_messages('payment', 'broker:19092'))
    yield

app = FastAPI(lifespan=lifespan,
              title="Hello Kafka With FastAPI",
              version="0.0.1",
              root_path="/payment-service",
              root_path_in_servers=True
              )

def get_session():
    with Session(engine) as session:
        yield session

@app.get("/payment")
async def root():
    return {"message": "Payment Service is running"}

stripe.api_key = settings.STRIPE

def get_all_products(session: Session, product_ids: List[int]) -> List[Product]:
    statement = select(Product).where(Product.id.in_(product_ids))
    results = session.exec(statement)
    return results.all()

# @app.post("/payments", response_model=Payment)
# async def process_payment(
#     payment: PaymentCreate,
#     session: Annotated[Session, Depends(get_session)],
#     producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]
# ) -> Payment:
#     new_payment = Payment(
#         user_id=payment.user_id,
#         amount=payment.amount,
#         currency=payment.currency,
#         status="pending"  # Default status is pending
#     )
#     session.add(new_payment)
#     session.commit()
#     session.refresh(new_payment)

#     # Convert to protobuf
#     payment_protobuf = payment_pb2.Payment(
#         id=new_payment.id,
#         user_id=int(new_payment.user_id),
#         amount=new_payment.amount,
#         currency=new_payment.currency,
#         status=new_payment.status,
#         created_at=new_payment.created_at.isoformat(),
#         updated_at=new_payment.updated_at.isoformat() if new_payment.updated_at else ""
#     )
#     serialized_payment = payment_protobuf.SerializeToString()
#     await producer.send_and_wait("PaymentProcessed", serialized_payment)

#     return new_payment

@app.get("/payments/{payment_id}", response_model=Payment)
async def get_payment_status(
    payment_id: int,
    session: Annotated[Session, Depends(get_session)]
) -> Payment:
    payment = session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return payment

@app.post("/payments/{payment_id}/refund", response_model=Payment)
async def refund_payment(
    payment_id: int,
    refund: PaymentRefund,
    session: Annotated[Session, Depends(get_session)],
    producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]
) -> Payment:
    payment = session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if refund.amount > payment.amount:
        raise HTTPException(status_code=400, detail="Refund amount exceeds payment amount")

    payment.status = "refunded"
    payment.updated_at = datetime.utcnow()
    session.add(payment)
    session.commit()
    session.refresh(payment)

    # Convert to protobuf
    payment_protobuf = payment_pb2.Payment(
        id=payment.id,
        user_id=int(payment.user_id),
        amount=payment.amount,
        currency=payment.currency,
        status=payment.status,
        created_at=payment.created_at.isoformat(),
        updated_at=payment.updated_at.isoformat() if payment.updated_at else ""
    )
    serialized_payment = payment_protobuf.SerializeToString()
    await producer.send_and_wait("PaymentRefunded", serialized_payment)

    return payment

@app.get("/payments/history/{user_id}", response_model=List[Payment])
async def get_transaction_history(
    user_id: int,
    session: Annotated[Session, Depends(get_session)]
) -> List[Payment]:
    payments = session.exec(select(Payment).where(Payment.user_id == user_id)).all()
    return payments

@app.post("/create-checkout-session")
async def create_checkout_session(payment_request: PaymentRequest, session: Annotated[Session, Depends(get_session)],
                                  producer: Annotated[AIOKafkaProducer, Depends(get_kafka_producer)]):
    try:
        cart_items = session.exec(
            select(CartItem).where(CartItem.user_id == payment_request.user_id)
        ).all()

        if not cart_items:
            raise HTTPException(status_code=404, detail="Cart is empty")
        
        product_ids = [int(item.product_id) for item in cart_items]

        # Fetch product details for the products in the cart
        products = {product.id: product for product in get_all_products(session, product_ids)}

        total_amount = 0
        line_items = []
        
        for item in cart_items:
            product = products.get(item.product_id)
            
            if not product:
                raise HTTPException(status_code=404, detail=f"Product with ID {item.product_id} not found")

            total_amount += product.price * item.quantity

            # Add line item for each product
            line_items.append({
                'price_data': {
                    'currency': "usd",
                    'product_data': {
                        'name': product.name,
                    },
                    'unit_amount': int(product.price * 100),  # Convert to cents
                },
                'quantity': item.quantity,
            })

        if not line_items:
            raise HTTPException(status_code=404, detail="No valid products found")
        
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url="https://29de-223-123-110-15.ngrok-free.app/success",
            cancel_url="https://29de-223-123-110-15.ngrok-free.app/cancel",
        )
        
        new_payment = Payment(
            # checkout_id=checkout_session['id'],
            user_id=payment_request.user_id,
            amount=total_amount,
            currency="usd",
            status="pending"  # Default status is pending
        )
        
        session.add(new_payment)
        session.commit()
        session.refresh(new_payment)

        order_protobuf = payment_pb2.Order(
            user_id=str(payment_request.user_id),
            products=[payment_pb2.Product(product_id=str(item.product_id), quantity=item.quantity) for item in cart_items],
            status="packing",
            total_amount=total_amount,
            order_date=datetime.utcnow().isoformat()
        )

        # Serialize the order message
        serialized_order = order_protobuf.SerializeToString()

        # Send the message to the OrderCreated Kafka topic
        await producer.send_and_wait("OrderCreated", serialized_order)
        
        return {"sessionId": checkout_session['id'], "Payment": new_payment}
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    endpoint_secret = "whsec_Lr4jtb47ELzkfz8boJxclbtJvciFZ04o"

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        return JSONResponse(status_code=400, content={"message": "Invalid payload"})
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return JSONResponse(status_code=400, content={"message": "Invalid signature"})

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # Fulfill the purchase, e.g., update order status in your database

    return {"status": "success"}