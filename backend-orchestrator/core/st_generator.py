import os

class STGenerator:
    """
    Generates Structured Text (.st) code for OpenPLC IEDs.
    """
    def __init__(self, output_dir: str = "/tmp/trinetra_st"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def generate_st(self, ied_id: str, controlled_breakers: list) -> str:
        """
        Generates protection relay ST code.
        - Dynamically creates Modbus Coils (%QX) for every controlled breaker.
        - Compares scaled voltage_pu from Pandapower against a 1.10 pu threshold (1100).
        - Trips ALL assigned breakers if overvoltage is detected.
        """
        breaker_decls = ""
        for i, b_id in enumerate(controlled_breakers):
            safe_name = b_id.replace('-', '_').replace('.', '_')
            breaker_decls += f"    Trip_Cmd_{safe_name} AT %QX0.{i} : BOOL := FALSE;\n"
        
        # Add Reset Coil (Always on %QX0.7 for consistency)
        breaker_decls += "    Reset_Cmd AT %QX0.7 : BOOL := FALSE;\n"

        # 2. Generate the Tripping Action (Setting coils to TRUE)
        trip_actions = ""
        for i, b_id in enumerate(controlled_breakers):
            safe_name = b_id.replace('-', '_').replace('.', '_')
            trip_actions += f"    Trip_Cmd_{safe_name} := TRUE;\n"

        # 3. Generate the Normal State Action (Setting coils to FALSE)
        normal_actions = ""
        for i, b_id in enumerate(controlled_breakers):
            safe_name = b_id.replace('-', '_').replace('.', '_')
            normal_actions += f"    Trip_Cmd_{safe_name} := FALSE;\n"

        # 4. The Master ST Content Template
        st_content = f"""\
PROGRAM trinetra_ied_{ied_id.replace('-','_').replace('.','_')}
  VAR
    (* Input Registers: Physics Telemetry *)
    V_scaled AT %MW0 : UINT := 1000;
    I_scaled AT %MW1 : UINT := 250;

    (* Diagnostic Counter *)
    scan_count AT %QW24 : INT := 0;
    
    (* Output Coils for Breakers *)
{breaker_decls}
  END_VAR

  VAR
    (* Internal Latching Logic (Non-located) *)
    fault_state : BOOL := FALSE;
  END_VAR

  (* Scan Counter *)
  IF scan_count >= 32767 THEN
    scan_count := 0;
  ELSE
    scan_count := scan_count + 1;
  END_IF;

  (* Latching Protection Logic *)
  IF V_scaled > 1100 THEN
    fault_state := TRUE;
  END_IF;

  IF Reset_Cmd THEN
    fault_state := FALSE;
  END_IF;

  (* Drive Breakers *)
  IF fault_state THEN
{trip_actions}
  ELSE
{normal_actions}
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
