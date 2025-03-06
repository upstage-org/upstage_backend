import sys
import json
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from src.global_config.helpers.fernet_crypto import encrypt

# Disable SQLAlchemy engine logging for less verbosity
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)

def get_new_table_columns(new_engine, table_name):
    """
    Return a list of column names for the specified table in the *new* database.
    """
    query = text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = :table
        ORDER BY ordinal_position
    """)
    with new_engine.connect() as conn:
        result = conn.execute(query, {"table": table_name})
        return [row[0] for row in result]

def clear_tables(new_engine, tables):
    """
    Clears all data from the specified tables in the new database
    using TRUNCATE TABLE with CASCADE.
    """
    with new_engine.connect() as conn:
        with conn.begin() as transaction:
            for table in tables:
                try:
                    conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                except SQLAlchemyError as e:
                    print(f"Error truncating table {table}: {e}", file=sys.stderr)
            transaction.commit()

def migrate_table(old_engine, new_engine, table_name):
    print(f"Migrating table '{table_name}'...")

    # Fetch the list of columns that exist in the new table.
    new_table_columns = get_new_table_columns(new_engine, table_name)
    if not new_table_columns:
        print(f"No columns found for table '{table_name}' in the new database. Skipping.")
        return

    # Fetch all rows from the old database table.
    with old_engine.connect() as old_conn:
        result = old_conn.execute(text(f"SELECT * FROM {table_name}"))
        rows = result.fetchall()
        if not rows:
            print(f"No data found in '{table_name}'. Skipping.")
            return

        # Only keep columns that exist in the new table.
        columns_list = new_table_columns
        columns_str = ", ".join(columns_list)
        placeholders = ", ".join([f":{col}" for col in columns_list])
        insert_sql = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
        insert_query = text(insert_sql)

    # Insert into the new database.
    with new_engine.connect() as new_conn:
        with new_conn.begin() as transaction:
            migrated_count = 0
            for row in rows:
                data = dict(row._mapping)

                # Build a dictionary of only the columns that exist in the new table.
                filtered_data = {}
                for key, value in data.items():
                    if key in new_table_columns:
                        if isinstance(value, (dict, list)):
                            filtered_data[key] = json.dumps(value)
                        else:
                            filtered_data[key] = value

                # If the new table has 'dormant' and it's not in old data, set it to False.
                if "dormant" in new_table_columns and "dormant" not in filtered_data:
                    filtered_data["dormant"] = False

                try:
                    with new_conn.begin_nested():
                        new_conn.execute(insert_query, filtered_data)
                    migrated_count += 1
                except SQLAlchemyError as e:
                    print(f"Error inserting row {filtered_data} into '{table_name}': {e}", file=sys.stderr)

            print(f"  Migrated {migrated_count} rows from '{table_name}'.")

def update_upstage_user_passwords(new_engine, new_password):
    """
    Updates all passwords in the 'upstage_user' table to the specified value.
    Adjust the query for hashed passwords if needed.
    """
    update_sql = text("UPDATE upstage_user SET password = :new_password")
    # For a hashed approach with pgcrypto (if your schema uses it), do something like:
    # update_sql = text("UPDATE upstage_user SET password = crypt(:new_password, gen_salt('bf'))")

    with new_engine.connect() as conn:
        with conn.begin() as transaction:
            try:
                conn.execute(update_sql, {"new_password": encrypt(new_password)})
                print(f"All 'upstage_user' passwords have been updated to '{new_password}'.")
            except SQLAlchemyError as e:
                print(f"Error updating passwords in 'upstage_user': {e}", file=sys.stderr)


def update_sequences(new_engine, tables):
    """
    Updates the sequence for each table in the list so that new rows have the correct IDs.
    Assumes that the sequence name follows the pattern: table_name_id_seq.
    """
    with new_engine.connect() as conn:
        with conn.begin() as transaction:
            for table in tables:
                seq_name = f"{table}_id_seq"
                update_seq_sql = text(f"SELECT setval(:seq_name, (SELECT COALESCE(MAX(id), 1) FROM {table}))")
                try:
                    conn.execute(update_seq_sql, {"seq_name": seq_name})
                    print(f"Updated sequence for table '{table}' using sequence '{seq_name}'.")
                except SQLAlchemyError as e:
                    print(f"Error updating sequence for table '{table}': {e}", file=sys.stderr)
            transaction.commit()


def main():
    old_db_url = input("Enter OLD DB connection string (e.g., user:password@host:port/db): ").strip().replace(" ", "")
    new_db_url = input("Enter NEW DB connection string (e.g., user:password@host:port/db): ").strip().replace(" ", "")
    new_password = input("Enter NEW PASSWORD: ").strip().replace(" ", "")

    old_engine = create_engine(f"postgresql://{old_db_url}")
    new_engine = create_engine(f"postgresql://{new_db_url}")

    # List the tables you want to migrate.
    tables_to_migrate = [
        "asset_type",
        "config",
        "jwt_no_list",
        "upstage_user",
        "admin_one_time_totp_qr_url",
        "asset", 
        "stage",
        "asset_usage",
        "scene",
        "user_session",
        "asset_license",
        "parent_stage",
        "performance",
        "stage_attribute",
        "events",
    ]
    
    # Clear all data in the specified tables in the new database.
    clear_tables(new_engine, tables_to_migrate)
    
    # Migrate each table.
    for table in tables_to_migrate:
        migrate_table(old_engine, new_engine, table)

    update_sequences(new_engine, tables_to_migrate)
    
    update_upstage_user_passwords(new_engine, new_password)

    print("Migration completed successfully.")

if __name__ == "__main__":
    main()
