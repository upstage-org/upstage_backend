# -*- coding: iso8859-15 -*-
import os
import sys

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)

import socket
from dotenv import load_dotenv

load_dotenv()
ENV_TYPE = os.getenv("ENV_TYPE")

DATABASE_CONNECT = os.getenv("DATABASE_CONNECT")
DATABASE_HOST = os.getenv("DATABASE_HOST")
DATABASE_PORT = os.getenv("DATABASE_PORT")
DATABASE_USER = os.getenv("DATABASE_USER")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
DATABASE_NAME = os.getenv("DATABASE_NAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_USER = os.getenv("MONGO_USER")

# payment
STRIPE_KEY = ""
STRIPE_PRODUCT_ID = ""


# MONGODB

EMAIL_TIME_EXPIRED_TOKEN = os.getenv("EMAIL_TIME_EXPIRED_TOKEN", 600)
MONGO_DB = os.getenv("MONGO_DB")
MONGO_HOST = os.getenv("MONGO_HOST")
MONGO_PORT = int(os.getenv("MONGO_PORT", "27017"))
MONGODB_COLLECTION_TOKEN = os.getenv("MONGODB_COLLECTION_TOKEN")
MONGO_EMAIL_DB = os.getenv("MONGO_EMAIL_DB")
MONGO_EMAIL_HOST = os.getenv("MONGO_EMAIL_HOST")
MONGO_EMAIL_PORT = int(os.getenv("MONGO_EMAIL_PORT", "27017"))

# JWT
SECRET_KEY = "Secret@123"
ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_MINUTES = os.getenv("JWT_ACCESS_TOKEN_MINUTES", "15")
JWT_REFRESH_TOKEN_DAYS = os.getenv("JWT_REFRESH_TOKEN_DAYS", "30")


# Apple
APPLE_ACCESS_TOKEN_CREATE = os.getenv("APPLE_ACCESS_TOKEN_CREATE")
APPLE_APP_ID = os.getenv("APPLE_APP_ID")
APPLE_APP_SECRET = os.getenv("APPLE_APP_SECRET")
APPLE_TEAM_ID = os.getenv("APPLE_TEAM_ID")

JWT_HEADER_NAME = "X-Access-Token"

CIPHER_KEY =  b"DDVf4r4bxTZYJSfYJDNDx2i5_Lhjo1L1uA_Ya20fIWc="
CLOUDFLARE_CAPTCHA_SECRETKEY = os.getenv("CLOUDFLARE_CAPTCHA_SECRETKEY")
CLOUDFLARE_CAPTCHA_VERIFY_ENDPOINT = os.getenv("CLOUDFLARE_CAPTCHA_VERIFY_ENDPOINT")


HOSTNAME = os.getenv("HOSTNAME")
ACCEPT_EMAIL_HOST = os.getenv("ACCEPT_EMAIL_HOST", "").split(",")
SEND_EMAIL_SERVER = os.getenv("SEND_EMAIL_SERVER", "http://localhost:8000")
FULL_DOMAIN = os.getenv("FULL_DOMAIN", "http://localhost:8000")
ACCEPT_SERVER_SEND_EMAIL_EXTERNAL = [
    "https://dev-app1.upstage.live"
]  # All client server endpoints. Only config on upstage server
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
SUPPORT_EMAILS = os.getenv("SUPPORT_EMAILS", "support@upstage.live").split(",")
EMAIL_HOST_DISPLAY_NAME = os.getenv("EMAIL_HOST_DISPLAY_NAME", "UpStage")
DOMAIN = os.getenv("DOMAIN", "upstage.live")

EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = True
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 465))
EMAIL_HOST_DISPLAY_NAME = os.getenv("EMAIL_HOST_DISPLAY_NAME", "UpStage")
EMAIL_TIME_TRIGGER_SECONDS = 60 * 1  # 1 minute
EMAIL_TIME_EXPIRED_TOKEN = 60 * 10
STREAM_EXPIRY_DAYS = 180
STREAM_KEY = os.getenv("STREAM_KEY", "")

MQTT_BROKER = os.getenv("MQTT_BROKER")
MQTT_ADMIN_PORT = int(os.getenv("MQTT_ADMIN_PORT", "1883"))
MQTT_TRANSPORT = "tcp"
MQTT_ADMIN_USER = os.getenv("MQTT_ADMIN_USER")
MQTT_ADMIN_PASSWORD = os.getenv("MQTT_ADMIN_PASSWORD")
PERFORMANCE_TOPIC_RULE = os.getenv("PERFORMANCE_TOPIC_RULE", "#")

EVENT_COLLECTION = os.getenv("EVENT_COLLECTION")

CLIENT_MAX_BODY_SIZE = os.getenv("CLIENT_MAX_BODY_SIZE", 0)

if "HARDCODED_HOSTNAME" in os.environ:
    ORIG_HOSTNAME = HOSTNAME = os.environ["HARDCODED_HOSTNAME"]
else:
    ORIG_HOSTNAME = socket.gethostname()
    HOSTNAME = socket.gethostname().replace(".", "_").replace("-", "_")

UPLOAD_USER_CONTENT_FOLDER = (
    "/usr/app/uploads"  # This is mounted here by docker-compose file.
)
DEMO_MEDIA_FOLDER = "./dashboard/demo"

UPSTAGE_FRONTEND_URL = os.getenv("UPSTAGE_FRONTEND_URL", "http://localhost:3000")
ENV_TYPE = os.getenv("ENV_TYPE", "development")
hstr = "from .load_env import *"

VIDEO_MAX_SIZE = 500 * 1024 * 1024  # KB
OTHER_MEDIA_MAX_SIZE = 500 * 1024 * 1024  # KB

exec(hstr)

DATABASE_URL = f"{DATABASE_CONNECT}://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
