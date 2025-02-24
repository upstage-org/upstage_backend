# #!/bin/bash 
# Make sure the setup-os.sh has been executed before this script.

read -p "
Enter the domain name, including subdomain. Ex: streaming.myupstage.org: " dname
read -p "
1: If this is a service machine (dbs, mqtt) enter 1,
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

# Setup Nginx and Certbot
sudo apt install certbot python3-certbot-nginx

sudo apt update
sudo apt upgrade

sudo ufw status
sudo ufw allow 'Nginx Full'
sudo ufw delete allow 'Nginx HTTP'
sudo ufw status

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

certbot --nginx -d $dname

cd $currdir

case $machinetype in
	1) sed "s/YOUR_DOMAIN_NAME/$dname/g" ./initial_scripts/nginx_templates/nginx_template_for_svc_machines.conf >/etc/nginx/sites-available/$dname.conf
           mkdir -p /postgresql_data/var
           mkdir -p /postgresql_data/data
           mkdir -p /mongodb_data_volume
           mkdir -p /mosquitto_files/etc/mosquitto/conf.d
           mkdir -p /mosquitto_files/etc/mosquitto/cron
           ./initial_scripts/environments/generate_environments_script.sh

           cp ./container_scripts/mqtt_server/mosquitto.conf /mosquitto_files/etc/mosquitto/mosquitto.conf
           cp ./container_scripts/mqtt_server/pw.txt /mosquitto_files/etc/mosquitto/pw.txt
           cp ./container_scripts/mqtt_server/local_mosquitto.conf /mosquitto_files/etc/mosquitto/conf.d/local_mosquitto.conf
           cp ./container_scripts/mqtt_server/add_mqtt_cert_crontab.sh /mosquitto_files/etc/mosquitto/cron/add_mqtt_cert_crontab.sh
	   cd ./service_containers && ./run_docker_compose.sh 

	   cd $currdir
	   echo "
Completed service container setup."
		;;
	2) sed "s/YOUR_DOMAIN_NAME/$dname/g" ./initial_scripts/nginx_templates/nginx_template_for_app_machines.conf >/etc/nginx/sites-available/$dname.conf
           mkdir -p /app_code/demo
           mkdir -p /app_code/uploads
           cp -r ./src /app_code
           cp -r ./scripts /app_code
           cp -r ./dashboard/demo /app_code
           cp -r ./requirements.txt /app_code
           cp -r ./startup.sh /app_code

	   read -p "Now is the perfect time to copy your load_env.py file generated on your service machine (most likely here: /root/upstage_backend/src/global_config ) to /app_code/src/global_config on this machine. Once this is done, press enter to continue: " ready
	   cd ./app_containers && ./run_docker_compose.sh 
		;;
	3) sed "s/YOUR_DOMAIN_NAME/$dname/g" ./initial_scripts/nginx_templates/nginx_template_for_streaming_machines.conf >/etc/nginx/sites-available/$dname.conf
		;;
	4) sed "s/YOUR_DOMAIN_NAME/$dname/g" ./initial_scripts/nginx_templates/nginx_template_for_front_end_machines.conf >/etc/nginx/sites-available/$dname.conf
		;;
	*) echo "No match for machine type $machinetype, exiting."
		;;
esac
