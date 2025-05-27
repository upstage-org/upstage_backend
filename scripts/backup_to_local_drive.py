import os
import sys
sys.path.append('/usr/app/src')

from sqlalchemy import text
from src.global_config.helpers.fernet_crypto import encrypt
from src.global_config.env import DATABASE_HOST, DATABASE_NAME, DATABASE_PASSWORD, DATABASE_PORT, DATABASE_USER

import arrow
import glob
from loguru import logger
import shutil
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import subprocess
import time

# These locations inside the docker file are consistent.
ts = int(arrow.utcnow().timestamp())
dump_file = f'/mnt/backups/pgdumpfile_{ts}.sql'
asset_backup = '/mnt/backups/assets'

def backup_db_and_assets_to_local_disk():
    while True:
        cmd = f'PGPASSWORD={DATABASE_PASSWORD} /usr/bin/pg_dump -h {DATABASE_HOST} -p {DATABASE_PORT} -U {DATABASE_USER} -w --dbname {DATABASE_NAME}'

        ts = int(arrow.utcnow().timestamp())
        dump_file = f'/mnt/backups/pgdumpfile_{ts}.sql'
        with open(dump_file, "w") as file:
            process = subprocess.Popen(
                cmd,
                stdout=file,
                stderr=subprocess.PIPE,
                shell=True
                )
         
            process.wait()

        cmd = f'gzip {dump_file}'

        process = subprocess.Popen(
            cmd,
            stderr=subprocess.PIPE,
            shell=True
            )
        process.wait()
        files = glob.glob(os.path.join('/mnt/backups', '*.sql.gz'))

        old_ts = int(arrow.utcnow().shift(days= -3).timestamp())
        for file in files:
            file_ts = int(file.split('_')[1].split('.sql.gz')[0])
            if file_ts < old_ts:
                os.remove(file)

        logger.info(f"Backed up the database: {DATABASE_NAME}")
    
        shutil.copytree(
            '/usr/app/uploads',
            asset_backup,
            dirs_exist_ok=True,
            copy_function=shutil.copy2,
            )

        logger.info(f"Backed up assets")

        time.sleep(3600)

if __name__ == "__main__":
    backup_db_and_assets_to_local_disk()
