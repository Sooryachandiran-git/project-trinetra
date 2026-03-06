# Milestone 3: The Cyber-Physical Bridge (Modbus & Physics Integration)

**Date:** March 6, 2026
**Status:** Completed

## ⚡ Summary of Accomplishments

In this milestone, we moved beyond the "look and feel" of the project and implemented the core intelligence: the **Cyber-Physical Tick**. We built the infrastructure that allows a cyber-control layer (Modbus/OpenPLC) to actually change the behavior of a physical power grid in real-time.

### 1. The Modbus Manager (`modbus_manager.py`)
- Built an asynchronous communication layer using `pymodbus`.
- **Concurrency:** Designed the manager to poll multiple IEDs simultaneously using `asyncio.gather`, ensuring we don't exceed our 500ms real-time tick budget.
- **Protocol Translation:** Implemented the "Multiplier Method" to solve the challenge of sending decimal physics values (Voltages) over integer-only Modbus registers.

### 2. The Simulation Engine (`simulation_engine.py`)
- Created a background "Tick" that acts as the heartbeat of the digital twin.
- **Topology Sync:** Implemented logic that translates a Modbus Coil toggle (a Relay trip) into a physical isolation event in the electrical grid.
- **Convergence Guard:** Wrapped the physics solver in protective logic to prevent the server from crashing during "Islanding" (mathematical non-convergence).

### 3. API Expansion (`main.py`)
- Integrated the Simulation Engine into the FastAPI lifecycle.
- **Dynamic Startup:** The `/api/deploy` endpoint now non-blockingly spawns the background simulation thread.
- **Graceful Shutdown:** Implemented a `/api/stop` endpoint to clean up network sockets and stop background threads.

---

## 🧠 Interview Guide: "The Cyber-Physical Bridge"

This section breaks down the complex engineering concepts we implemented—perfect for an interview or technical presentation.

### Concept 1: The "Cyber-Physical Tick" Loop
**Interview Context:** *"How do you synchronize two systems that run at different speeds?"*

In a Digital Twin, you have two "clocks": the Cyber clock (PLC) and the Physics clock (Grid Solver). We synchronized them using a **Polling Loop**.

```python
# The Sim Loop
while is_running:
    start_time = time.time()
    
    # 1. Capture the 'Cyber' intent (Are breakers open?)
    states = await modbus.read_coils()
    
    # 2. Update the 'Physical' world
    net.line.at[0, 'in_service'] = states[0]
    pp.runpp(net) # The Physics Brain
    
    # 3. Provide 'Cyber' feedback (What is the new voltage?)
    await modbus.write_registers(net.res_bus.vm_pu.iloc[0] * 100)
    
    # Wait for the next 500ms beat
    await asyncio.sleep(0.5 - (time.time() - start_time))
```

### Concept 2: The Multiplier Method (Float vs. Integer)
**Interview Context:** *"Modbus Holding Registers are only 16-bit integers. How do you send a voltage like 1.052 kV?"*

**The Problem:** Computers use "Floating Point" (Decimals), but industrial hardware often uses "Integers" (Whole Numbers) for speed and simplicity.
**The Solution:** We use a **Fixed-Point Multiplier**. 
- **Physics Value:** 1.052
- **Multiplier:** 100
- **Modbus Value:** 105 (Sent as an integer)
- **Decoding:** The PLC receives 105, divides by 100, and gets 1.05 back.

### Concept 3: Handling Convergence Errors (Physics Resilience)
**Interview Context:** *"What happens to your twin if the grid becomes unstable or a blackout occurs?"*

In Pandapower, if a load is completely disconnected, the math crashes because there is no solution (Infinite Impedance). 
**Our Implementation:**
```python
try:
    pp.runpp(self.net)
except Exception:
    # We catch the 'Crash' and tell the logs it's an islanding event
    logger.warning("Island detected. Physics is offline but Backend stays alive.")
```
**Why it matters:** In a research project, you want to study the attack, not have your server die because the math got hard!

### Concept 4: Asynchronous I/O (`asyncio`)
**Interview Context:** *"Why use Python for a real-time SCADA system?"*

Python isn't "fast" in terms of raw math, but it is **excellent** at "waiting." By using `asyncio`, we fire off 50 Modbus requests at the same time and wait for them all to return in parallel. This allows us to scale to massive grids without lagging the 500ms tick.

---

**Next Milestone:** Phase 3 — Automating Docker Orchestration and ST Logic Injection.
