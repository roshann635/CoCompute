import asyncio
import json
import logging
import socket

logger = logging.getLogger(__name__)


def get_lan_ip() -> str:
    """Determine the LAN IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


class MasterDiscoveryProtocol(asyncio.DatagramProtocol):
    def __init__(self, master_ip: str, master_port: int):
        self.configured_ip = master_ip
        self.master_port = master_port
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        logger.info("UDP Discovery Server listening on 0.0.0.0:9999")

    def datagram_received(self, data, addr):
        try:
            message = json.loads(data.decode())
            if message.get("action") == "DISCOVER":
                resolved_ip = self.configured_ip
                if not resolved_ip or resolved_ip in ("0.0.0.0", "127.0.0.1", "localhost"):
                    resolved_ip = get_lan_ip()

                logger.info(f"Received discovery request from {addr}. Responding with master IP {resolved_ip}:{self.master_port}")
                
                # Respond with master details
                response = {
                    "action": "DISCOVER_RESPONSE",
                    "master_ip": resolved_ip,
                    "master_port": self.master_port,
                    "master_ws_port": self.master_port,
                    "registration_endpoint": f"ws://{resolved_ip}:{self.master_port}/ws/register"
                }
                self.transport.sendto(json.dumps(response).encode(), addr)
        except Exception as e:
            logger.error(f"Error handling UDP packet from {addr}: {e}")


async def start_discovery_server(master_ip: str, master_port: int, udp_port: int = 9999):
    loop = asyncio.get_running_loop()
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: MasterDiscoveryProtocol(master_ip, master_port),
        local_addr=('0.0.0.0', udp_port)
    )
    return transport
