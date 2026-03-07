import os

class STGenerator:
    """
    Generates Structured Text (.st) code for OpenPLC IEDs.
    
    The generated code is fully self-contained (no Slave Device config needed).
    It produces CHANGING values in the OpenPLC Monitoring page:
    - scan_count: increments every 500ms (proves PLC is alive)
    - heartbeat:  toggles every 1 second
    - Fixed nominal voltage/current/frequency values
    - Breaker coil outputs readable by the TRINETRA backend
    """
    def __init__(self, output_dir: str = "/tmp/trinetra_st"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def generate_st(self, ied_id: str, controlled_breakers: list) -> str:
        """
        Creates a self-contained .st file with:
        - A scan counter and heartbeat (visible changing values in Monitoring)
        - One coil per breaker (%QX0.0, %QX0.1, ...)
        - Static realistic voltage/current/frequency registers
        """
        # Build breaker variable declarations and assignments
        breaker_vars = "\n".join([
            f"    breaker_{b_id.replace('-','_')} AT %QX0.{i} : BOOL := TRUE;"
            for i, b_id in enumerate(controlled_breakers)
        ])
        breaker_logic = "\n".join([
            f"  breaker_{b_id.replace('-','_')} := TRUE;   (* Closed by default *)"
            for b_id in controlled_breakers
        ])

        st_content = f"""\
PROGRAM trinetra_ied_{ied_id.replace('-', '_')}
  VAR
    (* Scan counter: increments every 500ms — VISIBLE CHANGE in Monitoring tab *)
    scan_count      AT %QW0 : INT := 0;

    (* Heartbeat: toggles every 1 second — PROVES PLC IS RUNNING *)
    heartbeat       AT %QX0.7 : BOOL := FALSE;
    tmr             : TON;

    (* Grid measurement registers — static nominal values *)
    voltage_pu_x100 AT %QW1 : INT := 100;  (* 100 = 1.00 pu *)
    current_mA      AT %QW2 : INT := 500;  (* 500 mA base load *)
    frequency_x10   AT %QW3 : INT := 500;  (* 500 = 50.0 Hz *)

    (* Protection relay: one coil per controlled breaker *)
{breaker_vars}
    over_voltage    AT %QX0.5 : BOOL := FALSE;
    under_voltage   AT %QX0.6 : BOOL := FALSE;
  END_VAR

  (* 1. Scan counter — increments every 500ms, wraps at 32767 *)
  IF scan_count >= 32767 THEN
    scan_count := 0;
  ELSE
    scan_count := scan_count + 1;
  END_IF;

  (* 2. Heartbeat toggle every 1 second *)
  tmr(IN := NOT heartbeat, PT := T#1s);
  IF tmr.Q THEN
    heartbeat := NOT heartbeat;
  END_IF;

  (* 3. Nominal grid measurements *)
  voltage_pu_x100 := 100;
  current_mA      := 500;
  frequency_x10   := 500;

  (* 4. Fault flags — no faults under nominal conditions *)
  over_voltage  := FALSE;
  under_voltage := FALSE;

  (* 5. Breaker control — keep all CLOSED under normal conditions *)
{breaker_logic}

END_PROGRAM

CONFIGURATION Config0
  RESOURCE Res0 ON PLC
    TASK Task0(INTERVAL := T#500ms, PRIORITY := 0);
    PROGRAM Inst0 WITH Task0 : trinetra_ied_{ied_id.replace('-', '_')};
  END_RESOURCE
END_CONFIGURATION
"""
        filepath = os.path.join(self.output_dir, f"ied_{ied_id}.st")
        with open(filepath, "w") as f:
            f.write(st_content)
        return filepath
