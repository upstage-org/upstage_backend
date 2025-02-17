output_file="./src/global_config/load_env.py"
template_file="./configuration_scripts/environments/env_app_template.py"
pw_file="./configuration_scripts/mqtt_server/pw.txt"
docker_compose_file_1="./configuration_scripts/multiple-containers/docker-compose.yaml"  # This is the docker-compose file for the multiple containers
docker_compose_file_2="./configuration_scripts/single-container/docker-compose.yaml" # This is the docker-compose file for the single container

git stash

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
    keys=("POSTGRES_PASSWORD" "MQTT_PASSWORD" "EMAIL_HOST" "EMAIL_HOST_USER" "EMAIL_HOST_PASSWORD" "EMAIL_PORT" "STRIPE_KEY" "STRIPE_PRODUCT_ID")
    values=()

    # Generate POSTGRES_PASSWORD and MQTT_PASSWORD using openssl
    POSTGRES_PASSWORD=$(openssl rand -base64 12)
    MQTT_PASSWORD=$(openssl rand -base64 12)
    values+=("$POSTGRES_PASSWORD")
    values+=("$MQTT_PASSWORD")

    # Prompt user for the rest of the keys
    for key in "${keys[@]:2}"; do
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

    while IFS= read -r line; do
        for i in "${!keys[@]}"; do
            if [[ "$line" == *"{${keys[$i]}}"* ]]; then
                line="${line//\{${keys[$i]}\}/${values[$i]}}"
                break
            fi
        done
        echo "$line"
    done < "$pw_file" > "$pw_file.tmp" && mv "$pw_file.tmp" "$pw_file"


    for i in "${!keys[@]}"; do
        sed -i '' "s|\${${keys[$i]}}|${values[$i]}|g" "$docker_compose_file_1"
    done

     for i in "${!keys[@]}"; do
        sed -i '' "s|\${${keys[$i]}}|${values[$i]}|g" "$docker_compose_file_2"
    done
}

# Generate the configuration file
generate_config

echo "Configuration file generated at $output_file"




# Exit the script
exit 0