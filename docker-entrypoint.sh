#!/bin/bash
set -e

# Check if using Cosmos DB emulator with HTTPS
if [[ "$COSMOS_DB_ENDPOINT" == *"cosmosdb"* ]] && [[ "$COSMOS_DB_ENDPOINT" == "https://"* ]]; then
    echo "Installing Cosmos DB emulator certificate..."
    
    # Extract host and port
    COSMOS_HOST=$(echo "$COSMOS_DB_ENDPOINT" | sed -E 's|https?://([^:/]+).*|\1|')
    COSMOS_PORT=${COSMOS_DB_ENDPOINT##*:}
    COSMOS_PORT=${COSMOS_PORT%/*}
    [[ "$COSMOS_PORT" =~ ^[0-9]+$ ]] || COSMOS_PORT=8081
    
    # Wait for emulator
    for i in {1..24}; do
        timeout 5 openssl s_client -connect $COSMOS_HOST:$COSMOS_PORT </dev/null >/dev/null 2>&1 && break
        [ $i -eq 24 ] && { echo "Warning: Emulator not ready"; exec "$@"; }
        sleep 5
    done
    
    # Extract and install certificate
    openssl s_client -connect $COSMOS_HOST:$COSMOS_PORT </dev/null 2>/dev/null | \
        sed -ne '/-BEGIN CERTIFICATE-/,/-END CERTIFICATE-/p' > /tmp/cosmos.crt
    
    cp /tmp/cosmos.crt /usr/local/share/ca-certificates/cosmos.crt
    update-ca-certificates >/dev/null 2>&1
    
    # Update Python certifi
    CERTIFI_PATH=$(python -c "import certifi; print(certifi.where())" 2>/dev/null)
    [ -f "$CERTIFI_PATH" ] && cat /tmp/cosmos.crt >> "$CERTIFI_PATH"
    
    # Enable SSL verification
    unset PYTHONHTTPSVERIFY REQUESTS_CA_BUNDLE CURL_CA_BUNDLE SSL_CERT_FILE
    echo "Certificate installed - SSL enabled"
fi

exec "$@"
