import sys
from sqlalchemy import text
from src.global_config.helpers.fernet_crypto import encrypt
from src.global_config.env import DATABASE_HOST, DATABASE_NAME, DATABASE_PASSWORD, DATABASE_PORT, DATABASE_USER

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError



def update_upstage_user_passwords():
    """
    Updates all passwords in the 'upstage_user' table to the specified value.
    Adjust the query for hashed passwords if needed.
    """

    new_engine = create_engine(f"postgresql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}")

    new_password = input("Enter NEW PASSWORD (this password will be used for all user logins):").strip().replace(" ", "")
    update_sql = text("UPDATE upstage_user SET password = :new_password")

    with new_engine.connect() as conn:
        with conn.begin() as transaction:
            try:
                conn.execute(update_sql, {"new_password": encrypt(new_password)})
                logging.warning(f"All 'upstage_user' passwords have been updated to '{new_password}'.")
            except SQLAlchemyError as e:
                logging.warning(f"Error updating passwords in 'upstage_user': {e}", file=sys.stderr)

if __name__ == "__main__":
    update_upstage_user_passwords()
