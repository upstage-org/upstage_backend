This guide will help you set up and run the Upstage application using either Docker prebult images,
or using Dokcer form the source code.

It is recommended that you run three docker instances, preferably on three separate machines, with three separate subdomains. For example: streaming.myupstage.org, service.myupstage.org, app.myupstage.org

We do provide scripts to run all containers on one machine, but it is not recommended.

# Upstage Setup Guide: From Official Docker Images:
TBD

# Upstage Setup Guide: From Git Repo to Local Docker Images

## Setup OS-level services in Debian: 
Run everything as root.

Run ``` apt install git ```

Then git clone this repo.

### Install Docker, Nginx, and Certbot on all three machines:

```sh
./initial_scripts/setup-os.sh
```

This assumes you wish to use Let's Encrypt and will also run the script to configure the service environment and set default passwords:
```sh
./initial_scripts/setup-your-domain.sh
```
Choose option 1

This will auto-generate passwords for various applications, and will store them in a local config file.

It will also start three docker containers, one for MongoDB, one for Postgresql, one for Mosquitto.

## Setup Instructions for your application machine: Upstage, Upstage Event Capture, Upstage Email (optional)

```sh
./initial_scripts/setup-your-domain.sh
```
Choose option 2

This will start three "app" containers: Upstage, Upstage-Event, Upstage-Email

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

- Exec into the backend container:

```sh
docker exec -it {upstage_backend_container_id} bash
```
- Create default data:

```sh
python3 -m src.stages.scripts.scaffold-base-media
```

Input variables:
- `/usr/app/uploads`: This is the default directory for `UPLOAD_USER_CONTENT_FOLDER` in `env.py`. If you modify this path, ensure to update the corresponding path in the docker-compose file as well.
- `{administrator_username}`: This placeholder should be replaced with the username of the administrator account created in the previous steps.

