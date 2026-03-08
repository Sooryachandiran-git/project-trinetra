# TRINETRA: End-to-End Physics & Attack Test Protocol (FDIA-test1)

Follow this exact architecture and protocol to prove the Pandapower physics engine is actively responding to the UI, and that the OpenPLC logic trips based on live values.

## 1. Canvas Architecture (The "Knowns")

Drag and drop these exact components onto your canvas and link them together in a straight line:

1. **External Grid** → connect to → **Bus 1**
2. **Bus 1** → connect to → **Breaker**
3. **Breaker** → connect to → **Bus 2**
4. **Bus 2** → connect to → **Load**
5. **IED** → connect dashed line to → **Breaker**

### Exact Node Properties
Double-click each node and apply these exact values:

*   **External Grid**: `vm_pu = 1.0`, `va_degree = 0.0`
*   **Bus 1**: `vn_kv = 110.0`
*   **Bus 2**: `vn_kv = 110.0`
*   **Breaker**: Status = `Closed`
*   **Load**: `p_mw = 50.0`, `q_mvar = 10.0`
*   **IED**: Port = `5020`. Then, click **Open ST Code Editor**.

## 2. The Custom ST Code
Erase whatever is in the ST Code Editor and paste this exact script. 

```pascal
PROGRAM trinetra_ied_node_test
  VAR
    (* Located Variables Case: Physical Addresses *)
    V_scaled AT %MW0 : UINT := 1000;
    I_scaled AT %MW1 : UINT := 250;
    scan_count AT %QW24 : INT := 0;
    Trip_Cmd_breaker_1 AT %QX0.0 : BOOL := FALSE;
    Reset_Cmd AT %QX0.7 : BOOL := FALSE;
  END_VAR

  VAR
    (* Unlocated Variable Case: Internal Memory *)
    fault_state : BOOL := FALSE;
  END_VAR

  (* Heartbeat *)
  IF scan_count >= 32767 THEN
    scan_count := 0;
  ELSE
    scan_count := scan_count + 1;
  END_IF;

  (* THE PROTECTION LOGIC: Latching Pattern *)
  IF V_scaled > 1100 THEN
    fault_state := TRUE;
  END_IF;

  IF Reset_Cmd THEN
    fault_state := FALSE;
  END_IF;

  (* Drive the physical breaker *)
  Trip_Cmd_breaker_1 := fault_state;

END_PROGRAM

CONFIGURATION Config0
  RESOURCE Res0 ON PLC
    TASK Task0(INTERVAL := T#500ms, PRIORITY := 0);
    PROGRAM Inst0 WITH Task0 : trinetra_ied_node_test;
  END_RESOURCE
END_CONFIGURATION
```

## 3. Deployment & Baseline Verification
1. Click **Deploy**.
2. Wait ~25 seconds for the Docker backend to compile your custom ST code and connect to Modbus.
3. Once the **Run Mode** activates, look at the canvas. The line connecting the Breaker to the Load should be **GREEN** and animating.
4. Go to the **Control Room**. You should see the `Grid Base Voltage` sitting steadily around `1.0000 pu`.

## 4. The Cyber-Attack (FDIA)
Open a completely new terminal window and run:
```bash
cd ~/project-trinetra/backend-orchestrator
source venv/bin/activate
python attacks/fdia_attack.py --target 127.0.0.1 --port 5020 --voltage_pu 1.20
```

### What to watch for:
1.  **The Canvas**: The wire will instantly turn **RED**.
2.  **Latching**: The wire will **STAY RED** even after the script finishes.
3.  **Reset**: Click the green **"Master System Reset"** button in the Control Room. The wire will turn **GREEN** again.
