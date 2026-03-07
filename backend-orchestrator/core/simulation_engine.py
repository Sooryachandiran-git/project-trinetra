import os
import asyncio
import logging
import time
from typing import Optional, Dict, Any
from core.grid_builder import build_pandapower_network
from core.modbus_manager import ModbusManager
from core.docker_manager import DockerManager
from core.st_generator import STGenerator
from core.provisioner import Provisioner
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
        self.docker = DockerManager()
        self.st_gen = STGenerator()
        self.prov = Provisioner(self.docker)
        
        self.is_running = False
        self.tick_rate = 0.5  # 500ms target
        self._task: Optional[asyncio.Task] = None
        self.mappings = {}

    async def start(self, payload: DeploymentPayload):
        """Initialize containers, provision logic, and start the polling loop."""
        if self.is_running:
            await self.stop()

        logger.info("Initializing Dynamic Orchestrator...")
        self.payload = payload
        
        # 1. Start Docker containers for IEDs & Provision logic
        for ied in payload.scada_system.ieds:
            # Generate Web Port (e.g., 8080 + IED offset)
            web_port = 8080 + payload.scada_system.ieds.index(ied)
            
            # Launch container
            if self.docker.run_ied(ied.id, ied.port, web_port):
                controlled_breakers = [
                    m.breaker_id for m in payload.scada_system.control_mappings 
                    if m.ied_id == ied.id
                ]
                
                # Check for custom ST code from the UI
                if ied.st_code:
                    logger.info(f"IED {ied.id}: Using custom ST code from UI.")
                    st_path = os.path.join(self.st_gen.output_dir, f"ied_{ied.id}_custom.st")
                    with open(st_path, "w") as f:
                        f.write(ied.st_code)
                else:
                    st_path = self.st_gen.generate_st(ied.id, controlled_breakers)
                
                await self.prov.provision_ied(ied.id, st_path, web_port)
            
        # 2. Initialize Pandapower net
        self.net, diagnostics = build_pandapower_network(payload)
        self.mappings = diagnostics.get("mappings", {})

        # 3. Connect to all IEDs via Modbus
        # Provisioning already waited ~22s for PLC compilation + 3s for start.
        # Give it a few more seconds for the Modbus server to come up.
        logger.info("Waiting 5s for PLC Modbus servers to become ready...")
        await asyncio.sleep(5)

        for ied in payload.scada_system.ieds:
            await self.modbus.connect_ied(ied.id, "127.0.0.1", ied.port)
            logger.info(f"Modbus connected to IED {ied.id} on port {ied.port}")

        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """Stop simulation and cleanup Docker containers."""
        logger.info("Halt triggered: Cleaning up testbed...")
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        await self.modbus.disconnect_all()
        self.docker.stop_all_ieds()
        
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
            logger.info("--- Physics Tick: Power Flow Converged ---")
        except Exception as e:
            logger.warning(f"Power flow failed to converge (possibly islanded): {e}")

        # 4. WRITE: Update IED sensors (e.g., Bus Voltages)
        if hasattr(self.net, 'res_bus') and not self.net.res_bus.empty:
            voltage = self.net.res_bus.vm_pu.iloc[0]
            for ied in self.payload.scada_system.ieds:
                # Write to register 0 (raw voltage * multiplier for PLC logic)
                await self.modbus.write_sensor_value(ied.id, 0, voltage)
                logger.info(f"Cyber Tick: Wrote Voltage {voltage:.4f} pu to IED {ied.id}")
