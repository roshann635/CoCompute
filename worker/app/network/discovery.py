import asyncio
import json
import socket
import logging
import ipaddress
try:
    import psutil
except ImportError:
    psutil = None

logger = logging.getLogger(__name__)


def get_all_broadcast_addresses() -> list[str]:
    """Dynamically determine all broadcast and direct candidate addresses for local interfaces."""
    addrs = set(["255.255.255.255", "127.0.0.1"])
    
    # Common subnet fallback broadcasts
    for fallback in ["192.168.1.255", "192.168.0.255", "192.168.72.255", "192.168.76.255", "192.168.79.255", "10.0.0.255", "10.10.31.255"]:
        addrs.add(fallback)

    if psutil:
        try:
            for iface, snics in psutil.net_if_addrs().items():
                for snic in snics:
                    if snic.family == socket.AF_INET and snic.address:
                        if not snic.address.startswith("127."):
                            addrs.add(snic.address)
                        if snic.broadcast:
                            addrs.add(snic.broadcast)
                        elif snic.netmask and not snic.address.startswith("127."):
                            try:
                                net = ipaddress.IPv4Network(f"{snic.address}/{snic.netmask}", strict=False)
                                addrs.add(str(net.broadcast_address))
                            except Exception:
                                pass
        except Exception as e:
            logger.debug(f"Error computing dynamic broadcast addresses: {e}")

    return list(addrs)


class MasterEndpoint(tuple):
    """2-tuple (ip, port) with optional .code attribute for backward compatibility."""
    def __new__(cls, ip: str, port: int, code: str = None):
        inst = super().__new__(cls, (ip, port))
        inst.ip = ip
        inst.port = port
        inst.code = code
        return inst


class WorkerDiscoveryProtocol(asyncio.DatagramProtocol):
    def __init__(self, on_discovered_callback):
        self.on_discovered_callback = on_discovered_callback
        self.transport = None
        self.discovered = False
        self.broadcast_addrs = get_all_broadcast_addresses()

    def connection_made(self, transport):
        self.transport = transport
        try:
            sock = self.transport.get_extra_info('socket')
            if sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except Exception:
            pass
        
        # Send initial broadcast
        self.send_discovery()

    def send_discovery(self):
        if not self.discovered and self.transport and not self.transport.is_closing():
            message = json.dumps({"action": "DISCOVER"}).encode()
            logger.info("Broadcasting discovery message to local network on port 9999...")

            for b_ip in self.broadcast_addrs:
                try:
                    self.transport.sendto(message, (b_ip, 9999))
                except Exception:
                    pass

            # Retry every 1.0s until discovered
            asyncio.get_running_loop().call_later(1.0, self.send_discovery)


    def datagram_received(self, data, addr):
        try:
            message = json.loads(data.decode())
            if message.get("action") == "DISCOVER_RESPONSE":
                self.discovered = True
                master_ip = message.get("master_ip")
                master_ws_port = int(message.get("master_ws_port") or message.get("master_port", 8000))
                master_code = message.get("master_code")
                
                # If master returned 0.0.0.0 or unresolvable, use sender IP
                if not master_ip or master_ip in ("0.0.0.0", "localhost"):
                    master_ip = addr[0]
                elif master_ip == "127.0.0.1" and not addr[0].startswith("127."):
                    # Master thinks it is 127.0.0.1 but worker reached it via LAN
                    master_ip = addr[0]
                else:
                    try:
                        socket.gethostbyname(master_ip)
                    except (socket.gaierror, TypeError):
                        logger.warning(f"Unresolvable master IP received ('{master_ip}'). Using sender IP: {addr[0]}")
                        master_ip = addr[0]

                registration_endpoint = f"ws://{master_ip}:{master_ws_port}/ws/worker"
                logger.info(f"Discovered Master Node at {master_ip}:{master_ws_port} (Code: {master_code or 'N/A'})")
                
                if self.on_discovered_callback:
                    endpoint_obj = MasterEndpoint(master_ip, master_ws_port, master_code)
                    self.on_discovered_callback(endpoint_obj, registration_endpoint)
                
                if self.transport and not self.transport.is_closing():
                    self.transport.close()
                
        except Exception as e:
            logger.error(f"Error parsing discovery response: {e}")

    def error_received(self, exc):
        logger.debug(f"UDP Error received: {exc}")


async def discover_master(udp_port: int = 9999, timeout: float = 6.0) -> MasterEndpoint:
    """
    Broadcasts on the local network to find the master node.
    Returns MasterEndpoint(master_ip, master_port, master_code) or raises TimeoutError if UDP broadcast fails.
    """
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    
    def on_discovered(endpoint_obj, endpoint_url):
        if not future.done():
            future.set_result(endpoint_obj)

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
        logger.info(f"UDP auto-discovery timed out after {timeout}s (broadcast may be filtered on this network).")
        raise
    finally:
        if transport and not transport.is_closing():
            transport.close()


