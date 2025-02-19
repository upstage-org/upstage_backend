output_file="./src/global_config/load_env.py"
template_file="./configuration_scripts/environments/env_app_template.py"
pw_file="./container_scripts/mqtt_server/pw.txt"
standalone_pw_file="./standalone_service_containers/mqtt_server/pw.txt"
service_containers_file="./service_containers/run_docker_compose.sh"  # This is the docker-compose file for the multiple containers
standalone_service_containers_file="./standalone_service_containers/run_docker_compose.sh"  # This is the docker-compose file for the standalone container

echo "$(dirname "$output_file")"

mkdir -p "$(dirname "$output_file")"

if [ ! -f "$output_file" ]; then
    touch "$output_file"
fi

# Clear the output file
> "$output_file"

# Function to prompt user for input and replace placeholders
generate_config() {
    local key value
    keys=("REPLACE_POSTGRES_PASSWORD" "REPLACE_MQTT_P_PASSWORD" "REPLACE_MQTT_A_PASSWORD" "REPLACE_MONGO_PASSWORD"  "SVC_HOST" "EMAIL_HOST" "EMAIL_HOST_USER" "EMAIL_HOST_PASSWORD" "EMAIL_PORT" "STRIPE_KEY" "STRIPE_PRODUCT_ID")
    values=()

    # Generate POSTGRES_PASSWORD and MQTT_PASSWORD using openssl
    REPLACE_POSTGRES_PASSWORD=$(openssl rand -base64 9 | tr -dc 'A-Za-z0-9' | head -c 12)
    REPLACE_MQTT_P_PASSWORD=$(openssl rand -base64 9 | tr -dc 'A-Za-z0-9' | head -c 12)
    REPLACE_MQTT_A_PASSWORD=$(openssl rand -base64 9 | tr -dc 'A-Za-z0-9' | head -c 12)
    REPLACE_MONGO_PASSWORD=$(openssl rand -base64 9 | tr -dc 'A-Za-z0-9' | head -c 12)
    values+=("$REPLACE_POSTGRES_PASSWORD")
    values+=("$REPLACE_MQTT_P_PASSWORD")
    values+=("$REPLACE_MQTT_A_PASSWORD")
    values+=("$REPLACE_MONGO_PASSWORD")

    # Prompt user for the rest of the keys
    echo "Enter the following values"
    for key in "${keys[@]:4}"; do
        read -p "Enter value for ${key}: " value
        values+=("$value")
    done

    # Replace placeholders with values
    while IFS= read -r line; do
        for i in "${!keys[@]}"; do
            line="${line//\{${keys[$i]}\}/${values[$i]}}"
        done
        echo "$line" >> "$output_file"
    done < "$template_file"

    echo "Configuration file generated at $output_file"

    # Function to replace placeholders in a given file
    replace_placeholders() {
        local file=$1
        for i in "${!keys[@]}"; do
            sed -i '' "s|${keys[$i]}|${values[$i]}|g" "$file"
        done
    }

    replace_placeholders "$pw_file"
    echo "Passwords generated and saved to $pw_file"

    replace_placeholders "$service_containers_file"
    echo "Passwords generated and saved to $service_containers_file"

    replace_placeholders "$standalone_pw_file"
    echo "Passwords generated and saved to $standalone_pw_file"

    replace_placeholders "$standalone_service_containers_file"
    echo "Passwords generated and saved to $standalone_service_containers_file"

}

# Generate the configuration file
generate_config

# Exit the script
exit 0
