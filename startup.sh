#!/bin/sh
# Get the current date in the format DayOfWeek_Day_Month_Year
formatted_date=$(date +"%d_%m_%Y")

# Print the formatted date
echo "Formatted Date: $formatted_date"

old_file_path="src/global_config/config_formatted_date.py"
new_file_path="src/global_config/config_$formatted_date.py"

if [ ! -e "$new_file_path" ]; then
    cp "$old_file_path" "$new_file_path"
fi

# Export the timestamp as an environment variable
export TIMESTAMP=$formatted_date

alembic upgrade head
ruff format src
uvicorn src.main:app --proxy-headers --forwarded-allow-ips='*' --host 0.0.0.0 --port 3000 --reload