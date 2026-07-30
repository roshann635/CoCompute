# ─────────────────────────────────────────────────────────
#  CoCompute — Generate self-signed SSL certificates
# ─────────────────────────────────────────────────────────

$CertDir = Join-Path $PSScriptRoot "certs"
New-Item -ItemType Directory -Force -Path $CertDir | Out-Null

Write-Host ""
Write-Host "  CoCompute - SSL Certificate Generator" -ForegroundColor Cyan
Write-Host "  ======================================" -ForegroundColor Cyan
Write-Host ""

# Check for OpenSSL
if (Get-Command openssl -ErrorAction SilentlyContinue) {
    openssl req -x509 -nodes -days 365 `
        -newkey rsa:2048 `
        -keyout "$CertDir\server.key" `
        -out "$CertDir\server.crt" `
        -subj "/C=IN/ST=State/L=City/O=CoCompute/CN=localhost" `
        -addext "subjectAltName=DNS:localhost,DNS:*.localhost,IP:127.0.0.1"

    Write-Host ""
    Write-Host "  Certificates generated in $CertDir\" -ForegroundColor Green
    Write-Host "    - server.crt  (certificate)" -ForegroundColor White
    Write-Host "    - server.key  (private key)" -ForegroundColor White
}
else {
    # Fallback: PowerShell self-signed cert
    Write-Host "  OpenSSL not found. Using PowerShell fallback..." -ForegroundColor Yellow

    $cert = New-SelfSignedCertificate `
        -DnsName "localhost" `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -NotAfter (Get-Date).AddDays(365) `
        -FriendlyName "CoCompute SSL" `
        -KeyExportPolicy Exportable

    # Export as PFX
    $pwd = ConvertTo-SecureString -String "cocompute" -Force -AsPlainText
    Export-PfxCertificate -Cert $cert -FilePath "$CertDir\server.pfx" -Password $pwd | Out-Null

    Write-Host ""
    Write-Host "  PFX certificate generated: $CertDir\server.pfx" -ForegroundColor Green
    Write-Host ""
    Write-Host "  To convert to PEM (for nginx), install OpenSSL and run:" -ForegroundColor Yellow
    Write-Host "    openssl pkcs12 -in certs\server.pfx -out certs\server.crt -nokeys -password pass:cocompute" -ForegroundColor White
    Write-Host "    openssl pkcs12 -in certs\server.pfx -out certs\server.key -nodes -nocerts -password pass:cocompute" -ForegroundColor White
}

Write-Host ""
Write-Host "  To enable SSL, run:" -ForegroundColor Cyan
Write-Host "    docker-compose -f docker-compose.yml -f docker-compose.ssl.yml up --build" -ForegroundColor White
Write-Host ""
