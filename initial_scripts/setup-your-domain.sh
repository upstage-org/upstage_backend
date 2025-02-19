# #!/bin/bash 
# Make sure the setup-os.sh has been executed before this script.

read -p "Enter the domain name, including subdomain. Ex: streaming.myupstage.org: " dname
read -p "1: If this is a service machine (dbs, mqtt) enter 1,
2: an app machine, enter 2,
3: a streaming machine, enter 3,
4: a front end machine, enter 4: " machinetype
machinetype=$((machinetype))

currdir=$PWD

if [[ -z "$dname" ]]
then
	echo "No empty values allowed."
	exit -1
fi

mkdir -p /etc/nginx/ssl
cd /etc/nginx/ssl
openssl dhparam -out dhparam.pem 2048

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

certbot --nginx -d $dname

cd $currdir

case $machinetype in
	1) sed "s/YOUR_DOMAIN_NAME/$dname/g" ./initial_scripts/nginx_template_for_svc_machines.conf >/etc/nginx/sites-available/$dname.conf
           mkdir /postgresql_data_volume
           mkdir /mongodb_data_volume
		;;
	2) sed "s/YOUR_DOMAIN_NAME/$dname/g" ./initial_scripts/nginx_template_for_app_machines.conf >/etc/nginx/sites-available/$dname.conf
		;;
	3) sed "s/YOUR_DOMAIN_NAME/$dname/g" ./initial_scripts/nginx_template_for_streaming_machines.conf >/etc/nginx/sites-available/$dname.conf
		;;
	4) sed "s/YOUR_DOMAIN_NAME/$dname/g" ./initial_scripts/nginx_template_for_front_end_machines.conf >/etc/nginx/sites-available/$dname.conf
		;;
	*) echo "No match for machine type $machinetype, exiting."
		;;
esac

nginx -t
systemctl restart nginx

read -p "Do you want to fill in environment variables? (yes/no): " fill_env
if [[ "$fill_env" == "yes" ]]; then
	cd $currdir
    sh configuration_scripts/environments/generate_environments_script.sh
else
    echo "Exiting without filling environment variables."
    exit 0
fi
