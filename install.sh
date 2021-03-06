#!/usr/bin/env bash

set -e

dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" > /dev/null 2>&1 && pwd)"

sudo echo "" > /dev/null
sudo apt install $(awk '{printf "python3-%s ", $0}' requirements.txt)
sudo mkdir -p /etc/smtp_proxy/
sudo mkdir -p /etc/systemd/system
sudo cp "$dir/smtp-proxy.service" /etc/systemd/system/
sudo mkdir -p /usr/local/bin/
sudo cp "$dir/smtp_proxy.py" /usr/local/bin/
systemctl enable --now smtp-proxy.service
