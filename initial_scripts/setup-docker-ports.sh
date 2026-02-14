#!/bin/bash
# Dynamic UFW rules for Docker container port access

# Get dynamic IPs
INTERNAL_IP=$(hostname -I | awk '{print $3}')
DOCKER_BRIDGE=$(docker network inspect bridge --format='{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null || echo "172.17.0.0/16")
UPSTAGE_NETWORK=$(docker network inspect upstage-network --format='{{range .IPAM.Config}}{{.Subnet}}{{end}}' 2>/dev/null || echo "172.18.0.0/16")

echo "Setting up UFW rules for:"
echo "Internal IP: $INTERNAL_IP"
echo "Docker Bridge: $DOCKER_BRIDGE" 
echo "Upstage Network: $UPSTAGE_NETWORK"

# PostgreSQL - Port 5433
ufw allow from $DOCKER_BRIDGE to 127.0.0.1 port 5433
ufw allow from $UPSTAGE_NETWORK to any port 5433
ufw allow from $DOCKER_BRIDGE to $INTERNAL_IP port 5433
ufw allow from $UPSTAGE_NETWORK to $INTERNAL_IP port 5433

# MongoDB - Port 27018  
ufw allow from $DOCKER_BRIDGE to 127.0.0.1 port 27018
ufw allow from $UPSTAGE_NETWORK to any port 27018
ufw allow from $DOCKER_BRIDGE to $INTERNAL_IP port 27018
ufw allow from $UPSTAGE_NETWORK to $INTERNAL_IP port 27018

# MQTT - Port 1884
ufw allow from $DOCKER_BRIDGE to 127.0.0.1 port 1884
ufw allow from $UPSTAGE_NETWORK to any port 1884
ufw allow from $DOCKER_BRIDGE to $INTERNAL_IP port 1884
ufw allow from $UPSTAGE_NETWORK to $INTERNAL_IP port 1884

echo "UFW rules setup complete!"
ufw reload
ufw status numbered