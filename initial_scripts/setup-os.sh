# #!/bin/bash
# Install and setup the OS
export DEBIAN_FRONTEND=noninteractive

apt -y update
apt -y upgrade

apt -y install ufw
yes | ufw allow ssh
yes | ufw enable

# Add Docker's official GPG key and other tools:
apt -y install ca-certificates curl logrotate

cp initial_scripts/logrotate_for_docker.commands /etc/logrotate.d/docker
logrotate -d /etc/logrotate.d/docker

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null
apt -y update

$(. /etc/os-release && echo "$VERSION_CODENAME")

for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do apt-get -y remove ; done
apt -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

docker run hello-world

ufw status

echo "
Before proceeding to the next script, be sure that you have a domain name registered with a DNS registrar like namecheap, gandi, etc.
Also ensure that in your DNS records: 
1: an 'A' record points to the IP address of your app server, not your svc server.
2: an 'A' record points to the IP address of your svc server.
3: an 'A' record points to the IP address of your streaming server.
4: a working email address, such as support@your_upstage.org, to use when registering with Let's Encrypt.

We recommend domain names such as your_upstage.org , svc.your_upstage.org , streaming.your_upstage.org .

We will use Let's Encrypt to generate SSL keys for these domain. 
If you do not want to use Let's Encrypt, you may want to cherrypick lines from the next script and run them manually.

Please see the README for further details.
"
