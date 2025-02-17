This guide will help you set up and run the Upstage application using either Docker prebult images,
or using Dokcer form the source code.

It is recommended that you run three docker instances, preferably on three separate machines, with three separate subdomains. For example: streaming.myupstage.org, service.myupstage.org, app.myupstage.org

# Upstage Setup Guide: From Official Docker Images:
TBD

# Upstage Setup Guide: From Git Repo to Local Docker Images

## Setup OS

Install Docker, Nginx, and Certbot on all three machines.

### 1. Debian

```sh
./initial_scripts/setup-os.sh
```

This assumes you wish to use Let's Encrypt:
```sh
./initial_scripts/setup-your-domain.sh
```

This will auto-generate passwords for avrious applications, and store them in a local config file:
**************** Fill this in ***********************

## Prerequisites

- Docker
- Docker Compose

## Setup Instructions

### 1. Configure Environment Variables

To generate and update the environment variables, run the following command:

```sh
sh configuration_scripts/environments/generate_environments_script.sh
```

This script will create the necessary environment configuration files required for the application to run. Make sure to review and update any generated environment variables as needed.

### 2. Input Required Environment Variables

You will be prompted to enter the following environment variables. Please provide the necessary values when prompted:

```sh
Enter value for EMAIL_HOST: 
Enter value for EMAIL_HOST_USER: 
Enter value for EMAIL_HOST_PASSWORD: 
Enter value for EMAIL_PORT: 
Enter value for STRIPE_KEY: 
Enter value for STRIPE_PRODUCT_ID: 
```

Make sure to input accurate values for each prompt to ensure the application runs correctly.

### 2. Be sure to change these passwords and parameters before proceeding:

### 3. Start the Application

You can start the Upstage application using either a single container or multiple containers.

#### Single Container

To start the application using a single container, run the following command:

```sh
cd configuration_scripts/single-container
sh startup.sh
```

#### Multiple Containers

To start the application using multiple containers, use Docker Compose. First, ensure you have a `docker-compose.yml` file configured. Then, run the following command:

```sh
cd configuration_scripts multiple-containers
docker-compose up -d --build
```

This will start all the services defined in your `docker-compose.yml` file.

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

