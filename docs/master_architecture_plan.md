# Project TRINETRA Tasks

## Phase 1: Digital Twin Builder (Frontend)
- [ ] Initialize React application (using Vite)
- [ ] Set up project structure, routing, and core CSS
  - [ ] Implement a highly professional, modular, light-themed design system
- [ ] Create Home Page (Landing / Plant Selection)
  - [ ] Add a prominent icon/card for "Electrical SCADA System" selection
- [ ] Install and configure `reactflow` for the grid topology canvas
- [ ] Create the main application layout (Header, Sidebar, Workspace)
- [ ] Implement the React Connective Tissue (Store, Services, Utils)
  - [ ] **State Manager:** Create `src/store/useGridStore.js` (Zustand) for centralized React Flow state.
  - [ ] **API Messenger:** Create `src/services/api.js` and `src/services/fastApiBridge.js` for Axios communication.
  - [ ] **JSON Compiler:** Create `src/utils/jsonBuilder.js` to compile visual nodes into the FastAPI payload on "Deploy".
- [ ] Implement the Draggable Component Palette (Sidebar)
  - [ ] **Electrical Components Panel**
    - [ ] External Grid (`vm_pu`)
    - [ ] Bus (`vn_kv`)
    - [ ] Transmission Line (`length_km`, `r_ohm_per_km`, `x_ohm_per_km`)
    - [ ] Circuit Breaker (State: Closed/Open)
    - [ ] Load (`p_mw`, `q_mvar`)
  - [ ] **SCADA Components Panel**
    - [ ] IED (Bind Port, Controlled Breakers)
    - [ ] Network Switch (Visual only)
    - [ ] GPS Clock & Protocol Converter (Visual only)
    - [ ] RTU / SCADA PC (Visual representation of backend)
- [ ] Implement the interactive Topology Canvas with React Flow
  - [ ] **Aesthetics:** Use light-gray dot grid background (`variant="dots" gap={16}`).
  - [ ] **Routing:** Use orthogonal step-paths (`type="smoothstep"`) for edges, strictly 90-degree lines.
  - [ ] **Node Design (Hybrid):** Professional white cards with shadows containing traditional electrical symbols. Show critical micro-badges (State/Voltage) up front, hide deep config behind double-click modals.
  - [ ] **Dynamic Handles:** 
    - Bus nodes operate as massive bars (unlimited connections).
    - IEDs dynamically generate handles based on "Number of Controlled Breakers" input. 
    - Breakers/Lines strictly 1-in, 1-out.
  - [ ] **Design Mode (Builder):** Drag, drop, route wires, and double-click to set Pandapower parameters.
  - [ ] **Run Mode (Dual-View Dashboard):**
    - Transition triggers upon "Deploy" (Canvas locks, sidebar hides).
    - *View A: Topology SLD.* Live canvas, dot grid fades. Lines flash Red on fault, breakers animate open/closed (Red/Green). Spatial awareness of attacks. Includes **"STALE DATA/COMMUNICATION LOST"** yellow warnings on IED nodes if Modbus connection drops.
    - *View B: Control Room.* Full-screen, high-contrast dashboard. Top Row KPIs, Middle Row Recharts/Plotly sine/trend graphs, Bottom Row scrolling Alarm Historian text logs.
    - [ ] **Historian / Data Log Tab:** Include a DB Health Indicator (Rows recorded) and a "📥 Export Research Dataset (CSV)" button that triggers a FastAPI GET request.
    - [ ] **Red Team Control Panel (Run Mode):** Add a dedicated "Attack Interface" panel to trigger specific attack profiles (e.g., inject FDIA, launch DoS) against the running twin.
- [ ] State Management for the Grid Topology (saving/loading grid state and JSON payload generation). Ensure backend routing Maps 1 IED to 2 Breakers natively (e.g., R1 controls BR1 & BR2).

## Phase 2: Backend API & Physics Engine Bridge
- [ ] Initialize FastAPI backend
- [ ] Integrate Pandapower for Load Flow equations
- [ ] Create Modbus TCP/IP communication layer (pymodbus)
  - [ ] Implement Multiplier Method (Float to Int and Int to Float conversion for Modbus Registers)
- [ ] Implement the Cyber-Physical Tick (Polling Loop via asyncio/threading every ~500ms)
  - [ ] Read OpenPLC Modbus Coils (Trip Status)
  - [ ] Update Pandapower switches
  - [ ] Recalculate power flow equations
  - [ ] Scale and Write analog values (Voltages/Currents) back to OpenPLC Holding Registers
- [ ] **Red Teaming API Endpoints:**
  - [ ] Create `POST /api/attack/fdia` to intercept/overwrite the Modbus write loop with malicious data.
  - [ ] Create `POST /api/attack/dos` to intentionally block the `pymodbus` read thread for a specific port.

## Phase 3: Control Emulation (Dynamic Orchestrator)
- [ ] Implement FastAPI Docker Compose Orchestration
  - [ ] Render a dynamic `docker-compose.yml` file into a dedicated `backend-orchestrator/temp_run/` folder from the JSON payload.
  - [ ] Ensure `.gitignore` ignores `backend-orchestrator/temp_run/` to prevent overwriting Git histories.
  - [ ] Execute `subprocess.run(["docker-compose", "-f", "dynamic_lab.yml", "up", "-d"])` on Deploy.
  - [ ] Ensure clean teardown via `docker-compose down` on Stop to prevent port conflicts.
- [ ] Automate `.st` Payload Injection via FastAPI HTTP Requests
  - [ ] Automatically POST the uploaded `.st` logic to `http://localhost:<PORT>/upload-program`
  - [ ] Automatically execute web commands to compile and start the logic inside the container
- [ ] **Distance Protection Logic Implementation:** Ensure the base OpenPLC `.st` file calculates Impedance (`Z=V/I`) to accurately replicate the lab's Distance Protection relays.
- [ ] Integrate OpenPLC Modbus states tightly with Pandapower physics loop

## Phase 4: Time-Series Database Integration (ML-Ready)
- [ ] Set up InfluxDB Docker Container
- [ ] Create ML-Optimized Data Ingestion Pipeline (FastAPI to InfluxDB)
  - [ ] Construct the JSON Point payload on every 500ms Tick with 100ms pymodbus timeouts.
  - [ ] Write the **Macro Grid KPIs** (`total_load_mw`, `total_loss_mw`)
  - [ ] Write **The Truth** (Physics): `line1_v_true`, `line1_i_true` (from Pandapower)
  - [ ] Write **The Lie** (Cyber): `line1_v_measured`, `line1_i_measured` (from OpenPLC). Output `NaN` on timeout.
  - [ ] Write **Connection Health**: `r1_comms_status` (1 = Online, 0 = Timeout/Dead)
  - [ ] Write **Logic State**: `br1_physical_status`, `r1_trip_coil`
  - [ ] Tag **ML Labels**: `is_under_attack` (1/0), `grid_state` (NORMAL, UNDER_ATTACK, DEGRADED)
  - [ ] Maintain an `operator_audit_log` Measurement for human overrides.
- [ ] Implement `GET /api/export-data` Endpoint
  - [ ] Package InfluxDB `grid_telemetry` ticks into `trinetra_attack_data_YYYY.csv` for Pandas/Scikit-Learn analysis.

## Critical Technical Risks & Solutions

### 1. The Asynchronous Modbus Bottleneck (Phase 2)
- **Risk:** Synchronous Modbus polling across multiple IEDs will stretch the 500ms limit, causing clock drift between the cyber and physical engines.
- **Solution:** Use **`asyncio.gather()`** in FastAPI with `AsyncModbusTcpClient` to fire all Modbus read/write requests simultaneously, ensuring the loop waits only as long as the slowest responding container.

### 2. The OpenPLC Cold Start Delay (Phase 3)
- **Risk:** OpenPLC containers take several seconds to boot via Docker Compose. Injecting the `.st` payload instantly at `t=0` will result in `ConnectionRefusedError`.
- **Solution:** Implement a **Health Check Polling Loop** in FastAPI. Send tiny `GET` requests to the OpenPLC web server (`localhost:808x`) until receiving a `200 OK` before initiating the payload injection sequence.

### 3. The Pandapower Convergence Crash (Phase 2)
- **Risk:** Isolating a load from generation (e.g., tripping all incoming breakers) causes Newton-Raphson mathematically to fail (`pandapower.api.ConvergenceError`), crashing the entire backend.
- **Solution:** Wrap `pp.runpp(net)` in a strict `try/except` block. Upon a convergence failure due to islanding, gracefully catch the error, manually set isolated node voltages to `0.0V`, and continue the tick without server interruption.
