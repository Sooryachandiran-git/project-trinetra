import os

filepath = r"e:\Projects\project-trinetra\backend-orchestrator\core\simulation_engine.py"
with open(filepath, "r") as f:
    code = f.read()

# 1. Add NTPListener
listener_code = """
class NTPListener(asyncio.DatagramProtocol):
    def __init__(self, engine):
        self.engine = engine

    def datagram_received(self, data, addr):
        if len(data) >= 48:
            logger.warning(f"Malicious UDP NTP payload received from {addr}! GPS Desync triggered.")
            self.engine.set_attack_state("atk13_gps_desync", True)

class SimulationEngine:"""
code = code.replace("class SimulationEngine:", listener_code)

# 2. Register attack state
old_state = """        self.attack_state = {
            "atk12_mitm_demo": {
                "enabled": False,
                "mode": "mask_trip",
                "voltage_scale": 1.08,
                "current_scale": 0.82,
            }
        }"""
new_state = """        self.attack_state = {
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
        self.ntp_transport = None"""
code = code.replace(old_state, new_state)

# 3. Add listener start
old_start = """        self.is_running = True
        self._task = asyncio.create_task(self._run_loop())"""
new_start = """        self.is_running = True
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
            logger.error(f"Failed to bind NTP listener: {e}")"""
code = code.replace(old_start, new_start)

# 4. Add listener stop
old_stop = """        self.is_running = False
        if self._task:
            self._task.cancel()
            self._task = None"""
new_stop = """        self.is_running = False
        if self._task:
            self._task.cancel()
            self._task = None
            
        if hasattr(self, 'ntp_transport') and self.ntp_transport:
            self.ntp_transport.close()
            self.ntp_transport = None"""
code = code.replace(old_stop, new_stop)

# 5. Add UI notes
old_notes = """            outbound_i = max(0, int(scaled_i * float(atk12.get("current_scale", 0.82))))
            attack_notes.append(
                "ATK-12 demo active: simulated MITM is falsifying breaker state and telemetry."
            )"""
new_notes = """            outbound_i = max(0, int(scaled_i * float(atk12.get("current_scale", 0.82))))
            attack_notes.append(
                "ATK-12 demo active: simulated MITM is falsifying breaker state and telemetry."
            )
            
        atk13 = self.attack_state.get("atk13_gps_desync", {})
        if atk13.get("enabled"):
            attack_notes.append(
                "ATK-13 (GPS Time Desync) active! Distance relay PMUs reporting contradictory time-vectors. Fault location impossible."
            )"""
code = code.replace(old_notes, new_notes)

with open(filepath, "w") as f:
    f.write(code)

print("Patch applied to simulation_engine.py successfully!")
