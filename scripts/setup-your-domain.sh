# #!/bin/bash 
# Make sure the setup-os.sh has been executed before this script.

read -p "Enter the domain name, including subdomain. Ex: streaming.myupstage.org: " dname

if [[ -z "$dname" ]]
then
	echo "No empty values allowed."
	exit -1
fi

cd /etc/nginx/sites-available
echo "
server {
	server_name $dname;
} " > ${dname}.conf

cd /etc/nginx/sites-enabled
rm -rf default
ln -s ../sites-available/${dname}.conf .

nginx -t
systemctl restart nginx

# Setup Certbot

sudo apt install certbot python3-certbot-nginx
