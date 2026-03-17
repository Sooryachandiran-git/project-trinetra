import asyncio
import logging
from pymodbus.client import AsyncModbusTcpClient
from typing import Dict, List, Any, Optional

logger = logging.getLogger("ModbusManager")

class ModbusManager:
    """
    Manages asynchronous Modbus TCP connections to multiple IEDs (OpenPLC instances).
    Supports reading coils (breakers) and writing holding registers (sensors) 
    using the Multiplier Method for float-to-int conversion.
    """
    def __init__(self, multiplier: int = 100):
        self.clients: Dict[str, AsyncModbusTcpClient] = {}
        self.multiplier = multiplier

    async def connect_ied(self, ied_id: str, host: str, port: int) -> bool:
        """Initialize and connect to a specific IED. Returns True if successful."""
        if ied_id not in self.clients:
            logger.info(f"Connecting to IED {ied_id} at {host}:{port}")
            client = AsyncModbusTcpClient(host, port=port)
            success = await client.connect()
            self.clients[ied_id] = client
            return success
        return self.clients[ied_id].connected

    async def disconnect_all(self):
        """Gracefully close all active Modbus connections."""
        for ied_id, client in self.clients.items():
            logger.info(f"Disconnecting IED {ied_id}")
            client.close()
        self.clients.clear()

    async def read_breaker_status(self, ied_id: str, address: int = 0) -> bool:
        """
        Reads a Modbus Coil to determine if a breaker is CLOSED (True) or OPEN (False).
        Default OpenPLC address for the first coil is usually 0 (%QX0.0).
        """
        client = self.clients.get(ied_id)
        if not client or not client.connected:
            return False
        
        try:
            result = await client.read_coils(address, count=1)
            if not result.isError():
                return result.bits[0]
        except Exception as e:
            logger.error(f"Error reading breaker status from IED {ied_id}: {e}")
        
        return False

    async def write_sensor_value(self, ied_id: str, address: int, value: float):
        """
        Writes a float value to a Modbus Holding Register using the Multiplier Method.
        Value is multiplied by self.multiplier (default 100) and sent as a 16-bit integer.
        """
        client = self.clients.get(ied_id)
        if not client or not client.connected:
            return

        scaled_value = int(value * self.multiplier)
        try:
            # Holding Registers start at address 0 in many Modbus implementations
            await client.write_register(address, scaled_value)
        except Exception as e:
            logger.error(f"Error writing sensor value to IED {ied_id}: {e}")

    async def poll_all_breakers(self, mappings: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Given a list of control mappings (ied_id -> breaker_id), 
        polls all IEDs concurrently and returns a map of breaker statuses.
        """
        results = {}
        tasks = []

        async def poll_task(mapping):
            status = await self.read_breaker_status(mapping['ied_id'])
            results[mapping['breaker_id']] = status

        for mapping in mappings:
            tasks.append(poll_task(mapping))

        if tasks:
            await asyncio.gather(*tasks)
        
        return results
