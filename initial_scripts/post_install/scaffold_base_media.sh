#!/bin/bash

set -a

echo "This script will insert scaffold base data into the database."
echo "It will perform the following steps:"
echo "1. Connect to the database."
echo "2. Create necessary tables if they do not exist."
echo "3. Insert predefined scaffold base data into the tables."
echo "Please ensure that the database connection parameters are correctly configured before running this script."

container=docker ps | grep upstage_container| awk '{print $1}'


docker exec -it $container "python3 -m src.stages.scripts.scaffold_base_media"