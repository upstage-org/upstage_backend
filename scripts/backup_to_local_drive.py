import sys
from sqlalchemy import text
from src.global_config.helpers.fernet_crypto import encrypt
from src.global_config.env import DATABASE_HOST, DATABASE_NAME, DATABASE_PASSWORD, DATABASE_PORT, DATABASE_USER

from loguru import logger
import shutil
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# These should proabbaly be in the config variables.
dump_file = '/mnt/backups/pgdumpfile.sql'
asset_backup = '/mnt/backups/assets'

def backup_db_and_assets_to_local_disk():
    cmd = [
        'pg_dump',
        '-h', DATABASE_HOST,
        '-p', DATABASE_PORT,
        '-U', DATABASE_USER,
        '-v',  # Verbose output
        '--password', DATABASE_PASSWORD,
        DATABASE_NAME,
        ]

    logger.info(f"Starting pg_dump for database: {dDATABASE_NAME}")
    
    # Run pg_dump and write output to file
    with open(dump_file, 'w') as f:
        result = subprocess.run(
            cmd,
            stdout=f,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
               # Perform recursive copy

    shutil.copytree(
        '/app_code/uploads',
        asset_backup,
        dirs_exist_ok=overwrite,
        copy_function=shutil.copy2,
        )

if __name__ == "__main__":
    backup_db_and_assets_to_local_disk()
