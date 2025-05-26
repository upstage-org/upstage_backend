#!/bin/bash

# Running from the root dir...
#
output_file="./src/global_config/load_env.py"
template_file="./initial_scripts/environments/env_app_template.py"
pwd_template_file="./initial_scripts/environments/pwd_template.txt"
pw_file="./container_scripts/mqtt_server/pw.txt"
service_containers_template_file="./initial_scripts/environments/run_docker_compose_service_template.txt"
service_containers_file="./service_containers/run_docker_compose.sh" 

# Function to prompt user for input and replace placeholders
generate_config() {
    local key value
    keys=("REPLACE_FASTAPI_SECRET_KEY" "REPLACE_POSTGRES_PASSWORD" "REPLACE_MQTT_P_PASSWORD" "REPLACE_MQTT_A_PASSWORD" "REPLACE_MONGO_PASSWORD" "REPLACE_CLOUDFLARE_CAPTCHA_SECRETKEY" "EMAIL_HOST" "EMAIL_HOST_USER" "EMAIL_HOST_PASSWORD" "EMAIL_PORT")
    values=()

    # Generate POSTGRES_PASSWORD and MQTT_PASSWORD using openssl
    REPLACE_POSTGRES_PASSWORD=$(openssl rand -base64 9 | tr -dc 'A-Za-z0-9' | head -c 12)
    REPLACE_MQTT_P_PASSWORD=$(openssl rand -base64 9 | tr -dc 'A-Za-z0-9' | head -c 12)
    REPLACE_MQTT_A_PASSWORD=$(openssl rand -base64 9 | tr -dc 'A-Za-z0-9' | head -c 12)
    REPLACE_MONGO_PASSWORD=$(openssl rand -base64 9 | tr -dc 'A-Za-z0-9' | head -c 12)
    REPLACE_FASTAPI_SECRET_KEY= $(openssl rand -hex 48 )


    values+=("$REPLACE_FASTAPI_SECRET_KEY")
    values+=("$REPLACE_POSTGRES_PASSWORD")
    values+=("$REPLACE_MQTT_P_PASSWORD")
    values+=("$REPLACE_MQTT_A_PASSWORD")
    values+=("$REPLACE_MONGO_PASSWORD")

    # Prompt user for the rest of the keys
    echo "Enter the following values"
    for key in "${keys[@]:5}"; do
        read -p "Enter value for ${key}: " value
	if [[ "$key" =~ .*"PORT".* ]] && [[ -z "$value" ]]
	then 
            value=0
	fi
        values+=("$value")
    done

    a=`hostname -I`
    read -a arr <<< "$a"
    echo "
Note that on Digital Ocean, the third IP in the 'hostname -I' command: ${arr[2]} is the local network IP, used for faster connection without going out to the internet. That is the IP we're using. If this is incorrect in your environment, please change this IP address in the generated config file $output_file. All IPs for this server are: ${arr[@]}"
    SVC_HOST="${arr[2]}"
    keys+=("SVC_HOST")
    values+=("$SVC_HOST")

    # Clear the output file
    > "$output_file"

    # Replace placeholders with values in app config file.
    while IFS= read -r line; do
        for i in "${!keys[@]}"; do
            line="${line//\{${keys[$i]}\}/${values[$i]}}"
        done
        echo "$line" >> "$output_file"
    done < "$template_file"

    echo "
Configuration file generated at $output_file"

    # Replace placeholders in pwd_template.txt and copy to pw.txt
    > "$pw_file"
    while IFS= read -r line; do
        for i in "${!keys[@]}"; do
            line="${line//${keys[$i]}/${values[$i]}}"
        done
        echo "$line" >> "$pw_file"
    done < "$pwd_template_file"

    echo "
Passwords generated and saved to $pw_file"

    # Function to replace placeholders in docker compose service file.
    cp "$service_containers_template_file" "$service_containers_file"
    replace_placeholders() {
        local file=$1
        for i in "${!keys[@]}"; do
            sed -i "s|${keys[$i]}|${values[$i]}|g" "$file"
        done
    }
    replace_placeholders "$service_containers_file"
    echo "
Passwords generated and saved to $service_containers_file"
}

# Generate the configuration file
generate_config

echo "
If no errors have occurred, you are ready to set up the app server now. Just a heads-up: you will be instructed to copy-paste or transfer over the configuration file generated here: $output_file

"
