#!/bin/bash
# ─────────────────────────────────────────────────────────
#  CoCompute — Generate self-signed SSL certificates
# ─────────────────────────────────────────────────────────
set -e

CERT_DIR="$(dirname "$0")/certs"
mkdir -p "$CERT_DIR"

echo "╔═══════════════════════════════════════════════╗"
echo "║  CoCompute — SSL Certificate Generator        ║"
echo "╚═══════════════════════════════════════════════╝"
echo ""

openssl req -x509 -nodes -days 365 \
    -newkey rsa:2048 \
    -keyout "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.crt" \
    -subj "/C=IN/ST=State/L=City/O=CoCompute/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,DNS:*.localhost,IP:127.0.0.1"

chmod 600 "$CERT_DIR/server.key"
chmod 644 "$CERT_DIR/server.crt"

echo ""
echo "✅ Certificates generated in $CERT_DIR/"
echo "   • server.crt  (certificate)"
echo "   • server.key  (private key)"
echo ""
echo "To enable SSL, run:"
echo "  docker-compose -f docker-compose.yml -f docker-compose.ssl.yml up --build"
