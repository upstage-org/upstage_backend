This guide will help you set up and run the Upstage application using Docker from the source code.

It is recommended that you run three Debian docker machines/virtual machines with three separate subdomains. 

For example: streaming.myupstage.org, service.myupstage.org, app.myupstage.org

It is possible to install our front end, back end and streaming service all on one instance/machine, but it is not recommended. 

# Prerequisites:
### A working email address such as "support@your-domain" or "admins@your-domain", used for LetsEncrypt and Upstage admin emails:

Examples: support@your_upstage.org, admins@your_upstage.org

Wherever your email registry was purchased, in your email service provider dashboard (not part of this installation), it is recommended that you forward these emails to individuals who will approve account requests, receive LetsEncrypt emails, and be responsible for general Upstage administration. Sending outbound emails is handled from within an Upstage admin screen, and will use this same email account as a 'BCC' address. This is done for awareness of all outbound emails, and potential abuses of email become apparent very quickly in case that happens.

### A wildcard domain name and four 'A' DNS records, so that we can configure subdomains for each machine:

Example: mydomain.org (application), svc.mydomain.org (data and networking), streaming.mydomain.org and auth.streaming.mydomain.org (jitsi videobridge).

Be sure that you have a domain name registered with a DNS registrar like namecheap, gandi, etc.
Also ensure that in your DNS records: 

1: an 'A' record points to the IP address of your app server.
1: an 'A' record points to the IP address of your svc server.
1: Two 'A' records pointing to (a) the IP address of your streaming server, and (b) 'auth.' prefix pointing to the same IP of your streaming server as shown above. This is necessary even if users won't be logging into your jitsi streaming instance.

### Cloudflare Turnstyle Account (free).
This is used for captcha handling. Turning this off is not recommended, since bots already exist which try to flood Upstage with new user request attempts. We use the non-interactive, no-pre-clearance captcha configuration.

# Dependencies that are configured on your behalf, and should remain "hands-free": This is provided for your information only, and requires no action from you other than following the interactive installation instructions:

1. MQTT: mosquitto: Uses SSL for websocket connections only. TCP backend connections do not use SSL.
1. MQTT, MongoDB, Postgresql are all password protected. Passwords are auto-generated, and UFW rules ensure that remote access is only granted to the app server. 
1. All code, data and configuration exists on the physical/virtual machines in the '/' directory, and these corresponding directories are mounted into the individual instances as needed. This means that if a docker instance inside the physical/virtual fails for some reason, data will not be lost. 
1. Rerunning certain scripts will cause auto-generated passwords for DBs and such to be reset, and may cause data loss. See the [Restarting](#restarting-instances-in-case-of-problems) section for details on scripts which can be re-executed without harm. 
1. You may want to take snapshots of the above mentioned directories in each virtual/physical machine, or have them mounted from one shared, backed-up drive. See the [Restarting](#restarting-instances-in-case-of-problem) scripts to see how to stop and restart MongoDB and Postgresql for backups.

# Directories which contain all configuration and data (you may want to take snapshots of these):
### In app machine: configuration and all user static content uploads:
```
/app_code
alembic  demo  requirements.txt  scripts  src  uploads

/frontend_app
build  dist
```

### In svc machine: all databases and network/db utility configuration:
```
In / :
/mongodb_data_volume
/postgresql_data
/mosquitto_files
```

### In streaming machine: docker is not used here. Local jitsi videobridge installation/configuration happens via script:
```
In /etc/jitsi:
jicofo	meet  videobridge

In /etc/prosody:
README	certs  conf.avail  conf.d  migrator.cfg.lua  prosody.cfg.lua
```

# Restarting instances, in case of problems:

The following scripts will retain auto-generated passwords, and can be rerun safely at any time:

### App Instance:
The app instance can be restarted by running this script, which shuts down and restarts docker:
```
cd /root/upstage_backend/app_containers
./run_docker_compose.sh
```
This is a harmless script that runs docker compose to "bounce" the app instance. 
It can be re-executed at any time.

### Service Instance:
The svc instance can be restarted by running this script, which shuts down and restarts docker:
```
cd /root/upstage_backend/service_containers
./run_docker_compose.sh
```
This shell script can harmlessly be restarted at any time. 
It sets the Postgresql and MongoDB passwords used by docker-compose.
Inside the docker-compose file, you'll see how the Mosquitto password is reset upon restart, from a password backup file:
```
cat /mosquitto_files/etc/mosquitto/pw.backup 
performance:mmmmmmmmmmm
admin:nnnnnnnnnnnnn
```
### Streaming Instance:
Jitsi-videonbridge is installed directly in Debian. To restart it, run the following as root:
```
systemctl restart jicofo.service prosody.service jitsi-videobridge2.service nginx
```

### Rerunning Other Scripts:
Please note that rerunning setup-os.sh, setup-your-domain.sh, or any scripts other than the docker-compose scripts in the service machine, there is a risk of data loss. That being said, there should be no reason to have to rerun these scripts once things are running successfully.

# Handling Upgrades

### To keep your Upstage instance synchronized with our latest version, please contact us and we will help you with the upgrade, until such time that we have an automated upgrade process. If your version is older than 3.0.0, a fresh installation is required. Contact us for details regarding database and static content migration to our latest version.

# Upstage Setup Guide: From Git Repo to Local Docker Images

Run everything as root, preferably using ssh keys instead of login/password, for better security.

## Setup OS-level services in Debian: 

Spin up three of the latest Debian images in three separate instances.

We recommend doing this right after image spin-up of each image, to protect your instances:
```sh
apt install git ufw
ufw allow 22
ufw enable
```

Then git clone this repo and 'cd' into the topmost directory of that repo copy.

## On All Three Machines: Install Docker, Nginx, and Certbot:

```sh
./initial_scripts/setup-os.sh
```

## Specific to the Back End, Front End, or Streaming Service:
This uses LetsEncrypt and will also run the script to configure the service environment and set default passwords:
```sh
./initial_scripts/setup-your-domain.sh
```
If you don't wish to use LetsEncrypt, you can replace its keys with your own, and uninstall it after this entire installation process is complete. Note that nginx runs on each instance, managing the SSL layer on all instances. SSL is never handled or expected within docker instance configuration or code.

## On the Back End Server: Your Foundational Services Installed and Configured:
Choose option 1 to set up the Back End.

This will auto-generate passwords for various applications, and will store them in a local config file. It will also configure nginx for the specific type of machine you are setting up. Note that nginx, LetsEncrypt and ufw all run on the machine itself, not in the instances.

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
