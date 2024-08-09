from starlette.config import Config
from starlette.datastructures import Secret

try:
    config = Config(".env")
except FileNotFoundError:
    config = Config()
DATABASE_URL="postgresql://ziakhan:my_password@postgres_db:5432/mydatabase"
TEST_DATABASE_URL="postgresql://ziaukhan:oSUELz91i@ep-polished-waterfall-a50jz332.us-east-2.aws.neon.tech/neondb?sslmode=require"

BOOTSTRAP_SERVER = "broker:19092"
KAFKA_ORDER_TOPIC = "inventory"
KAFKA_CONSUMER_GROUP_ID_FOR_PRODUCT = "consumer-group-id"
# DATABASE_URL = config("postgresql://ziakhan:my_password@postgres_db:5432/mydatabase", cast=Secret)
# BOOTSTRAP_SERVER = config("BOOTSTRAP_SERVER", cast=str)
# KAFKA_ORDER_TOPIC = config("KAFKA_ORDER_TOPIC", cast=str)
# KAFKA_CONSUMER_GROUP_ID_FOR_PRODUCT = config("KAFKA_CONSUMER_GROUP_ID_FOR_PRODUCT", cast=str)

# TEST_DATABASE_URL = config("TEST_DATABASE_URL", cast=Secret)

ALGORITHM = "HS256"
SECRET_KEY = "A Secure Secret Key"