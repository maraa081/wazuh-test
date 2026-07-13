#!/bin/bash
# install-docker.sh — Install Docker on Ubuntu 22.04 for the campaign runner
# Usage: sudo bash install-docker.sh
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then echo "ERREUR: lance en root"; exit 1; fi

echo "=== Installation Docker sur Ubuntu 22.04 ==="

# Remove old packages
for pkg in docker.io docker-doc docker-compose podman-docker containerd runc; do
    apt-get remove -y $pkg 2>/dev/null || true
done

# Add Docker's official GPG key and repo
apt-get update -qq
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker packages
apt-get update -qq
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable
systemctl enable docker
systemctl start docker

# Verify
docker --version && echo "OK Docker installe" || echo "Echec installation"

# Add current user to docker group (avoid sudo)
if [ -n "${SUDO_USER:-}" ]; then
    usermod -aG docker "$SUDO_USER"
    echo "User $SUDO_USER ajoute au groupe docker (re-login requis)"
fi

echo ""
echo "Prêt à lancer: curl -sL https://raw.githubusercontent.com/maraa081/wazuh-test/main/scripts/docker-dataset/run-campaign.sh | sudo bash"
