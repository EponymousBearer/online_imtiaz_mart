from starlette.config import Config
from starlette.datastructures import Secret

try:
    config = Config(".env")
except FileNotFoundError:
    config = Config()

DATABASE_URL = config("DATABASE_URL", cast=Secret)
BOOTSTRAP_SERVER = config("BOOTSTRAP_SERVER", cast=str)
KAFKA_ORDER_TOPIC = config("KAFKA_ORDER_TOPIC", cast=str)
KAFKA_CONSUMER_GROUP_ID_FOR_PRODUCT = config("KAFKA_CONSUMER_GROUP_ID_FOR_PRODUCT", cast=str)

TEST_DATABASE_URL = config("TEST_DATABASE_URL", cast=Secret)

ALGORITHM = "HS256"
SECRET_KEY = "A Secure Secret Key"

# smtp_server = config("smtp_server", cast=Secret)
# smtp_port = config(587, cast=str)
# smtp_username = config("smtp_username", cast=Secret)
# smtp_password = config("smtp_password", cast=Secret)

smtp_server = config("SMTP_SERVER")
smtp_port = config("SMTP_PORT", cast=int)
smtp_username = config("SMTP_USERNAME")
smtp_password = config("SMTP_PASSWORD")