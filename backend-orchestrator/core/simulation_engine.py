import os
import asyncio
import logging
import time
import tempfile
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
        self.current_state = {
            "status": "offline",
            "voltage": 0.0,
            "current": 0.0,
            "breakers": {},
            "ied_health": {}
        }

    async def start(self, payload: DeploymentPayload):
        """Initialize containers, provision logic, and start the polling loop."""
        if self.is_running:
            await self.stop()

        logger.info("Initializing Dynamic Orchestrator...")
        self.payload = payload
        
        # 1. Start Docker containers for IEDs & Provision logic
        if not self.docker.client:
            logger.error("DOCKER CLIENT MISSING: Cannot launch containers. Is Docker running?")
            
        for ied in payload.scada_system.ieds:
            web_port = 8090 + payload.scada_system.ieds.index(ied)
            
            # Launch container
            if self.docker.run_ied(ied.id, ied.port, web_port):
                controlled_breakers = [
                    m.breaker_id for m in payload.scada_system.control_mappings 
                    if m.ied_id == ied.id
                ]
                
                if ied.st_code:
                    logger.info(f"IED {ied.id}: Using custom ST code from payload.")
                    st_path = os.path.join(tempfile.gettempdir(), f"ied_{ied.id}_custom.st")
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
        if payload.scada_system.ieds:
            logger.info("Waiting 5s for PLC Modbus servers to become ready...")
            await asyncio.sleep(5)

            for ied in payload.scada_system.ieds:
                success = await self.modbus.connect_ied(ied.id, "127.0.0.1", ied.port)
                if success:
                    logger.info(f"Modbus connected to IED {ied.id} on port {ied.port}")
                else:
                    logger.error(f"FAILED to connect Modbus to IED {ied.id} on port {ied.port}")

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
            # 1. Gather true base values
            vm_pu = float(self.net.res_bus.vm_pu.iloc[0])
            vn_kv = float(self.net.bus.vn_kv.iloc[0])
            
            # 2. Get mathematically accurate Current (kA)
            current_ka = 0.0 
            if hasattr(self.net, 'res_line') and not self.net.res_line.empty:
                current_ka = float(self.net.res_line.i_ka.iloc[0])
            elif hasattr(self.net, 'res_ext_grid') and not self.net.res_ext_grid.empty:
                # If there are no transmission lines (Ext Grid attached directly to Bus with Load)
                # Calculate current from S_mva draw
                p_mw = abs(float(self.net.res_ext_grid.p_mw.iloc[0]))
                q_mvar = abs(float(self.net.res_ext_grid.q_mvar.iloc[0]))
                s_mva = (p_mw**2 + q_mvar**2)**0.5
                v_mag = 1.732 * vn_kv * vm_pu
                current_ka = s_mva / v_mag if v_mag > 0 else 0.0
                
            # 3. Scale up to integers for Modbus format
            scaled_v = int(vm_pu * 1000) # e.g. 1.0 pu -> 1000 (meaning 100.0%)
            scaled_i = int(current_ka * 1000) # e.g. 0.25 kA -> 250 A
            
            self.mb_server.update_voltage(vm_pu)
            self.mb_server.update_coil(0, True)
            
            # Write Physics to IED Modbus memory (with graceful error handling per IED)
            for ied in self.payload.scada_system.ieds:
                client = self.modbus.clients.get(ied.id)
                if client and client.connected:
                    try:
                        await client.write_registers(address=1024, values=[scaled_v, scaled_i], slave=1)
                    except Exception as write_err:
                        logger.warning(f"Write failed for IED {ied.id}: {write_err}. Attempting reconnect...")
                        try:
                            await client.connect()
                        except Exception:
                            pass
                elif client and not client.connected:
                    # Client exists but dropped — try to reconnect silently
                    try:
                        await client.connect()
                        logger.info(f"IED {ied.id}: Reconnected to Modbus.")
                    except Exception:
                        pass  # Will retry next tick
                # else: no client yet (still provisioning), silently skip
            
            # 5. Clean Console Telemetry Reporting
            breaker_count = len(self.net.switch) if hasattr(self.net, 'switch') else 0
            any_open = any(v for v in breaker_statuses.values()) if breaker_statuses else False
            
            log_str = f"Physics: V={vm_pu:.4f} pu, I={current_ka:.4f} kA | Breakers: {breaker_count} (Tripped: {sum(v for v in breaker_statuses.values())})"
            if any_open:
                logger.warning(f"{log_str} [GRID FAULT - RELAY TRIPPED]")
            else:
                logger.info(f"{log_str} [GRID NOMINAL]")
            
            # 6. Save the global state for the React SSE Telemetry Stream
            ied_health = {}
            for ied in self.payload.scada_system.ieds:
                if hasattr(self.modbus, 'clients') and ied.id in self.modbus.clients:
                    ied_health[ied.id] = self.modbus.clients[ied.id].connected
                else:
                    ied_health[ied.id] = False

            self.current_state = {
                "status": "running" if self.is_running else "offline",
                "voltage_pu": round(vm_pu, 4),
                "voltage_kv": round(vm_pu * vn_kv, 2),
                "current_ka": round(current_ka, 4),
                "breakers": breaker_statuses,
                "ied_health": ied_health
            }
