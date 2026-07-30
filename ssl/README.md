# CoCompute — SSL/TLS Setup

## Quick Start

### 1. Generate Certificates

**Linux / macOS:**
```bash
cd ssl
chmod +x generate_certs.sh
./generate_certs.sh
```

**Windows (PowerShell):**
```powershell
cd ssl
.\generate_certs.ps1
```

This creates `ssl/certs/server.crt` and `ssl/certs/server.key`.

### 2. Launch with SSL

```bash
docker-compose -f docker-compose.yml -f docker-compose.ssl.yml up --build
```

This will:
- Serve the dashboard over **HTTPS** (port 443)
- Redirect HTTP (port 80) to HTTPS
- Proxy API/WebSocket traffic through nginx with TLS termination
- Configure workers to use **WSS** (secure WebSocket)

### 3. Access

- Dashboard: `https://localhost`
- API Docs: `https://localhost/api/v1/docs`

> **Note:** Your browser will show a security warning for the self-signed certificate.
> This is expected for LAN deployments. Click "Advanced" → "Proceed" to continue.

## Architecture

```
Browser ──HTTPS──▶ Nginx (TLS termination)
                        │
                        ├──HTTP──▶ Master API (port 8000)
                        └──WS────▶ Master WS  (port 8000)

Worker ──WSS──▶ Master (port 8000, optional TLS)
```

## Worker TLS Configuration

Workers support TLS via environment variables:

| Variable | Default | Description |
|---|---|---|
| `USE_TLS` | `false` | Enable TLS for master connections |
| `TLS_VERIFY` | `false` | Verify SSL certificates (set `false` for self-signed) |

## Production Recommendations

For production deployments:
1. Replace self-signed certificates with CA-signed ones (e.g., Let's Encrypt)
2. Set `TLS_VERIFY=true` on workers
3. Rotate certificates before expiry (365 days)
