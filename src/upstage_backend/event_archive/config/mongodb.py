# -*- coding: iso8859-15 -*-
import os
import sys

from upstage_backend.global_config.env import (
    EMAIL_TIME_EXPIRED_TOKEN,
    MONGO_EMAIL_DB,
    MONGO_EMAIL_HOST,
    MONGO_EMAIL_PORT,
    MONGODB_COLLECTION_TOKEN,
    MONGO_USER,
    MONGO_PASSWORD,
)
import pymongo


# Note: build_mongo_client (the former event_archive queue client targeting
# MONGO_HOST/MONGO_PORT/MONGO_DB) was removed along with the Mongo->Postgres
# worker pipeline. Event archive now writes directly to Postgres via async
# SQLAlchemy. The email-token helpers below are unrelated and still in use
# by mails/helpers/mail.py.


def build_mongo_email_client(
    host=MONGO_EMAIL_HOST,
    port=MONGO_EMAIL_PORT,
    username=MONGO_USER,
    password=MONGO_PASSWORD,
):
    uri = f"mongodb://{username}:{password}@{host}:{port}"
    return pymongo.MongoClient(uri)


def get_mongo_token_collection():
    client = build_mongo_email_client()
    mongo_db = client[MONGO_EMAIL_DB]
    collection = mongo_db[MONGODB_COLLECTION_TOKEN]
    if "expired_date" not in collection.index_information():
        collection.create_index(
            "expired_date",
            name="expired_date",
            expireAfterSeconds=EMAIL_TIME_EXPIRED_TOKEN,
        )
    return collection
