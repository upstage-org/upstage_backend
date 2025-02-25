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

## Insert Demo Data

To insert demo data into your application, you can use the provided `scaffold_base_media.sh` script

```sh
./initial_scripts/post_install/scaffold_base_media.sh
```

This script will insert the necessary demo data into your application. Make sure to verify that the data has been correctly inserted by checking the relevant sections of your application.