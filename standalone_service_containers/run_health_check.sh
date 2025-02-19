until docker exec standalone_service_container pg_isready -U postgres &>/dev/null; do
    echo "Waiting for PostgreSQL to be ready..."
    sleep 2
done

echo "PostgreSQL is ready!"

docker exec -d standalone_service_container mongod --config /etc/mongod.conf &

until curl -s localhost:27017 &>/dev/null; do
    echo "Waiting for MongoDB to be ready..."
    sleep 2
done

echo "MongoDB is ready!"

docker exec -d standalone_service_container mosquitto -c /etc/mosquitto/mosquitto.conf &

until nc -zv localhost 1883 &>/dev/null; do
    echo "Waiting for Mosquitto to be ready..."
    sleep 2
done

echo "Mosquitto is ready!"