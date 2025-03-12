# -*- coding: iso8859-15 -*-
import os
import sys

appdir = os.path.abspath(os.path.dirname(__file__))
projdir = os.path.abspath(os.path.join(appdir, ".."))
projdir2 = os.path.abspath(os.path.join(appdir, "../.."))
if projdir not in sys.path:
    sys.path.append(appdir)
    sys.path.append(projdir)
    sys.path.append(projdir2)

from global_config import (
    EMAIL_TIME_EXPIRED_TOKEN,
    MONGO_EMAIL_DB,
    MONGO_EMAIL_HOST,
    MONGO_EMAIL_PORT,
    MONGO_HOST,
    MONGO_PORT,
    MONGODB_COLLECTION_TOKEN,
    MONGO_USER,
    MONGO_PASSWORD,
)
import pymongo


def build_mongo_client(
    host=MONGO_HOST, port=MONGO_PORT, username=MONGO_USER, password=MONGO_PASSWORD
):
    print(f"Connecting to MongoDB at {host}:{port}")
    uri = f"mongodb://{username}:{password}@{host}:{port}"
    print(f"URI: {uri}")
    return pymongo.MongoClient(uri)


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
