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

hostnamectl set-hostname $dname

# Setup Nginx and Certbot
apt -y install certbot python3-certbot-nginx

apt -y update
apt -y upgrade

ufw status
ufw delete allow 'Nginx HTTP'
ufw allow 80
ufw allow 443
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
systemctl enable nginx

cd $currdir

case $machinetype in
        1) certbot --nginx -d $dname
           if [[ $? -ne 0 ]]; then
               echo "Certbot failed. Please wait a bit for your new DNS entries to propagate through the internet, and then retry."
               exit 1
           fi 
           sed "s/YOUR_DOMAIN_NAME/$dname/g" ./initial_scripts/nginx_templates/nginx_template_for_svc_machines.conf >/etc/nginx/sites-available/$dname.conf
           mkdir -p /postgresql_data/var
           mkdir -p /postgresql_data/data
           mkdir -p /mongodb_data_volume
           mkdir -p /mosquitto_files/etc/mosquitto/conf.d
           mkdir -p /mosquitto_files/etc/mosquitto/cron
           mkdir -p /mosquitto_files/var/lib/mosquitto
           ./initial_scripts/environments/generate_environments_script.sh
           
           chmod +x ./scripts/generate_cipher_key.sh
           ./scripts/generate_cipher_key.sh

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
           if [[ $? -ne 0 ]]; then
               echo "Certbot failed. Please wait a bit for your new DNS entries to propagate through the internet, and then retry."
               exit 1
           fi 
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
Please log into your service machine in another shell, and copy your load_env.py file generated on your service machine (most likely here: /root/upstage_backend/src/global_config ) to /app_code/src/global_config on this machine. 

You can do so by running 'scp' to copy the file down to your local machine, then using scp to copy it up to the app machine: 

On your own machine, in a shell window, run these, something like this:

scp root@your_service_machine.org:/root/upstage_backend/src/global_config/load_env.py .
scp ./load_env.py root@your_app_machine.org:/app_code/src/global_config/load_env.py

Once this is done, press enter to continue: " ready
           chmod 755 $output_file
           sed -i "s/{APP_HOST}/$dname/g" $output_file

           read -p "
Run the contents of this script over on the service machine:
           `cat $run_these_ufw_commands` 
           Press enter when finished: " ready
           cd ./app_containers && ./run_docker_compose.sh 
                ;;

        
        3) IFS='.' read -ra parts <<< "$dname"
           sed -i "s/^127.0.1.1.*$/127.0.1.1 ${dname} auth.${dname} ${parts[0]} auth.${parts[0]}/" /etc/hosts
           export DEBIAN_FRONTEND=dialog

           cd /etc/nginx/sites-available
           echo "
           server {
                   server_name ${dname} auth.${dname};
           } " > ${dname}.conf
           cd $currdir

           certbot --nginx -d $dname -d auth.$dname
           if [[ $? -ne 0 ]]; then
               echo "Certbot failed. Please wait a bit for your new DNS entries to propagate through the internet, and then retry."
               exit 1
           fi 
           # Prosody, a Jitsi component, needs 'auth' even if users won't be logging into your stream.
           sed "s/YOUR_DOMAIN_NAME/$dname/g" ./initial_scripts/nginx_templates/nginx_template_for_streaming_machines.conf >/etc/nginx/sites-available/$dname.conf
           ufw allow 10000/udp          # Used by Jitsi-videobridge to run an internal test when connection id bad.
           DIST="$(lsb_release -sc)"

           curl https://download.jitsi.org/jitsi-key.gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/jitsi-keyring.gpg
           echo "deb [signed-by=/usr/share/keyrings/jitsi-keyring.gpg] https://download.jitsi.org stable/" | sudo tee /etc/apt/sources.list.d/jitsi-stable.list

           apt update -y
           apt upgrade -y
           read -p "In the next two prompts, Jitsi will ask for your full domain name (not the 'auth.' domain). 

It will then ask you about SSL keys. Choose 'I want to use my own certificate'. 

Jitsi will prompt you for the location of the existing SSL keys. These are the responses:

For the cert, copy-paste: /etc/letsencrypt/live/$dname/fullchain.pem
For the key, copy-paste: /etc/letsencrypt/live/$dname/privkey.pem

Once you've copy-pasted these two paths to another screen/location, press enter to continue:" resp

           mkdir -p /etc/prosody/certs

           cp /etc/letsencrypt/live/$dname/fullchain.pem /etc/prosody/certs/$dname.crt
           cp /etc/letsencrypt/live/$dname/fullchain.pem /etc/prosody/certs/auth.$dname.crt
           cp /etc/letsencrypt/live/$dname/privkey.pem /etc/prosody/certs/$dname.key
           cp /etc/letsencrypt/live/$dname/privkey.pem /etc/prosody/certs/auth.$dname.key

           chmod 640 /etc/prosody/certs/*key
           chmod 644 /etc/prosody/certs/*crt
           chown prosody:prosody /etc/prosody/certs/*

           apt-get install jitsi-meet
           sed "s/YOUR_DOMAIN_NAME/$dname/g" ./initial_scripts/post_install/jitsi-cert-cron-script.sh >/root/jitsi-cert-cron-script.sh
           chmod 755 /root/jitsi-cert-cron-script.sh
           echo "0 1 * * * /root/jitsi-cert-cron-script.sh" >/tmp/pcron
           crontab /tmp/pcron
           rm /tmp/pcron
           crontab -l

           # Repeat this. Jitsi changes perms after installation.
           chmod 640 /etc/prosody/certs/*key
           chmod 644 /etc/prosody/certs/*crt
           chown prosody:prosody /etc/prosody/certs/*

                ;;
        *) echo "No match for machine type $machinetype, exiting."
                ;;
esac

systemctl restart nginx
