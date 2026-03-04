#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "=== Starting Raspberry Pi Production Setup ==="

# 1. Update system and install required packages
echo "--- Updating system and installing dependencies ---"
sudo apt update
sudo apt upgrade -y
sudo apt install -y swig liblgpio-dev vim ca-certificates curl

# 2. Set up the Python Virtual Environment
echo "--- Setting up Python Virtual Environment ---"
cd ~
python3 -m venv venv
source venv/bin/activate

# 3. Install Python dependencies
echo "--- Installing Python packages ---"
cd ~/Production
python -m pip install -r requirements.txt

# 4. Remove conflicting Docker packages
echo "--- Cleaning up old Docker installations ---"
sudo apt remove -y docker.io docker-compose docker-doc podman-docker containerd runc || true

# 5. Add Docker's official GPG key and repo
echo "--- Setting up Docker repository ---"
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/debian
Suites: $(. /etc/os-release && echo "$VERSION_CODENAME")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF

# 6. Install Docker
echo "--- Installing Docker ---"
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 7. Set up QuestDB
echo "--- Initializing QuestDB Docker Container ---"
sudo chmod +x Questdb/createServer.sh
./Questdb/createServer.sh
# Stop the container immediately so systemd can take over
sudo docker stop osiris

# 8. Set up Systemd Services
echo "--- Copying Systemd services and starting them ---"
sudo cp -a Systemd/. /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable status_server.service
sudo systemctl start status_server.service

# 9. Configure Hardware Overlays
echo "--- Configuring SPI in /boot/firmware/config.txt ---"
# Comment out dtparam=spi=on if it exists and is uncommented
sudo sed -i 's/^dtparam=spi=on/#dtparam=spi=on/' /boot/firmware/config.txt

# Add dtoverlay=spi0-0cs if it doesn't already exist in the file
if ! grep -q "^dtoverlay=spi0-0cs" /boot/firmware/config.txt; then
    echo "dtoverlay=spi0-0cs" | sudo tee -a /boot/firmware/config.txt
fi

echo "=== Setup Complete! ==="
echo "A reboot is required to apply the changes."