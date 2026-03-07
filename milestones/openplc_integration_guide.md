# OpenPLC Integration Guide: Lessons Learned & Best Practices

Integrating a physics engine (like Pandapower) with a cyber-control layer (OpenPLC) requires strict adherence to network protocols, memory mapping, and compiler constraints. This document details the exact architecture, API endpoints, and technical hurdles involved in automating an OpenPLC digital twin.

---

## 1. How Data is Shared (The Cyber-Physical Bridge)

OpenPLC acts as a Modbus TCP server. The Python backend (FastAPI/Pandapower) acts as a Modbus Client that continuously polls and writes to OpenPLC’s memory at a set interval (the "Tick Rate").

### Memory Mapping & Register Types
Modbus has distinct register types. You must use the correct type for the correct telemetry:

*   **Holding Registers (`%MW`)**: Used for passing **analog measurements** (Voltage, Current, Power).
    *   *Constraint*: Modbus registers only hold 16-bit Integers (0 to 65535). They **cannot hold floats / decimal numbers**.
    *   *Solution*: Use a "Multiplier Method". If physics output is `230.55V`, Python must multiply it by 100 before writing `23055` to `%MW0`. The ST Logic inside the PLC must be aware that `23000` equals `230V`.
*   **Coils (`%QX`)**: Used for reading **digital actions** from the PLC (e.g., opening a breaker).
    *   *Constraint*: Coils hold Booleans (`TRUE` / `FALSE`).
    *   *Pattern*: Python writes sensor data to `%MW` registers. The OpenPLC ST code evaluates those registers. If a fault is detected, the ST code sets a `%QX` output coil to `TRUE`. Python reads that `%QX` coil and executes the physical switch-opening in Pandapower.

> [!WARNING]
> **Memory Overlap / Clashes:** You cannot map two different variables in ST code to the same memory location (e.g., `%QX0.0`). If an IED controls multiple breakers, you must assign a unique coil for each (e.g., `%QX0.0`, `%QX0.1`).

---

## 2. Automating OpenPLC Execution

When standing up an OpenPLC container dynamically (e.g., `tuttas/openplc_v3`), you must bypass the standard GUI and use backend scripts and APIs to inject and run the code.

### The Provisioning Pipeline

1.  **Launch the Container:** Start the Docker container, mapping its internal port `8080` (Web API) to an external port (e.g., `8080`) and internal `502` to an external Modbus port (e.g., `5020`).
2.  **Wait for Boot:** The OpenPLC SQLite DB and Python web server take time to initialize. You must wait (~5 seconds) and continuously check if `http://localhost:<web_port>` is accessible before proceeding.
3.  **Inject ST Code:** Instead of uploading through the API (which can be flaky with file form-data), use `docker cp` to forcefully write your `.st` file into the container at the expected path (`/workdir/openplc_v3/scripts/blank_program.st`).
4.  **Execute the Compiler:** Do not use the Web API to compile. Use `docker exec` to trigger the backend bash script directly:
    ```bash
    cd /workdir/openplc_v3/scripts && bash compile_program.sh blank_program.st
    ```
    *Wait ~20-30 seconds.* Wait for the CLI output: `Compilation finished successfully!`.
5.  **Start the Runtime via API:** Once the C-code is compiled into the `openplc` binary, you must start the executor using OpenPLC's minimal HTTP API.

### Required OpenPLC API Endpoints

To programmatically control the PLC state without the GUI, utilize requests with Python's `requests.Session()` to maintain cookies:

1.  **Login:**
    *   `POST /login`
    *   Data: `{"username": "openplc", "password": "openplc"}`
2.  **Start PLC Runtime:**
    *   `GET /start_plc`
    *   This boots the compiled binary and opens port 502 for Modbus! Modbus will **not** listen until this is called.
3.  **Stop PLC Runtime:**
    *   `GET /stop_plc`
    *   Useful for graceful shutdowns or reprogramming.
4.  **Status Check:**
    *   `GET /dashboard`
    *   Scrape the HTML response for the word `Running` or `Compiling`.

---

## 3. Structured Text (.st) Code Constraints

Getting OpenPLC's `matiec` compiler to accept custom logic injected from a UI requires exact syntax.

### The CONFIGURATION Block is Mandatory
Python scripts generating `.st` files often forget the trailing configuration block. **If omitted, the compiler will fail with:** `mv: cannot stat 'Config0.c': No such file or directory`.

Every `.st` file must end with:
```pascal
CONFIGURATION Config0
  RESOURCE Res0 ON PLC
    TASK Task0(INTERVAL := T#500ms, PRIORITY := 0);
    PROGRAM Inst0 WITH Task0 : your_program_name;
  END_RESOURCE
END_CONFIGURATION
```
*(Ensure `your_program_name` perfectly matches the `PROGRAM` declaration at the top).*

### The Web Server Regex Quirk (The "AT" Bug)
If you deploy code and the Modbus mapping fails with the OpenPLC Web UI indicating the variable Type is **"AT"**, you have encountered the regex parser bug.

The embedded OpenPLC python web server uses a rigid text parser to populate the *Monitoring* table. It assumes variables are defined with exactly **one space**. Extraneous tabs or spaces for alignment will break the UI's ability to watch the variable.

**BAD (Breaks UI):**
```pascal
V_scaled          AT %MW0 : UINT := 23000;
```

**GOOD (Strict 1-Space Formatting):**
```pascal
V_scaled AT %MW0 : UINT := 23000;
```

### Compiler Type strictness (No Floats)
The `matiec` compiler often throws errors relating to `REAL` or `LREAL` types when dealing with standard Modbus registers because a standard Holding Register is a 16-bit Integer (`UINT` or `INT`). Make sure to cast your logic to Integers entirely (as seen in the Distance Protection multiplier approach) rather than attempting floating-point division directly inside the `VAR` blocks unless you combine two registers into a 32-bit `REAL`.

---

## 4. Graceful Shutdown & Port Management

The Backend Orchestrator uses background daemon threads for PyModbus servers and continuous simulation ticks.

**The "Address already in use" Trap:**
If an exception occurs or the user hits `Ctrl+C`, FastAPI's `uvicorn` shuts down, but the background Modbus server threads do not necessarily release their OS level socket bindings (`0.0.0.0:5502` or `0.0.0.0:8000`).

**Solution:**
1. Maintain explicit references to your PyModbus threads.
2. Hook into the web framework's lifecycle utilizing `@app.on_event("shutdown")`.
3. Explicitly call PyModbus's `ServerStop()` method and execute a `thread.join()` to guarantee the ports are freed back to the OS before the main python process exits.
