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
from core.modbus_server import TRINETRAModbusServer
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
        # Internal Modbus server that OpenPLC polls FROM
        self.mb_server = TRINETRAModbusServer(port=5502)
        self.mb_server.start()
        
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
                
                if ied.st_code:
                    logger.info(f"IED {ied.id}: Using custom ST code from payload.")
                    st_path = os.path.join("/tmp", f"ied_{ied.id}_custom.st")
                    with open(st_path, "w") as f:
                        f.write(ied.st_code)
                else:
                    logger.info(f"IED {ied.id}: Falling back to dynamically generated ST code.")
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
            self._task = None
            
        await self.modbus.disconnect_all()
        
        # Stop internal Modbus Server so port 5502 is freed
        self.mb_server.stop()
        
        # Stop IED containers asynchronously
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.docker.stop_all_ieds)
        
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
        
        # 2. SYNC TO PHYSICS: Update Pandapower switch states based on PLC breaker coil outputs
        switch_map = self.mappings.get("switch_map", {})
        
        for breaker_id, trip_command_active in breaker_statuses.items():
            # In the user's ST code, %QX0.0 is 'Trip_Command'.
            # If TRUE -> the breaker should OPEN. If FALSE -> the breaker should CLOSE.
            is_closed = not trip_command_active
            
            if breaker_id in switch_map:
                switch_idx = switch_map[breaker_id]
                prev_state = self.net.switch.at[switch_idx, 'closed']
                self.net.switch.at[switch_idx, 'closed'] = is_closed
                
                if prev_state != is_closed:
                    if is_closed:
                        logger.info(f"BREAKER {breaker_id}: RECLOSED -> Switch closed -> Flow restored")
                    else:
                        logger.warning(f"BREAKER {breaker_id}: TRIPPED (PLC commanded) -> Switch open -> Flow severed")
                        
        # 3. SOLVE: Execute Power Flow
        import pandapower as pp
        try:
            pp.runpp(self.net)
            logger.info("--- Physics Tick: Power Flow Converged ---")
        except Exception as e:
            logger.warning(f"Power flow failed to converge (possibly islanded): {e}")

        # 4. WRITE: Update IED sensors and report voltage
        if hasattr(self.net, 'res_bus') and not self.net.res_bus.empty:
            voltage = self.net.res_bus.vm_pu.iloc[0] * 230  # Actual Voltage (e.g., 230V)
            
            # Get current from the first line (if exists), else default to safe value
            current = 15.20 
            if hasattr(self.net, 'res_line') and not self.net.res_line.empty:
                current = self.net.res_line.i_ka.iloc[0] * 1000 # Actual Current in Amps
                
            # Scale up to remove decimals for Modbus 16-bit Integer
            scaled_v = int(voltage * 100)
            scaled_i = int(current * 100)
            
            # Write to TRINETRA Modbus server (for Slave Device integration)
            self.mb_server.update_voltage(voltage)
            self.mb_server.update_coil(0, True)
            
            # Write Voltage and Current to IED Modbus holding registers (Address 0 and 1)
            for ied in self.payload.scada_system.ieds:
                # Write multiple registers: [Voltage, Current]
                if hasattr(self.modbus, 'clients') and ied.id in self.modbus.clients:
                    await self.modbus.clients[ied.id].write_registers(address=0, values=[scaled_v, scaled_i], slave=1)
                else:
                    logger.warning(f"Could not write V/I to IED {ied.id}: client not found.")
            
            # Report physics state with trip context
            any_open = any(v for v in breaker_statuses.values()) if breaker_statuses else False
            if any_open:
                logger.warning(f"Physics: Voltage={voltage:.4f} pu [BREAKER TRIPPED - PLC protection relay OPEN]")
            else:
                logger.info(f"Physics: Voltage={voltage:.4f} pu | Breaker CLOSED | Grid Normal")
