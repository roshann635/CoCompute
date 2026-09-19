import asyncio
import json
import socket
import logging

logger = logging.getLogger(__name__)

class WorkerDiscoveryProtocol(asyncio.DatagramProtocol):
    def __init__(self, on_discovered_callback):
        self.on_discovered_callback = on_discovered_callback
        self.transport = None
        self.discovered = False

    def connection_made(self, transport):
        self.transport = transport
        
        # Enable broadcasting
        sock = self.transport.get_extra_info('socket')
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # Send initial broadcast
        self.send_discovery()

    def send_discovery(self):
        if not self.discovered:
            message = json.dumps({"action": "DISCOVER"}).encode()
            logger.info("Broadcasting discovery message to 255.255.255.255:9999 and local subnets...")
            # Global broadcast
            try:
                self.transport.sendto(message, ('255.255.255.255', 9999))
            except Exception as e:
                logger.debug(f"Global broadcast error: {e}")

            # Also attempt subnet targeted broadcasts for common lab LAN ranges
            for broadcast_ip in ['192.168.255.255', '192.168.79.255', '192.168.1.255', '192.168.0.255']:
                try:
                    self.transport.sendto(message, (broadcast_ip, 9999))
                except Exception:
                    pass

            # Retry after 3 seconds if not discovered
            asyncio.get_running_loop().call_later(3, self.send_discovery)

    def datagram_received(self, data, addr):
        try:
            message = json.loads(data.decode())
            if message.get("action") == "DISCOVER_RESPONSE":
                self.discovered = True
                master_ip = message.get("master_ip")
                master_ws_port = int(message.get("master_ws_port") or message.get("master_port", 8000))
                
                # Network resolution fix: check if master_ip is usable from LAN
                if not master_ip or master_ip in ("0.0.0.0", "127.0.0.1", "localhost"):
                    master_ip = addr[0]
                else:
                    try:
                        socket.gethostbyname(master_ip)
                    except (socket.gaierror, TypeError):
                        logger.warning(f"Unresolvable master IP received ('{master_ip}'). Falling back to sender's IP: {addr[0]}")
                        master_ip = addr[0]

                registration_endpoint = f"ws://{master_ip}:{master_ws_port}/ws/worker"
                logger.info(f"Discovered Master Node at {master_ip}:{master_ws_port}")
                
                if self.on_discovered_callback:
                    self.on_discovered_callback(master_ip, master_ws_port, registration_endpoint)
                
                self.transport.close()
                
        except Exception as e:
            logger.error(f"Error parsing discovery response: {e}")

    def error_received(self, exc):
        logger.error(f"UDP Error received: {exc}")


async def discover_master(udp_port: int = 9999, timeout: float = 8.0) -> tuple:
    """
    Broadcasts on the local network to find the master node.
    Returns (master_ip, master_port) tuple or raises TimeoutError if UDP broadcast fails.
    """
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    
    def on_discovered(ip, port, endpoint):
        if not future.done():
            future.set_result((ip, port))

    transport, protocol = await loop.create_datagram_endpoint(
        lambda: WorkerDiscoveryProtocol(on_discovered),
        local_addr=('0.0.0.0', 0),
        allow_broadcast=True
    )
    
    try:
        # Wait until master is discovered or timeout expires
        result = await asyncio.wait_for(future, timeout=timeout)
        return result
    except asyncio.TimeoutError:
        logger.warning(f"UDP auto-discovery timed out after {timeout} seconds (network switch may be dropping UDP broadcast).")
        raise
    finally:
        if not transport.is_closing():
            transport.close()

