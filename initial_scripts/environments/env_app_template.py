HOSTNAME="{APP_HOST}"

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
SECRET_KEY= "{REPLACE_FASTAPI_SECRET_KEY}"
CIPHER_KEY = b"{REPLACE_CIPHER_KEY}"


CLIENT_MAX_BODY_SIZE=500 * 1024 * 1024

UPLOAD_USER_CONTENT_FOLDER="/usr/app/uploads" # Mounted this way in docker-compose
DEMO_MEDIA_FOLDER="/usr/app/dashboard/demo"

# These settings are only for the upstage.live server. 
# payment
STRIPE_KEY = ""
STRIPE_PRODUCT_ID = ""

# This is the upstage.live host/hosts that will act as an email proxy 
# for servers specified below. 
ACCEPT_EMAIL_HOST = ["upstage.live"]
# These are the domain names of machines from which upstage.live will accept
# and send external email. We act as a mail proxy for approved clients.
ACCEPT_SERVER_SEND_EMAIL_EXTERNAL = []

SEND_EMAIL_SERVER = "https://upstage.live"

# Change to "Production" for official releases.
ENV_TYPE="Dev/Testing"

JWT_ACCESS_TOKEN_MINUTES = "86400" # 1 day
JWT_REFRESH_TOKEN_DAYS = "30" # 30 days
