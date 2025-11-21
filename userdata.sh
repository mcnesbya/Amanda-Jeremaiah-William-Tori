#!/bin/bash

# 1. Install git (requires sudo, which is included in User Data or you run this script with sudo)
yum install -y git

# 2. Clone into the home directory of the current user (ec2-user)
# Remove the existing directory if it's there
rm -rf Amanda-Jeremaiah-William-Tori 
git clone https://github.com/cs298f25/Amanda-Jeremaiah-William-Tori.git

# 3. Change into the correct relative directory
cd Amanda-Jeremaiah-William-Tori

# 4. Finish setup (These steps were successful, no change needed)
chmod +x redeploy.sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 5. Administrative commands MUST have sudo if run manually by ec2-user
# When using this script as EC2 User Data, the sudo is optional but good for clarity.
sudo cp stravaapp.service /etc/systemd/system
sudo systemctl daemon-reload # Good practice
sudo systemctl enable stravaapp.service
sudo systemctl start stravaapp.service