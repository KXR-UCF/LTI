#!/usr/bin/env bash
# Prepare a Raspberry Pi running the WANDA software.
#
# This script expects the repository at /home/lti/Wanda and is intended to be
# run by the lti user. It installs dependencies and service units, but does not
# enable control or data-acquisition services.

set -euo pipefail

readonly WANDA_USER="lti"
readonly WANDA_HOME="/home/${WANDA_USER}"
readonly WANDA_DIR="${WANDA_HOME}/Wanda"
readonly VENV_DIR="${WANDA_HOME}/venv"
readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

INSTALL_GRAFANA=true
case "${1:-}" in
    "") ;;
    --skip-grafana) INSTALL_GRAFANA=false ;;
    *)
        echo "Usage: $0 [--skip-grafana]" >&2
        exit 1
        ;;
esac

if [[ "$(id -un)" != "${WANDA_USER}" ]]; then
    echo "Run this script as ${WANDA_USER}, not $(id -un)." >&2
    exit 1
fi

if [[ "${SCRIPT_DIR}" != "${WANDA_DIR}" ]]; then
    echo "Expected this repository at ${WANDA_DIR}; found it at ${SCRIPT_DIR}." >&2
    echo "Update the service-unit paths before using a different location." >&2
    exit 1
fi

echo "=== WANDA Pi setup ==="

echo "--- Installing system dependencies ---"
sudo apt-get update
sudo apt-get install -y \
    ca-certificates \
    curl \
    python3-dev \
    python3-pip \
    python3-venv \
    swig \
    liblgpio-dev

echo "--- Creating Python environment ---"
python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip
"${VENV_DIR}/bin/python" -m pip install -r "${WANDA_DIR}/requirements.txt"

echo "--- Installing Docker ---"
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

source /etc/os-release
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian ${VERSION_CODENAME} stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "${WANDA_USER}"

echo "--- Creating QuestDB container ---"
if ! sudo docker container inspect osiris > /dev/null 2>&1; then
    sudo bash "${WANDA_DIR}/Questdb/createServer.sh"
else
    echo "QuestDB container 'osiris' already exists; leaving it unchanged."
fi

echo "--- Installing WANDA systemd units ---"
sudo install -m 0644 "${WANDA_DIR}"/Systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now wanda_status_server.service

echo "--- Configuring SPI ---"
if [[ -f /boot/firmware/config.txt ]]; then
    BOOT_CONFIG=/boot/firmware/config.txt
elif [[ -f /boot/config.txt ]]; then
    BOOT_CONFIG=/boot/config.txt
else
    echo "Could not find Raspberry Pi boot configuration file." >&2
    exit 1
fi

sudo sed -i 's/^dtparam=spi=on/#dtparam=spi=on/' "${BOOT_CONFIG}"
if ! grep -q '^dtoverlay=spi0-0cs' "${BOOT_CONFIG}"; then
    echo 'dtoverlay=spi0-0cs' | sudo tee -a "${BOOT_CONFIG}" > /dev/null
fi

if [[ "${INSTALL_GRAFANA}" == "true" ]]; then
    echo "--- Setting up Grafana ---"
    bash "${WANDA_DIR}/wanda_grafana_setup.sh"
fi

echo "=== Setup complete ==="
echo "Reboot before using the ADS1256 hardware."
echo "Log out and back in before using Docker without sudo."
echo "The WANDA status server is running; review the Pi role, Grafana token files,"
echo "and service configuration before enabling control or data-acquisition services."
