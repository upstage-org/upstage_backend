#!/bin/bash 
# Make sure the setup-os.sh has been executed before this script.
export DEBIAN_FRONTEND=noninteractive

# Running from the root dir...
# Make sure this setting matches the setting in ./initial_scripts/environments/generate_environments_script.sh
# load_env.py is generated on the svc machine and copied manually to the app machine.
output_file="/app_code/src/global_config/load_env.py"
jitsi_env_file="/streaming_files/config/envfile"

read -p "
Enter the domain name, including subdomain. Ex: streaming.myupstage.org: " dname
read -p "
1: If this is a service machine (dbs, mqtt) enter 1,
2: an app machine (running UpStage application code), enter 2,
3: a streaming machine, enter 3: " machinetype
machinetype=$((machinetype))

currdir=$PWD

run_these_ufw_commands=$currdir/run_these_ufw_commands_on_svc_machine.sh

if [[ -z "$dname" ]]
then
        echo "No empty values allowed."
        exit -1
fi

# Setup Nginx and Certbot
apt -y install certbot python3-certbot-nginx

apt -y update
apt -y upgrade

ufw status
ufw allow 'Nginx Full'
ufw delete allow 'Nginx HTTP'
ufw status

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
> /var/www/html/index.nginx-debian.html
> /usr/share/nginx/html/index.html

nginx -t
systemctl restart nginx

cd $currdir

case $machinetype in
        1) certbot --nginx -d $dname
           sed "s/YOUR_DOMAIN_NAME/$dname/g" ./initial_scripts/nginx_templates/nginx_template_for_svc_machines.conf >/etc/nginx/sites-available/$dname.conf
           mkdir -p /postgresql_data/var
           mkdir -p /postgresql_data/data
           mkdir -p /mongodb_data_volume
           mkdir -p /mosquitto_files/etc/mosquitto/conf.d
           mkdir -p /mosquitto_files/etc/mosquitto/cron
           mkdir -p /mosquitto_files/var/lib/mosquitto
           ./initial_scripts/environments/generate_environments_script.sh

           cp ./container_scripts/mqtt_server/mosquitto.conf /mosquitto_files/etc/mosquitto/mosquitto.conf
           cp ./container_scripts/mqtt_server/pw.txt /mosquitto_files/etc/mosquitto/pw.txt
           cp ./container_scripts/mqtt_server/pw.txt /mosquitto_files/etc/mosquitto/pw.backup
           cp ./container_scripts/mqtt_server/local_mosquitto.conf /mosquitto_files/etc/mosquitto/conf.d/local_mosquitto.conf
           cp ./container_scripts/mqtt_server/add_mqtt_cert_crontab.sh /mosquitto_files/etc/mosquitto/cron/add_mqtt_cert_crontab.sh
           cd ./service_containers && ./run_docker_compose.sh 

           # Mosquitto inbound websocket port. Mosquitto is password-protected. 
           # The websocket needs to be open to the world, since the front end attaches to it.
           # The TCP port is private, only used by our app server.
           ufw allow 9002/any

           cd $currdir
           echo "
Completed service container setup."
                ;;
        2) certbot --nginx -d $dname
           sed "s/YOUR_DOMAIN_NAME/$dname/g" ./initial_scripts/nginx_templates/nginx_template_for_app_machines.conf >/etc/nginx/sites-available/$dname.conf
           mkdir -p /frontend_code
           mkdir -p /app_code/demo
           mkdir -p /app_code/uploads
           cp -r ./src /app_code
           cp -r ./alembic /app_code
           cp -r ./scripts /app_code
           cp -r ./dashboard/demo /app_code
           cp -r ./requirements.txt /app_code
           chmod -R 777 /app_code/alembic
           chmod -R 777 /app_code/uploads

           a=`hostname -I`
           read -a arr <<< "$a"
           echo "
Note that on Digital Ocean, the third IP in the 'hostname -I' command: ${arr[2]} is the local network IP, used for faster connection without going out to the internet. That is the IP we're using. If this is incorrect in your environment, please change this IP address in this generated script: $run_this_on_svc_machine . Note that the mongo port 27018 is open in case you're using the shared email feature. if you're not allowing clients to send emails through your server, remove this UFW rule."
           APP_HOST="${arr[2]}"
           echo '#!/bin/bash' > $run_these_ufw_commands
           echo "ufw allow from $APP_HOST proto tcp to any port 5433 " >> $run_these_ufw_commands
           echo "ufw allow from $APP_HOST proto tcp to any port 27018 " >> $run_these_ufw_commands
           echo "ufw allow from $APP_HOST proto any to any port 1884 " >> $run_these_ufw_commands

           read -p "
Please log into your service machine in another shell, and copy your load_env.py file generated on your service machine (most likely here: /root/upstage_backend/src/global_config ) to /app_code/src/global_config on this machine. Once this is done, press enter to continue: " ready
           chmod 755 $output_file
           sed -i "s/{APP_HOST}/$dname/g" $output_file

           read -p "
Run the contents of this script over on the service machine:
           `cat $run_these_ufw_commands` 
           Press enter when finished: " ready
           cd ./app_containers && ./run_docker_compose.sh 
                ;;

        
        3) certbot --nginx -d $dname -d auth.$dname # Prosody, a Jitsi component, needs 'auth' even if users won't be logging into your stream.
           sed "s/YOUR_DOMAIN_NAME/$dname/g" ./initial_scripts/nginx_templates/nginx_template_for_streaming_machines.conf >/etc/nginx/sites-available/$dname.conf
           ufw allow 10000/udp          # Used by Jitsi-videobridge to run an internal test when connection id bad.
           DIST="$(lsb_release -sc)"

           curl https://download.jitsi.org/jitsi-key.gpg.key | sudo sh -c 'gpg --dearmor > /usr/share/keyrings/jitsi-keyring.gpg'
           echo 'deb [signed-by=/usr/share/keyrings/jitsi-keyring.gpg] https://download.jitsi.org stable/' > /etc/apt/sources.list.d/jitsi-stable.list

           apt update -y
           apt upgrade -y
           read -p "In the next prompt, pick 'Use my own SSL keys'. 
Jitsi will prompt you for the location of the existing SSL keys. These are the responses:

/etc/letsencrypt/live/$dname/fullchain.pem
/etc/letsencrypt/live/$dname/privkey.pem

Once you've copy-pasted these to another screen, press enter to continue:" resp

           cp /etc/letsencrypt/live/$dname/fullchain.pem /var/lib/prosody/$dname.crt
           cp /etc/letsencrypt/live/$dname/fullchain.pem /var/lib/prosody/auth.$dname.crt
           cp /etc/letsencrypt/live/$dname/privkey.pem /var/lib/prosody/$dname.key
           cp /etc/letsencrypt/live/$dname/privkey.pem /var/lib/prosody/auth.$dname.key

           apt -y install jitsi-meet
           sed "s/YOUR_DOMAIN_NAME/$dname/g" ./initial_scripts/post_install/jitsi-cert-cron-script.sh >/root/jitsi-cert-cron-script.sh
           chmod 755 /root/jitsi-cert-cron-script.sh
           echo "0 1 * * * /root/jitsi-cert-cron-script.sh" >/tmp/pcron
           crontab /tmp/pcron
           rm /tmp/pcron
           crontab -l

                ;;
        *) echo "No match for machine type $machinetype, exiting."
                ;;
esac

systemctl restart nginx
