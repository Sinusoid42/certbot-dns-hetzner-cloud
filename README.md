
# certbot-dns-hetzner (Cloud API Edition – 2026)


  This repository provides a Certbot DNS plugin for the Hetzner Cloud DNS API
  (Hetzner Console DNS – 2026 generation).

  IMPORTANT
  ------------------------------------------------------------------------
  - This version supports ONLY the new Zone-Based Hetzner Cloud DNS API.
  - It does NOT support the legacy DNS Console API (dns.hetzner.com).
  - It does NOT support HTTP-01 challenges.
  - It does NOT support TLS-ALPN-01 challenges.
  - It supports DNS-01 challenges only.
  - Your DNS zone must already be migrated to Hetzner Console DNS.

  If your zone is still using the legacy DNS Console API, migrate it first.


# OVERVIEW


  This plugin allows Certbot to:

  • Create _acme-challenge TXT records via Hetzner Cloud DNS API
  • Validate DNS-01 challenges
  • Remove TXT records after validation
  • Issue wildcard certificates
  • Use Hetzner’s RRset-based DNS model correctly

  The implementation uses:

      https://api.hetzner.cloud/v1

  and authenticates using:

      Authorization: Bearer <CLOUD_API_TOKEN>


# REQUIREMENTS


  - Python 3.8+
  - Certbot (APT or pip installation recommended; snap not recommended)
  - Hetzner Cloud API token (Console → Security → API Tokens)
  - DNS zone migrated to Hetzner Console DNS
  - Proper firewall allowing outbound HTTPS (TCP 443)


# INSTALLATION


  IMPORTANT: This repository must be installed in the SAME Python
  environment that Certbot uses.

  Step 1 — Navigate into repository (or where you downloaded the repository to):

      cd /home/user/certbot-dns-hetzner

  Step 2 — Remove any previously installed versions when only using the zones (legacy from May26):

      sudo python3 -m pip uninstall -y certbot-dns-hetzner || true

  Step 3 — Install this repository in editable mode (optional):

      sudo python3 -m pip install -e . --break-system-packages

  Step 4 — Verify correct plugin path:

      sudo python3 -c "import certbot_dns_hetzner; print(certbot_dns_hetzner.__file__)"

  The printed path MUST point to your local repository.


# CREDENTIALS FILE


  Create/Edit credentials.ini:

      api_token = YOUR_HETZNER_CLOUD_API_TOKEN

  Example location:

      /home/ubuntu/certbot-dns-hetzner/credentials.ini

  Secure it (Make sure for prod. environments correct RW permissons apply):

      sudo chown root:root /home/dev/certbot-dns-hetzner/credentials.ini
      sudo chmod 600 /home/dev/certbot-dns-hetzner/credentials.ini


# AUTOMATED CERTIFICATE ISSUING


  This repository includes:

      setup_hetzner_certbot.sh

  This script:

  - Installs the plugin in editable mode
  - Validates credentials file
  - Ensures correct permissions
  - Issues certificates for predefined domains
  - Works with firewall-restricted environments
  - Uses TLS-enforced API communication (HTTPS only)

  REQUIRED CHANGES FOR USAGE:
  - The path/to/local/repository has to be changed, given your personal Environment
    This is present in the 'setupo_hetzner_certbot.sh' file allowing you to automate the certificate issuing.

  Example execution:

      ./setup_hetzner_certbot.sh


# MANUAL CERTIFICATE ISSUE


  Example multi-domain certificate:

      sudo certbot certonly \
        --authenticator dns-hetzner \
        --dns-hetzner-credentials /home/dev/certbot-dns-hetzner/credentials.ini \
        --dns-hetzner-propagation-seconds 60 \
        -d mydomain.net \
        -d auth.mydomain.net \
        -d console.mydomain.net \
        -d api.mydomain.net \
        -d www.mydomain.net

  Wildcard example:

      sudo certbot certonly \
        --authenticator dns-hetzner \
        --dns-hetzner-credentials /home/dev/certbot-dns-hetzner/credentials.ini \
        --dns-hetzner-propagation-seconds 60 \
        -d mydomain.net \
        -d '*.mydomain.net'


#  Changes from DNS 2.0 to Hetzner CloudAPI 3.0


  Hetzner Cloud DNS uses an RRset-based model.

  TXT records are managed via:

      POST /v1/zones/{zone}/rrsets/{name}/TXT/actions/add_records
      POST /v1/zones/{zone}/rrsets/{name}/TXT/actions/remove_records

  ###  The Urls have changed and some auth-flow has changed.
  ### The user is required now to use API Keys from the 'Hetzner-Console' not the 'DNSConsole'
  
  ## Issuing new API Keys
  - Go to Hetzner Console (Shows the Projects) (Not DNS Console)
  - Open the specific project
  - In the left Menu open "Security" and on the top 'API Tokens'
  - Generate a new APIToken with Read and Write Permissions.

  
 # TROUBLESHOOTING


  401 Unauthorized
  ----------------
  - Ensure you are using a Hetzner Cloud API token
  - Do NOT use DNS Console API tokens
  - Ensure correct API permissions (DNS read/write)
  - Verify certbot imports the correct plugin path

  Check:

      which certbot
      certbot --version
      sudo python3 -c "import certbot_dns_hetzner; print(certbot_dns_hetzner.__file__)"

  If certbot comes from /snap/bin/certbot,
  pip-installed plugins will NOT work.

  DNS Propagation Failure
  -----------------------
  Increase propagation wait time:

      --dns-hetzner-propagation-seconds 120

  Credentials Permission Warning
  ------------------------------
  Ensure credentials file is 600 and owned by root.


 ### SECURITY NOTES


  - Never expose API tokens
  - Use project-scoped tokens when possible
  - Keep credentials file restricted (chmod 600)
  - Rotate tokens periodically
  - Do not commit credentials into repository

 
###  COMPATIBILITY


  Supported:
  - Hetzner Cloud DNS (Console DNS 2026+)
  - DNS-01 challenge
  - Wildcard certificates
  - Firewall-restricted environments (HTTPS outbound)

  Not Supported:
  - Legacy DNS Console API
  - HTTP-01
  - TLS-ALPN-01
  - Secondary DNS mode


 ## LICENSE
 

  MIT License
