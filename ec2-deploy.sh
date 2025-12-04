#!/bin/bash

# 1. Install required packages
echo "--- Installing Python ---"
sudo yum install -y python3-pip


# 2. Create virtual environment and install dependencies
echo "--- Creating Virtual Environment ---"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
echo "--- Installing Dependencies ---"
pip install -r requirements.txt
echo "--- Dependencies Installed ---"

3. Initialize database tables
echo "--- Initializing Database Tables ---"
python3 setup_db.py 
deactivate

4. Copy the service file and start the service
echo "--- Copying Service File ---"
sudo cp ./stravaapp.service /etc/systemd/system/
echo "--- Reloading Systemd ---"
sudo systemctl daemon-reload
echo "--- Enabling Service ---"
sudo systemctl enable stravaapp.service 
echo "--- Starting Service ---"
sudo systemctl start stravaapp.service
echo "--- Service Started ---"