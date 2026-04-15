import os
import asyncio
import logging
import time
import tempfile
from typing import Optional, Dict, Any
from core.grid_builder import build_pandapower_network
from core.data_writer import DataWriter
from core.modbus_manager import ModbusManager
from core.docker_manager import DockerManager
from core.st_generator import STGenerator
from core.provisioner import Provisioner
from core.modbus_server import TRINETRAModbusServer
from api.models import DeploymentPayload

logger = logging.getLogger("SimulationEngine")


class NTPListener(asyncio.DatagramProtocol):
    def __init__(self, engine):
        self.engine = engine

    def datagram_received(self, data, addr):
        if len(data) >= 48:
            logger.warning(f"Malicious UDP NTP payload received from {addr}! GPS Desync triggered.")
            self.engine.set_attack_state("atk13_gps_desync", True)

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
        # ── InfluxDB DataWriter + runtime state trackers ─────────────────────
        self.data_writer = DataWriter()
        self.ied_bus_map: Dict[str, int] = {}
        # attack_state is set via POST /api/attack/start (Step 7).
        # Every tick reads this dict to stamp is_under_attack + attack_type tags.
        self.attack_state: Dict[str, Any] = {
            "active": False, 
            "attack_type": "none",
            "grid_state": "NORMAL", 
            "attack_target": "none",
            "atk12_mitm_demo": {
                "enabled": False,
                "mode": "mask_trip",
                "voltage_scale": 1.08,
                "current_scale": 0.82,
            },
            "atk13_gps_desync": {
                "enabled": False
            }
        }
        self.ntp_transport = None
        self._topology_id: str = "default"
        self._health_tick_count: int = 0  # throttle system_health to every 10 ticks (5s)
        self.current_state = {
            "status": "offline",
            "voltage": 0.0,
            "current": 0.0,
            "breakers": {},
            "ied_health": {},
            "active_attacks": []
        }

    def set_attack_state(self, attack_id: str, enabled: bool, config: Optional[Dict[str, Any]] = None):
        """Enable or disable an in-simulator attack demo and sync with Historian."""
        if attack_id not in self.attack_state:
            raise ValueError(f"Unknown attack id: {attack_id}")

        self.attack_state[attack_id]["enabled"] = enabled
        if config:
            self.attack_state[attack_id].update(config)

        # ---- NEW: Sync with Historian Database Labels ----
        if enabled:
            # Mark the grid as under attack and tell the database the exact name (e.g. "atk12_mitm_demo")
            self.attack_state["active"] = True
            self.attack_state["attack_type"] = attack_id
            self.attack_state["grid_state"] = "UNDER_ATTACK"
        else:
            # Check if ANY attacks are still enabled before reverting to NORMAL
            # We explicitly ignore generic keys (like active, attack_type, etc.) and only check the attack objects (which are dicts with an "enabled" key)
            any_active = any(
                isinstance(v, dict) and v.get("enabled") 
                for k, v in self.attack_state.items()
            )
            if not any_active:
                self.attack_state["active"] = False
                self.attack_state["attack_type"] = "none"
                self.attack_state["grid_state"] = "NORMAL"

    def get_active_attacks(self):
        return [attack_id for attack_id, state in self.attack_state.items() if state.get("enabled")]

    def _apply_attack_demos(self, breaker_statuses: Dict[str, bool], scaled_v: int, scaled_i: int):
        """
        Apply simulator-only tampering effects so the UI can demonstrate attack
        behavior without performing a real MITM on the network.
        """
        outbound_breakers = dict(breaker_statuses)
        outbound_v = scaled_v
        outbound_i = scaled_i
        attack_notes = []

        atk12 = self.attack_state.get("atk12_mitm_demo", {})
        if atk12.get("enabled"):
            if atk12.get("mode") == "mask_trip":
                outbound_breakers = {breaker_id: False for breaker_id in breaker_statuses}

            outbound_v = max(0, int(scaled_v * float(atk12.get("voltage_scale", 1.08))))
            outbound_i = max(0, int(scaled_i * float(atk12.get("current_scale", 0.82))))
            attack_notes.append(
                "ATK-12 demo active: simulated MITM is falsifying breaker state and telemetry."
            )
            
        gps_offset = 0
        atk13 = self.attack_state.get("atk13_gps_desync", {})
        if atk13.get("enabled"):
            gps_offset = 3600 * 24 * 365 * 5  # Jump 5 years into the future!
            attack_notes.append(
                "ATK-13 (GPS Time Desync) active! Distance relay PMUs reporting contradictory time-vectors. Fault location impossible."
            )

        return outbound_breakers, outbound_v, outbound_i, attack_notes, gps_offset

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
        self.ied_bus_map = self.mappings.get("ied_bus_map", {})
        self._topology_id = str(payload.metadata.get("topology_id", f"run_{int(time.time())}"))
        logger.info(f"Session | topology_id='{self._topology_id}' | ied_bus_map={self.ied_bus_map}")

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
        
        # Start NTP listener for ATK-13
        loop = asyncio.get_event_loop()
        try:
            self.ntp_transport, _ = await loop.create_datagram_endpoint(
                lambda: NTPListener(self),
                local_addr=('0.0.0.0', 5123)
            )
            logger.info("NTP/GPS Time Simulator listening on UDP 5123")
        except Exception as e:
            logger.error(f"Failed to bind NTP listener: {e}")

    async def stop(self):
        """Stop simulation and cleanup Docker containers."""
        logger.info("Halt triggered: Cleaning up testbed...")
        self.is_running = False
        if self._task:
            self._task.cancel()
            self._task = None
            
        if hasattr(self, 'ntp_transport') and self.ntp_transport:
            self.ntp_transport.close()
            self.ntp_transport = None
            
        await self.modbus.disconnect_all()
        
        # Stop internal Modbus Server so port 5502 is freed
        self.mb_server.stop()
        
        # Stop IED containers asynchronously
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.docker.stop_all_ieds)
        
        # Flush pending InfluxDB writes (saves buffer to disk if DB is down)
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.data_writer.close)

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
        _tick_start = time.time()

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
                prev_state = bool(self.net.switch.at[switch_idx, 'closed'])
                
                if prev_state != is_closed:
                    # Safe assignment bypassing Pandas copy-on-write view bugs
                    new_col = self.net.switch['closed'].copy()
                    new_col.at[switch_idx] = is_closed
                    self.net.switch['closed'] = new_col
                    
                    if is_closed:
                        logger.info(f"BREAKER {breaker_id}: RECLOSED -> Switch closed -> Flow restored")
                    else:
                        logger.warning(f"BREAKER {breaker_id}: TRIPPED (PLC commanded) -> Switch open -> Flow severed")
                        
        # 3. SOLVE: Execute Power Flow
        import pandapower as pp
        import copy
        try:
            # Create a completely fresh memory block to bypass Windows/Numpy array locks
            temp_net = copy.deepcopy(self.net)
            # Use 'flat' initialization to force Pandapower to ignore any cached Read-Only results
            pp.runpp(temp_net, init="flat")
            
            # If successful, adopt the new network
            self.net = temp_net
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
                
            import math
            # 3. Scale up to integers for Modbus format
            scaled_v = int(vm_pu * 1000) if not math.isnan(vm_pu) else 0 # e.g. 1.0 pu -> 1000 (meaning 100.0%)
            scaled_i = int(current_ka * 1000) if not math.isnan(current_ka) else 0 # e.g. 0.25 kA -> 250 A
            telemetry_breakers, outbound_v, outbound_i, attack_notes, gps_offset = self._apply_attack_demos(
                breaker_statuses,
                scaled_v,
                scaled_i,
            )

            self.mb_server.update_voltage(vm_pu)
            self.mb_server.update_coil(0, True)
            
            # Write Physics to IED Modbus memory (with graceful error handling per IED)
            for ied in self.payload.scada_system.ieds:
                client = self.modbus.clients.get(ied.id)
                if client and client.connected:
                    try:
                        await client.write_registers(address=1024, values=[outbound_v, outbound_i], slave=1)
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

            # ── Dual-Source Readback + InfluxDB Write (per IED-Breaker control_mapping) ──
            tick_duration_ms = (time.time() - _tick_start) * 1000
            self._health_tick_count += 1
            write_health = (self._health_tick_count % 10 == 0)  # every 10 ticks ≈ 5 seconds

            # Grid-wide stats written to every row in the dataset
            total_load_mw = float(self.net.res_load.p_mw.sum()) if (hasattr(self.net, 'res_load') and not self.net.res_load.empty) else 0.0
            total_loss_mw = float(self.net.res_line.pl_mw.sum()) if (hasattr(self.net, 'res_line') and not self.net.res_line.empty) else 0.0
            total_gen_mw  = float(self.net.res_ext_grid.p_mw.sum()) if (hasattr(self.net, 'res_ext_grid') and not self.net.res_ext_grid.empty) else 0.0

            for mapping in self.payload.scada_system.control_mappings:
                ied_id     = mapping.ied_id
                breaker_id = mapping.breaker_id

                # ── A. Per-bus localized physics truth (Option B) ──────────────────
                bus_idx = self.ied_bus_map.get(ied_id, 0)
                try:
                    v_true    = float(self.net.res_bus.vm_pu.iloc[bus_idx])
                    vn_kv_ied = float(self.net.bus.vn_kv.iloc[bus_idx])
                except Exception:
                    v_true, vn_kv_ied = vm_pu, vn_kv  # fallback to global

                # ── B. Modbus read-back — what is in the IED register RIGHT NOW ──
                # Normal: matches what we wrote (v_true scaled to integer)
                # Under FDIA: attacker overwrote register → v_measured ≠ v_true
                v_measured           = v_true
                i_measured           = current_ka
                scan_count           = 0
                rtt_ms               = 0.0
                consecutive_timeouts = 0
                is_connected         = False

                client = self.modbus.clients.get(ied_id)
                if client and client.connected:
                    is_connected = True
                    t_read = time.time()
                    try:
                        # Read reg 1024 (voltage) + 1025 (current) back from IED
                        result = await client.read_holding_registers(
                            address=1024, count=2, slave=1
                        )
                        rtt_ms = (time.time() - t_read) * 1000
                        if not result.isError():
                            v_measured = result.registers[0] / 1000.0
                            i_measured = result.registers[1] / 1000.0
                    except Exception:
                        consecutive_timeouts += 1

                    try:
                        # Read %QW24 → Modbus holding register 24 → plc_scan_count
                        sc_result = await client.read_holding_registers(
                            address=24, count=1, slave=1
                        )
                        if not sc_result.isError():
                            scan_count = int(sc_result.registers[0])
                    except Exception:
                        pass

                # ── C. Breaker ground truth from Pandapower ──────────────────
                phys_closed = True
                sw_map = self.mappings.get("switch_map", {})
                if breaker_id in sw_map:
                    phys_closed = bool(self.net.switch.at[sw_map[breaker_id], 'closed'])
                plc_trip = bool(breaker_statuses.get(breaker_id, False))

                # ── D. Comms status classification ──────────────────────────
                if not is_connected:
                    comms_status = "OFFLINE"
                elif consecutive_timeouts > 3:
                    comms_status = "DEGRADED"
                else:
                    comms_status = "ONLINE"

                # ── E. Write to InfluxDB (enqueued — never blocks the tick loop) ──
                self.data_writer.write_telemetry(
                    ied_id=ied_id,
                    breaker_id=breaker_id,
                    topology_id=self._topology_id,
                    physics={
                        "vm_pu":      v_true,
                        "v_kv":       v_true * vn_kv_ied,
                        "i_ka":       current_ka,
                        "total_load": total_load_mw,
                        "total_loss": total_loss_mw,
                        "total_gen":  total_gen_mw,
                    },
                    cyber={
                        "vm_pu_measured": v_measured,
                        "i_ka_measured":  i_measured,
                        "scan_count":     scan_count,
                        "rtt_ms":         rtt_ms,
                    },
                    attack_state=self.attack_state,
                    breaker={"physical": phys_closed, "plc_cmd": plc_trip},
                    tick_duration_ms=tick_duration_ms,
                )

                # system_health written every 10 ticks ≈ 5 seconds (Docker stats are slow)
                if write_health:
                    self.data_writer.write_system_health(
                        ied_id=ied_id,
                        connected=is_connected,
                        consecutive_timeouts=consecutive_timeouts,
                        comms_status=comms_status,
                    )

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
                "breakers": telemetry_breakers,
                "ied_health": ied_health,
                "active_attacks": self.get_active_attacks(),
                "attack_notes": attack_notes,
                "reported_voltage_pu": round(outbound_v / 1000, 4),
                "reported_current_ka": round(outbound_i / 1000, 4),
                "gps_clock_offset": gps_offset,
            }
