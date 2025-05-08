This guide will help you set up and run the Upstage application using Docker form the source code.

It is recommended that you run three Debian docker machines with three separate subdomains. 

For example: streaming.myupstage.org, service.myupstage.org, app.myupstage.org

It is possible to install our front end, back end and streaming service all on one instance/machine, but it is not recommended. 

Run everything as root, preferably using ssh keys instead of login/password, for better security.

# Upstage Setup Guide: From Official Docker Images:
TBD

# Upstage Setup Guide: From Git Repo to Local Docker Images

## Setup OS-level services in Debian: 

We recommend doing this right after image spin-up, to protect your instance:
```sh
apt install git ufw
ufw allow 22
ufw enable
```

Then git clone this repo.

## On All Three Machines: Install Docker, Nginx, and Certbot:

```sh
./initial_scripts/setup-os.sh
```

## Specific to the Back End, Front End, or Streaming Service:
This assumes you wish to use Let's Encrypt and will also run the script to configure the service environment and set default passwords:
```sh
./initial_scripts/setup-your-domain.sh
```

## On the Back End Server: Your Foundational Services Installed and Configured:
Choose option 1 to set up the Back End.

This will auto-generate passwords for various applications, and will store them in a local config file. It will also configure nginx for the specific type of machine you are setting up. Note that nginx, Let's Encrypt and ufw all run on the machine itself, not in the instances.

It will start three docker containers: MongoDB, Postgresql, Mosquitto.

## Setup Instructions for your Application Server: Upstage, Upstage Event Capture, Upstage Email (optional)

```sh
./initial_scripts/setup-your-domain.sh
```
Choose option 2 to set up the App server, which serves Upstage-specific Back End and Front End code.

This will configure and start three "app" containers: Upstage, Upstage-Event, Upstage-Stats. Note that  this script is interactive, and will prompt you to copy certain things.

## Setup Instructions for your Application Server also running the Front End:

The Front End code for Upstage runs on the same server as the application code, and comes from this repository:

```
https://github.com/upstage-org/upstage_frontend.git
```

After cloning the Front End code:

```sh
cd upstage_frontend
./initial_scripts/generate_environments_script.sh
./run_front_end.sh
```

Note that this script is also interactive. 

## Setup Instructions for Initializing Default Data

### Default Admin User, still on Application

Upon initial setup, a default administrator account is created with the following credentials:

- **Username:** `admin`
- **Password:** `Secret@123`

It is highly recommended to change the default password upon first login to ensure the security of your application. To change the password, follow these steps:

1. Log in to the application using the default credentials.
1. Navigate to the account settings or profile section.
1. Update the password to a strong, unique password.

Ensure that the new password meets the security requirements of your organization.

## Insert Demo Data

To insert demo data into your application, you can use the provided `scaffold_base_media.sh` script

```sh
./initial_scripts/post_install/scaffold_base_media.sh
```

This script will insert the necessary demo data into your application. Make sure to verify that the data has been correctly inserted by checking the relevant sections of your application.
