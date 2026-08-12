"""
CoCompute Shared Network Protocol Definitions.
Contains standard action names, message types, and key names.
"""

# Message Types (Actions)
ACTION_DISCOVER = "DISCOVER"
ACTION_DISCOVER_RESPONSE = "DISCOVER_RESPONSE"
ACTION_REGISTER = "REGISTER"
ACTION_HEARTBEAT = "HEARTBEAT"
ACTION_METRICS = "METRICS"
ACTION_EXECUTE = "EXECUTE"
ACTION_RESULT = "RESULT"

# Worker states
STATE_ONLINE = "online"
STATE_OFFLINE = "offline"
STATE_BUSY = "busy"

# Defaults
DEFAULT_UDP_PORT = 9999
DEFAULT_HTTP_PORT = 8000
