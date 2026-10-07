import asyncio
import json
import logging
import socket

logger = logging.getLogger(__name__)


def get_lan_ip(target_ip: str = None) -> str:
    """Determine the best LAN IP address of this machine to communicate with target_ip or LAN."""
    # If target is loopback, respond with loopback
    if target_ip in ("127.0.0.1", "localhost", "::1"):
        return "127.0.0.1"

    # Try connecting towards target_ip if provided
    if target_ip:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect((target_ip, 80))
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127."):
                return ip
        except Exception:
            pass

    # Check local NICs for private LAN address (192.168.x.x, 10.x.x.x, 172.x.x.x)
    try:
        import psutil
        for iface, snics in psutil.net_if_addrs().items():
            for snic in snics:
                if snic.family == socket.AF_INET and snic.address:
                    if snic.address.startswith(("192.168.", "10.", "172.")):
                        return snic.address
    except Exception:
        pass

    # Try connecting towards public DNS or gateway
    for probe in [("8.8.8.8", 80), ("1.1.1.1", 80), ("192.168.1.1", 80)]:

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.3)
            s.connect(probe)
            ip = s.getsockname()[0]
            s.close()
            if ip and not ip.startswith("127."):
                return ip
        except Exception:
            continue

    # Fallback to hostname resolution
    try:
        host_ip = socket.gethostbyname(socket.gethostname())
        if host_ip and not host_ip.startswith("127."):
            return host_ip
    except Exception:
        pass

    return "127.0.0.1"


import os
import hashlib

def get_master_code(ip: str = "127.0.0.1", port: int = 8000) -> str:
    """Generate or retrieve human-friendly Master Connect Code (e.g. CC-4827)."""
    env_code = os.getenv("MASTER_CODE")
    if env_code:
        cleaned = env_code.strip().upper()
        return cleaned if cleaned.startswith("CC-") else f"CC-{cleaned}"
    
    # Deterministic 4-character hex suffix from IP and Port
    h = hashlib.sha256(f"{ip}:{port}".encode("utf-8")).hexdigest()
    return f"CC-{h[:4].upper()}"


class MasterDiscoveryProtocol(asyncio.DatagramProtocol):
    def __init__(self, master_ip: str, master_port: int):
        self.configured_ip = master_ip
        self.master_port = master_port
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        try:
            sock = self.transport.get_extra_info('socket')
            if sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except Exception:
            pass
        logger.info("UDP Discovery Server listening on 0.0.0.0:9999")

    def datagram_received(self, data, addr):
        try:
            message = json.loads(data.decode())
            if message.get("action") == "DISCOVER":
                resolved_ip = self.configured_ip
                if not resolved_ip or resolved_ip in ("0.0.0.0", "localhost"):
                    resolved_ip = get_lan_ip(target_ip=addr[0])

                master_code = get_master_code(resolved_ip, self.master_port)
                logger.info(f"Received discovery request from {addr}. Responding with master IP {resolved_ip}:{self.master_port} (Code: {master_code})")
                
                # Respond with master details
                response = {
                    "action": "DISCOVER_RESPONSE",
                    "master_ip": resolved_ip,
                    "master_port": self.master_port,
                    "master_ws_port": self.master_port,
                    "master_code": master_code,
                    "registration_endpoint": f"ws://{resolved_ip}:{self.master_port}/ws/register"
                }
                self.transport.sendto(json.dumps(response).encode(), addr)
        except Exception as e:
            logger.error(f"Error handling UDP packet from {addr}: {e}")


async def start_discovery_server(master_ip: str, master_port: int, udp_port: int = 9999):
    try:
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: MasterDiscoveryProtocol(master_ip, master_port),
            local_addr=('0.0.0.0', udp_port)
        )
        return transport
    except Exception as e:
        logger.warning(f"Could not bind UDP discovery server on port {udp_port}: {e}")
        return None


