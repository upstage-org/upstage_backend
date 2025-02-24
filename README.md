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

### 1. Spin up the three containers in your service machine:
```
cd service_containers
./run_docker_compose.sh
```

## Setup Instructions for your application machine: Upstage, Upstage Event Capture, Upstage Email (optional)

### 1. Spin up the three containers in your service machine:
```
cd app_containers
./run_docker_compose.sh
```

## Setup Instructions for inserting Seeding Data

### 3. Insert Seeding Data


### Default Admin User

Upon initial setup, a default administrator account is created with the following credentials:

- **Username:** `admin`
- **Password:** `Secret@123`

It is highly recommended to change the default password upon first login to ensure the security of your application. To change the password, follow these steps:

1. Log in to the application using the default credentials.
2. Navigate to the account settings or profile section.
3. Update the password to a strong, unique password.

Ensure that the new password meets the security requirements of your organization.
