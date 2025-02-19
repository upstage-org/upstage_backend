This guide will help you set up and run the Upstage application using either Docker prebult images,
or using Dokcer form the source code.

It is recommended that you run three docker instances, preferably on three separate machines, with three separate subdomains. For example: streaming.myupstage.org, service.myupstage.org, app.myupstage.org

We do provide scripts to run all containers on one machine, but it is not recommended.

# Upstage Setup Guide: From Official Docker Images:
TBD

# Upstage Setup Guide: From Git Repo to Local Docker Images

## Setup OS

Install Docker, Nginx, and Certbot on all three machines.

### 1. Debian

```sh
./initial_scripts/setup-os.sh
```

This assumes you wish to use Let's Encrypt and will also run the script to configure the service environment and set default passwords:
```sh
./initial_scripts/setup-your-domain.sh
```

This will auto-generate passwords for various applications, and store them in a local config file:
**************** Fill this in ***********************

## Prerequisites (installed above)

- Docker
- Docker Compose

## Setup Instructions for your service machine: Postgresql, Mongodb, Mosquitto

We provides two different ways to start services on your service machine. Here's a breakdown

### 1. Spin up the three containers in your service machine:
```
cd service_containers
./run_docker_compose.sh
```

### 2: Spin up the one container in your service machine:
```
cd standalone_service_containers
./run_docker_compose.sh
```

To check the health of the services, run the following command:

```sh
cd standalone_service_containers
./run_health_check.sh
```

## Setup Instructions for your application machine: Upstage, Upstage Event Capture, Upstage Email (optional)

### 1. Spin up the three containers in your service machine:
```
cd app_containers
./run_docker_compose.sh
```

## Setup Instructions for inserting Seeding Data

### 3. Insert Seeding Data

- Exec into the backend container:

```sh
docker exec -it {upstage_backend_container_id} bash
```

- Create initial accounts:

Change default accounts by editing the following file:

```sh
vi src/users/scripts/create_test_users.py
```

After updating the information in this file, run the script to create accounts:

```sh
python3 -m src.users.scripts.create_test_users
```

- Create default data:

```sh
python3 -m src.stages.scripts.scaffold-base-media
```

Input variables:
- `/usr/app/uploads`: This is the default directory for `UPLOAD_USER_CONTENT_FOLDER` in `env.py`. If you modify this path, ensure to update the corresponding path in the docker-compose file as well.
- `{administrator_username}`: This placeholder should be replaced with the username of the administrator account created in the previous steps.

