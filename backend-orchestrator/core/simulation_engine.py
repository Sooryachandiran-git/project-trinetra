import asyncio
import logging
import time
from typing import Optional, Dict, Any
from core.grid_builder import build_pandapower_network
from core.modbus_manager import ModbusManager
from api.models import DeploymentPayload

logger = logging.getLogger("SimulationEngine")

class SimulationEngine:
    """
    The heart of the TRINETRA digital twin. 
    Performs the Cyber-Physical Tick loop: 
    Polls IEDs -> Updates Physics -> Solves Grid -> Updates IEDs.
    """
    def __init__(self):
        self.payload: Optional[DeploymentPayload] = None
        self.net = None
        self.modbus = ModbusManager()
        self.is_running = False
        self.tick_rate = 0.5  # 500ms target
        self._task: Optional[asyncio.Task] = None

    async def start(self, payload: DeploymentPayload):
        """Initialize the grid and start the background simulation task."""
        if self.is_running:
            await self.stop()

        logger.info("Starting Simulation Engine...")
        self.payload = payload
        
        # 1. Initialize Pandapower net and store internal mappings
        self.net, diagnostics = build_pandapower_network(payload)
        self.mappings = diagnostics.get("mappings", {})
        
        # 2. Connect to all defined IEDs
        for ied in payload.scada_system.ieds:
            await self.modbus.connect_ied(ied.id, "127.0.0.1", ied.port)

        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """Stop the loop and disconnect Modbus clients."""
        logger.info("Stopping Simulation Engine...")
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        await self.modbus.disconnect_all()
        self.net = None
        self.payload = None

    async def _run_loop(self):
        """The main polling loop."""
        while self.is_running:
            start_time = time.time()
            
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"Error during simulation tick: {e}")

            # Sleep to maintain the tick rate
            elapsed = time.time() - start_time
            sleep_time = max(0, self.tick_rate - elapsed)
            await asyncio.sleep(sleep_time)

    async def _tick(self):
        """A single iteration of the Cyber-Physical bridge."""
        if not self.net or not self.payload:
            return

        # 1. READ: Get breaker statuses from IEDs
        mappings = [
            {"ied_id": m.ied_id, "breaker_id": m.breaker_id} 
            for m in self.payload.scada_system.control_mappings
        ]
        
        breaker_statuses = await self.modbus.poll_all_breakers(mappings)
        
        # 2. SYNC TO PHYSICS: Update Pandapower line states based on breakers
        line_map = self.mappings.get("line_map", {})
        
        for breaker_id, is_closed in breaker_statuses.items():
            # A breaker (switch node) is OPEN (False) or CLOSED (True).
            # We find any lines connected to this breaker node.
            for line_node in self.payload.electrical_grid.lines:
                if line_node.from_node == breaker_id or line_node.to_node == breaker_id:
                    if line_node.id in line_map:
                        line_idx = line_map[line_node.id]
                        
                        # Sync state: Breaker Open -> Line out of service
                        self.net.line.at[line_idx, 'in_service'] = is_closed
                        
        # 3. SOLVE: Execute Power Flow
        import pandapower as pp
        try:
            pp.runpp(self.net)
        except Exception as e:
            logger.warning(f"Power flow failed to converge (possibly islanded): {e}")

        # 4. WRITE: Update IED sensors (e.g., Bus Voltages)
        # In a real setup, we'd map specific bus voltages to specific registers
        if hasattr(self.net, 'res_bus') and not self.net.res_bus.empty:
            for ied in self.payload.scada_system.ieds:
                # For demo, just write the first bus voltage (multiplied)
                voltage = self.net.res_bus.vm_pu.iloc[0]
                await self.modbus.write_sensor_value(ied.id, 0, voltage)
