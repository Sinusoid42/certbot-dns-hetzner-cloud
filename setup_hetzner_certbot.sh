#!/bin/bash
set -e

REPO_DIR="/home/dev/certbot-dns-hetzner"
CREDENTIALS_FILE="$REPO_DIR/credentials.ini"

if [ ! -f "$CREDENTIALS_FILE" ]; then
  echo "Error: Credentials file '$CREDENTIALS_FILE' not found."
  exit 1
fi

# Ensure root certbot imports your local modified plugin
cd "$REPO_DIR"
sudo python3 -m pip install -e . --break-system-packages

# Fix permissions
sudo chown root:root "$CREDENTIALS_FILE"
sudo chmod 600 "$CREDENTIALS_FILE"

DOMAINS=(
  "mydomain.com"
)

DOMAIN_ARGS=""
for domain in "${DOMAINS[@]}"; do
  DOMAIN_ARGS="$DOMAIN_ARGS -d $domain"
done

sudo certbot certonly \
  --authenticator dns-hetzner \
  --dns-hetzner-credentials "$CREDENTIALS_FILE" \
  --dns-hetzner-propagation-seconds 60 \
  $DOMAIN_ARGS
