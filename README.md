
# DidacticMadder-FrontEnd

-------------------------------------------------------------
Install Ubuntu 20.04 Server
- Disable cloud init
-- Add `cloud-init=disabled` to `GRUB_CMDLINE_LINUX` in /etc/default/grub
-- `update-grub`
-------------------------------------------------------------
Install required components:
- `sudo apt-get install python3-pip nginx redis-server`
- `sudo pip3 install gunicorn`
-------------------------------------------------------------
Edit (might be default) `/etc/nginx/nginx.conf`:

```
events {
        worker_connections 768;
}
```
-------------------------------------------------------------
Create self signed certificate (maybe use hostname for CN?)
`sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout /etc/ssl/private/nginx-selfsigned.key -out /etc/ssl/certs/nginx-selfsigned.crt`
-------------------------------------------------------------
- Install CTFd to `/opt/CTFd` (based on https://github.com/CTFd/CTFd):
```
cd /opt/
sudo git clone https://github.com/CTFd/CTFd.git
sudo chown -R nimda:nimda CTFd
cd CTFd
pip3 install -r requirements.txt
sudo apt-get install -y libmariadb-dev
pip3 install rq
pip3 install mariadb
```
- set `REDIS_URL = redis://localhost:6379` in config.ini
-------------------------------------------------------------
Build/install guacamole-server
- According to https://guacamole.apache.org/doc/gug/installing-guacamole.html
`sudo apt install -y gcc g++ libcairo2-dev libjpeg-turbo8-dev libpng-dev libtool-bin libossp-uuid-dev libavcodec-dev libavutil-dev libswscale-dev freerdp2-dev libpango1.0-dev libssh2-1-dev libvncserver-dev libtelnet-dev libssl-dev libvorbis-dev libwebp-dev make build-essential`

```
wget https://mirror.olnevhost.net/pub/apache/guacamole/1.3.0/source/guacamole-server-1.3.0.tar.gz
tar -xzf guacamole-server-1.3.0.tar.gz
cd guacamole-server-1.3.0/
./configure --with-init-dir=/etc/init.d
sudo make
sudo make install
sudo ldconfig
sudo systemctl start guacd
sudo systemctl enable guacd

sudo apt install -y tomcat9 tomcat9-admin tomcat9-common tomcat9-user
sudo mkdir /etc/guacamole
sudo wget https://downloads.apache.org/guacamole/1.3.0/binary/guacamole-1.3.0.war -O /etc/guacamole/guacamole.war
sudo ln -s /etc/guacamole/guacamole.war /var/lib/tomcat9/webapps/
sudo systemctl restart tomcat9
sudo mkdir /etc/guacamole/{extensions,lib}
echo "GUACAMOLE_HOME=/etc/guacamole" | sudo tee -a /etc/default/tomcat9

sudo ln -s /etc/guacamole /usr/share/tomcat9/.guacamole
```
-------------------------------------------------------------
- Install database for guacamole (https://guacamole.apache.org/doc/gug/jdbc-auth.html)

```
sudo apt install mariadb-server
sudo mysql_secure_installation
```


```
wget https://mirrors.sonic.net/apache/guacamole/1.3.0/binary/guacamole-auth-jdbc-1.3.0.tar.gz
sudo tar xvf guacamole-auth-jdbc-1.3.0.tar.gz
cd guacamole-auth-jdbc-1.3.0/mysql/
sudo mysql -u root
CREATE DATABASE guacamole_db; 
CREATE USER 'guacamole_user'@'localhost' IDENTIFIED BY 'ST@dm1n!';
GRANT SELECT,INSERT,UPDATE,DELETE ON guacamole_db.* TO 'guacamole_user'@'localhost';
FLUSH PRIVILEGES;
exit

cat schema/*.sql | sudo mysql -u root guacamole_db
sudo cp guacamole-auth-jdbc-mysql-1.3.0.jar /etc/guacamole/extensions/
cd
sudo wget https://dev.mysql.com/get/Downloads/Connector-J/mysql-connector-java-8.0.23.tar.gz
sudo tar xvf mysql-connector-java-8.0.23.tar.gz mysql-connector-java-8.0.23/
sudo mv mysql-connector-java-8.0.23/mysql-connector-java-8.0.23.jar /etc/guacamole/lib
```

-------------------------------------------------------------
- Configure CTFd
- plugin for DM
- Install CTFd/CTFd/plugins/virtual_machine_challenges

-------------------------------------------------------------
- `cd /opt`
- `sudo git clone https://github.com/w-a-y-n-e/DidacticMadder-FrontEnd.git`

- `cd DidacticMadder-FrontEnd`

- Change:
username in gunicorn.service
database user and password in guacamole.properties
- Change database password in 
- `sudo cp guacamole-ctfd-authentication/target/guacamole-ctfd-auth-1.2.0.jar /etc/guacamole/extensions/`

- `mvn assembly:assembly -DdescriptorId=jar-with-dependencies`

```
sudo cp gunicorn.service /etc/systemd/system/gunicorn.service
sudo cp gunicorn.socket /etc/systemd/system/gunicorn.socket
sudo cp reverse_proxy /etc/nginx/sites-available/reverse_proxy
sudo ln -s /etc/nginx/sites-available/reverse_proxy /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo cp guacamole.properties /etc/guacamole/guacamole.properties
sudo cp -r virtual_machine_challenges /opt/CTFd/CTFd/plugins/
sudo systemctl restart nginx
sudo systemctl daemon-reload
sudo systemctl restart gunicorn.socket
sudo systemctl enable gunicorn.socket
sudo systemctl enable gunicorn.service
sudo systemctl restart gunicorn.service
```
