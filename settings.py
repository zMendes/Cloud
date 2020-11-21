#CONSTANTES

OWNER = 'loe'

#Ubuntu 20.04
DEFAULT_IMG_NAME = "ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-20200907"
#DEFAULT_IMG = "ami-07efac79022b86107"



INSTANCE_TYPE = "t2.micro"

PROTOCOL = "HTTP"

SECURITY_GROUP_NAME = "elo-sc"

LOAD_BALANCER_NAME = "loe-lb"

AUTO_SCALING_NAME = "loe-auto"
KEY_NAME = "leok"




POSTGRES_NAME = "post-loe"
POSTGRES_SCRIPT = """#!/bin/bash
cd /home/ubuntu
sudo apt update -y
sudo apt install postgresql postgresql-contrib -y
sudo su - postgres -c "psql -c \\"CREATE USER cloud  WITH PASSWORD 'cloud' \\""
sudo su - postgres -c 'createdb -O cloud tasks'
sudo sh -c "sed \\"s/#listen_addresses = 'localhost'/listen_addresses = '*' /\\"  /etc/postgresql/12/main/postgresql.conf > postgresql.conf"
sudo cp  postgresql.conf /etc/postgresql/12/main
sudo sh -c  " sed 'a host       all             all             0.0.0.0/0          md5' /etc/postgresql/12/main/pg_hba.conf  > pg_hba.conf" 
sudo cp pg_hba.conf /etc/postgresql/12/main/
sudo ufw allow 5432/tcp
sudo systemctl restart postgresql
"""
