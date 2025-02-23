# #!/bin/bash
# Install and setup the OS
sudo apt update
sudo apt upgrade

apt install ufw
ufw allow ssh
ufw enable

# Add Docker's official GPG key and other tools:
sudo apt install ca-certificates curl logrotate

cp initial_scripts/logrotate_for_docker.commands /etc/logrotate.d/docker
logrotate -d /etc/logrotate.d/docker

sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update

$(. /etc/os-release && echo "$VERSION_CODENAME")

for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do sudo apt-get remove ; done
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo docker run hello-world

sudo ufw status

echo "
Before proceeding to the next script, be sure that you have a domain name registered with a DNS registrar like namecheap, gandi, etc.
Also ensure that in your DNS records, an 'A' record points to the IP address of your app server, not your svc server.

Your 'svc dot domain_name' server will run the back end services, while the app server will run Upstage.

We will use Let's Encrypt to generate SSL keys for that domain. If you do not want to use Let's Encrypt, you may want to cherrypick lines from the next script and run them manually.

Please see the README for further details.
"
