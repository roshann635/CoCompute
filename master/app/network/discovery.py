import asyncio
import json
import logging

logger = logging.getLogger(__name__)

class MasterDiscoveryProtocol(asyncio.DatagramProtocol):
    def __init__(self, master_ip: str, master_port: int):
        self.master_ip = master_ip
        self.master_port = master_port
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport
        logger.info(f"UDP Discovery Server listening on port 9999")

    def datagram_received(self, data, addr):
        try:
            message = json.loads(data.decode())
            if message.get("action") == "DISCOVER":
                logger.info(f"Received discovery request from {addr}")
                
                # Respond with master details
                response = {
                    "action": "DISCOVER_RESPONSE",
                    "master_ip": self.master_ip,
                    "master_ws_port": self.master_port,
                    "registration_endpoint": f"ws://{self.master_ip}:{self.master_port}/ws/register"
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
