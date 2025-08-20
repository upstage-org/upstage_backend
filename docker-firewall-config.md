# Installation Guide - Complete Backend Setup

## Docker Container Port Access Configuration

**Note:** There's some trickiness to running all images on the same machine. Follow these steps carefully:

### 1. UFW Localhost Rules (Essential for same machine)

To allow a machine to make outgoing connections to its own IP address using UFW, you must create rules in the `/etc/ufw/before.rules` file.

```bash
# Edit UFW before rules
sudo nano /etc/ufw/before.rules

# Add these lines before the COMMIT line:
-A ufw-before-input -i lo -j ACCEPT
-A ufw-before-output -o lo -d 127.0.0.1 -j ACCEPT

# Restart UFW
ufw disable && ufw enable
```

### 2. Dynamic Docker Network Port Access Setup

Run the script to automatically configure UFW rules for Docker container access:

```bash
chmod +x initial_scripts/setup-docker-ports.sh
./initial_scripts/setup-docker-ports.sh
```

### 3. Service Configuration Requirements

#### PostgreSQL Configuration

Be sure to pass this parameter in the postgresql docker image to ensure it listens on all interfaces:

```yaml
command: >
  postgres -c listen_addresses='*'
```

#### Restart Service Containers

After applying the firewall configuration and updating service settings, restart the service containers so they pick up the new bindings and network rules:

```bash
cd service_containers
./run_docker_compose.sh
```

## Streaming Server Support

We also support a streaming server, used for chat. Follow the same network configuration as above.

## Verification

After setup, verify that containers can access the services:

```bash
# Test from containers
docker exec -it container_name nc -zv $INTERNAL_IP 5433   # PostgreSQL
docker exec -it container_name nc -zv $INTERNAL_IP 27018  # MongoDB
docker exec -it container_name nc -zv $INTERNAL_IP 1884   # MQTT

# Check UFW status
ufw status numbered
```

## Expected UFW Rules Structure

After running the setup, your UFW rules should look similar to:

```
To                         Action      From
--                         ------      ----
22                         ALLOW       Anywhere
127.0.0.1 5433             ALLOW       172.17.0.0/16
127.0.0.1 27018            ALLOW       172.17.0.0/16
127.0.0.1 1884             ALLOW       172.17.0.0/16
5433                       ALLOW       172.18.0.0/16
27018                      ALLOW       172.18.0.0/16
1884                       ALLOW       172.18.0.0/16
5433/tcp                   ALLOW       [INTERNAL_IP]
27018/tcp                  ALLOW       [INTERNAL_IP]
1884                       ALLOW       [INTERNAL_IP]
```

## Troubleshooting

If containers cannot connect to services:

1. Check Docker network IPs: `docker network ls` and `docker network inspect <network_name>`
2. Verify UFW rules: `ufw status numbered`
3. Test connectivity: `docker exec -it container nc -zv <target_ip> <port>`
4. Check service binding: Services must bind to `0.0.0.0` or `*`, not just `127.0.0.1`
