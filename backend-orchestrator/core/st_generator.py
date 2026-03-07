import os

class STGenerator:
    """
    Generates Structured Text (.st) code for OpenPLC IEDs.
    
    KEY RULES learned from testing:
    - All variables MUST have AT bindings (matiec rejects internal-only vars mixed with AT vars)
    - Use %QW20+ for internal simulation vars (lower addresses %QW1-9 may have display glitches) 
    - NO TON timers (compatibility issues with this OpenPLC build)
    - NO variables without AT binding in same VAR block as AT-bound vars
    
    BREAKER OUTPUT -> BACKEND READ:
    - %QX0.0 = breaker_closed (backend reads this via FC1 Modbus coil read)
    - When FALSE: backend opens the pandapower line -> power flow shows 0 voltage
    """
    def __init__(self, output_dir: str = "/tmp/trinetra_st"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def generate_st(self, ied_id: str, controlled_breakers: list) -> str:
        """
        Generates protection relay ST code.
        - Voltage oscillates 85-115 (simulates grid + faults)
        - Trips when OV (>110) or UV (<90)
        - Auto-recloses after 20 scans (10s)
        - Backend reads %QX0.0 coil -> updates pandapower line state -> physics shows 0V
        """
        # One coil per breaker starting at %QX0.0
        breaker_decls = "\n".join([
            f"    breaker_{i}_{b_id.replace('-','_').replace('.','_')} AT %QX0.{i} : BOOL := TRUE;"
            for i, b_id in enumerate(controlled_breakers)
        ])

        st_content = f"""\
PROGRAM trinetra_ied_{ied_id.replace('-','_').replace('.','_')}
  VAR
    (* Output registers visible in Monitoring tab - use %QW20+ to avoid display glitches *)
    voltage_pu      AT %QW20 : INT := 100;
    current_mA      AT %QW21 : INT := 500;
    frequency_hz    AT %QW22 : INT := 500;
    trip_count      AT %QW23 : INT := 0;
    scan_count      AT %QW24 : INT := 0;

    (* Internal simulation state - also AT-bound to avoid matiec errors *)
    sim_direction   AT %QW30 : INT := 1;
    reclose_timer   AT %QW31 : INT := 0;

    (* Protection status bits - %QX0.0 is read by TRINETRA backend via Modbus FC1 *)
    breaker_closed  AT %QX0.0 : BOOL := TRUE;
    ov_trip         AT %QX0.1 : BOOL := FALSE;
    uv_trip         AT %QX0.2 : BOOL := FALSE;
    oc_trip         AT %QX0.3 : BOOL := FALSE;
    any_trip        AT %QX0.4 : BOOL := FALSE;

    (* Extra breaker coils *)
{breaker_decls}
  END_VAR

  (* 1. Scan counter - increments every 500ms *)
  IF scan_count >= 32767 THEN
    scan_count := 0;
  ELSE
    scan_count := scan_count + 1;
  END_IF;

  (* 2. Voltage oscillation: ramps between 85 and 115 (representing 0.85-1.15 pu) *)
  voltage_pu := voltage_pu + sim_direction;
  IF voltage_pu >= 115 THEN
    sim_direction := -1;
  END_IF;
  IF voltage_pu <= 85 THEN
    sim_direction := 1;
  END_IF;

  (* 3. Current inversely proportional to voltage (constant power load model) *)
  IF voltage_pu > 0 THEN
    current_mA := 10000 / voltage_pu;
  END_IF;

  (* 4. Frequency stays nominal *)
  frequency_hz := 500;

  (* 5. PROTECTION LOGIC *)
  IF voltage_pu > 110 THEN
    ov_trip := TRUE;
  END_IF;
  IF voltage_pu < 90 THEN
    uv_trip := TRUE;
  END_IF;
  IF current_mA > 120 THEN
    oc_trip := TRUE;
  END_IF;

  any_trip := ov_trip OR uv_trip OR oc_trip;

  (* 6. Trip the breaker *)
  IF any_trip AND breaker_closed THEN
    breaker_closed := FALSE;
    trip_count := trip_count + 1;
    reclose_timer := 0;
  END_IF;

  (* 7. Auto-reclose after 20 scans = 10 seconds *)
  IF NOT breaker_closed THEN
    reclose_timer := reclose_timer + 1;
    IF reclose_timer >= 20 THEN
      ov_trip := FALSE;
      uv_trip := FALSE;
      oc_trip := FALSE;
      any_trip := FALSE;
      breaker_closed := TRUE;
      reclose_timer := 0;
    END_IF;
  END_IF;

END_PROGRAM

CONFIGURATION Config0
  RESOURCE Res0 ON PLC
    TASK Task0(INTERVAL := T#500ms, PRIORITY := 0);
    PROGRAM Inst0 WITH Task0 : trinetra_ied_{ied_id.replace('-','_').replace('.','_')};
  END_RESOURCE
END_CONFIGURATION
"""
        filepath = os.path.join(self.output_dir, f"ied_{ied_id}.st")
        with open(filepath, "w") as f:
            f.write(st_content)
        return filepath
