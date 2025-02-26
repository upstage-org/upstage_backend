DATABASE_CONNECT = "postgresql"
DATABASE_HOST = "{SVC_HOST}"
DATABASE_PORT = 5433
DATABASE_USER = "postgres"
DATABASE_PASSWORD = "{REPLACE_POSTGRES_PASSWORD}"
DATABASE_NAME = "upstage"

MONGO_DB = "upstage"
MONGO_HOST = "{SVC_HOST}"
MONGO_PORT = 27018
MONGO_USER = "admin"
MONGO_PASSWORD = "{REPLACE_MONGO_PASSWORD}"
EVENT_COLLECTION = "events"
MONGODB_COLLECTION_TOKEN = "token"
MONGO_EMAIL_DB = "email"
MONGO_EMAIL_HOST = "{SVC_HOST}"
MONGO_EMAIL_PORT = 27018
MONGO_EMAIL_PASSWORD = "{REPLACE_MONGO_PASSWORD}"
MONGO_USER = "admin"

EMAIL_USE_TLS = True
EMAIL_HOST = "{EMAIL_HOST}"
EMAIL_HOST_USER = "{EMAIL_HOST_USER}"
EMAIL_HOST_PASSWORD = "{EMAIL_HOST_PASSWORD}"
EMAIL_PORT = int("{EMAIL_PORT}")
EMAIL_HOST_DISPLAY_NAME = "UpStage Support"
MQTT_BROKER = "{SVC_HOST}"
MQTT_TRANSPORT = "tcp"
MQTT_ADMIN_USER = "admin"
MQTT_ADMIN_PASSWORD = "{REPLACE_MQTT_A_PASSWORD}"
MQTT_ADMIN_PORT = 1884
MQTT_USER = "performance"
MQTT_PASSWORD = "{REPLACE_MQTT_P_PASSWORD}"
MQTT_PORT = 9002

CLOUDFLARE_CAPTCHA_SECRETKEY = "{REPLACE_CLOUDFLARE_CAPTCHA_SECRETKEY}"
CLOUDFLARE_CAPTCHA_VERIFY_ENDPOINT = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

CLIENT_MAX_BODY_SIZE=300 * 1024 * 1024

UPLOAD_USER_CONTENT_FOLDER="./uploads"
DEMO_MEDIA_FOLDER="./dashboard/demo"

# payment
STRIPE_KEY = ""
STRIPE_PRODUCT_ID = ""

SEND_EMAIL_SERVER = "https://upstage.live"