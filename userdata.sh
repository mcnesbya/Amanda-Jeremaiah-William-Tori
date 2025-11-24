#!/bin/bash

# 1. Install required packages
yum install -y git python3 python3-pip

# 2. Clone into the home directory of the current user (ec2-user)
# Remove the existing directory if it's there
sudo rm -rf /opt/Amanda-Jeremaiah-William-Tori 
git clone https://github.com/cs298f25/Amanda-Jeremaiah-William-Tori.git /opt/Amanda-Jeremaiah-William-Tori


# 4. Change into the correct directory
cd /opt/Amanda-Jeremaiah-William-Tori

# 5. Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Administrative commands MUST have sudo if run manually by ec2-user
# When using this script as EC2 User Data, the sudo is optional but good for clarity.
# sudo cp stravaapp.service /etc/systemd/system
#/home/ec2-user/Amanda-Jeremaiah-William-Tori/.venv/bin/python3 -m pip install --upgrade pip
sudo cp stravaapp.service /etc/systemd/system
sudo systemctl daemon-reload # Good practice
sudo systemctl enable stravaapp.service
sudo systemctl start stravaapp.service