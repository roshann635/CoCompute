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
                
                # Network resolution fix: check if master_ip is resolvable. If not, use sender's IP addr[0].
                try:
                    if master_ip:
                        socket.gethostbyname(master_ip)
                    else:
                        master_ip = addr[0]
                except (socket.gaierror, TypeError):
                    logger.warning(f"Unresolvable master IP received ('{master_ip}'). Falling back to sender's IP: {addr[0]}")
                    master_ip = addr[0]

                master_ws_port = message.get("master_ws_port")
                registration_endpoint = f"ws://{master_ip}:{master_ws_port}/ws/worker/{WORKER_UID}" if "WORKER_UID" in globals() else message.get("registration_endpoint")
                
                logger.info(f"Discovered Master Node at {master_ip}:{master_ws_port}")
                
                if self.on_discovered_callback:
                    # Trigger the callback to proceed with registration
                    self.on_discovered_callback(master_ip, master_ws_port, registration_endpoint)
                
                # Close the transport as we don't need UDP anymore
                self.transport.close()
                
        except Exception as e:
            logger.error(f"Error parsing discovery response: {e}")

    def error_received(self, exc):
        logger.error(f"UDP Error received: {exc}")

async def discover_master(udp_port: int = 9999, timeout: float = 8.0) -> dict:
    """
    Broadcasts on the local network to find the master node.
    Returns a dictionary with master details or raises TimeoutError if UDP broadcast fails.
    """
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    
    def on_discovered(ip, port, endpoint):
        if not future.done():
            future.set_result({
                "master_ip": ip,
                "master_ws_port": port,
                "registration_endpoint": endpoint
            })

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
