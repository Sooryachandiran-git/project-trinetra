# Milestone 4: The Dynamic Orchestrator (Docker & Auto-Provisioning)

**Date:** March 6, 2026
**Status:** Completed

## ⚡ Summary of Accomplishments

Milestone 4 marks the transition from a manual simulation to a fully automated, elastic testbed. We have implemented the "Orchestration Layer" which manages the containerized lifecycle of the Cyber-Physical components.

### 1. Docker Automation (`docker_manager.py`)
- Integrated the official **Docker Python SDK**.
- **On-Demand IEDs:** The backend now automatically spins up an isolated OpenPLC Docker container for every IED node you add to the React canvas.
- **Dynamic Port Mapping:** Maps the internal Modbus (502) and Web (8080) ports of containers to high-range ports on your host machine automatically.

### 2. Auto-ST Logic Generator (`st_generator.py`)
- Created a "Code Factory" for **Structured Text (IEC 61131-3)**.
- **Topology Mapping:** The generator analyzes which Breakers an IED is connected to and generates unique Modbus register mappings in real-time.
- **Template Logic:** Dynamically creates `PROGRAM` and `CONFIGURATION` blocks that OpenPLC can compile.

### 3. The Provisioner Engine (`provisioner.py`)
- Implemented **Logic Injection**. 
- It "hot-swaps" the PLC program inside the running container using `docker exec` commands, effectively "flashing" the IED from the web dashboard.

### 4. Full System Integration
- Updated the `SimulationEngine` to orchestrate this entire sequence:
    1. **Pre-Flight:** Stop all old containers.
    2. **Orchestration:** Launch new containers for the specific grid topology.
    3. **Provisioning:** Inject generated ST code.
    4. **Connection:** Wait for boot-up and connect via Modbus.
    5. **Tick:** Start the real-time simulation loop.

---

## 🧠 Interview Guide: "The Orchestrator & Containerization"

This milestone demonstrates advanced "DevOps for ICS" (Industrial Control Systems) concepts.

### Concept 1: Infrastructure as Code (IaC) for SCADA
**Interview Context:** *"How do you make your SCADA lab scaleable?"*

Instead of manually configuring IP addresses and ports for 50 PLCs, we treated the PLCs as **Infrastructure**. Our backend is the "Orchestrator" (like a mini-Kubernetes) that defines the environment based on the user's visual drawing.

### Concept 2: Logic Injection & Provisioning
**Interview Context:** *"How do you update the logic on a running PLC without manual intervention?"*

We used a technique called **Direct File Injection**. By writing the `.st` file directly into the container's script directory and triggering a reload, we bypassed the manual Web UI, allowing for mass-updates across many IEDs simultaneously.

### Concept 3: Dynamic Port Mapping
**Interview Context:** *"How do 5 containers all listen on Modbus port 502 without colliding?"*

**The Problem:** Every PLC wants port 502.
**The Solution:** We used **Docker Bridge Mapping**. 
- Container 1: `502 -> 5021`
- Container 2: `502 -> 5022`
The backend keeps track of this mapping so the Simulation Engine knows exactly which high-range port leads to which virtual IED.

---

**Final Status:** The TRINETRA testbed is now fully automated. Deploying a grid is now "One-Click" from the UI to the Docker Cloud!
