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
        - Compares scaled voltage from Pandapower against a 250V threshold.
        - Trips ALL assigned breakers if overvoltage is detected.
        """
        # 1. Generate Variable Declarations (Dynamically map to %QX0.0, %QX0.1, etc.)
        breaker_decls = ""
        for i, b_id in enumerate(controlled_breakers):
            safe_name = b_id.replace('-', '_').replace('.', '_')
            breaker_decls += f"    Trip_Cmd_{safe_name} AT %QX0.{i} : BOOL := FALSE;\n"

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
    (* Input Registers received from Pandapower Physics Engine via Modbus *)
    V_scaled          AT %MW0 : UINT := 23000;  (* Voltage * 100 *)
    I_scaled          AT %MW1 : UINT := 1520;   (* Current * 100 *)

    (* Custom Diagnostic Variables *)
    scan_count        AT %QW24 : INT := 0;     
    
    (* Dynamic Output Coils (Read by Python Backend) *)
{breaker_decls}
  END_VAR

  (* Scan Counter - Proves the logic is executing *)
  IF scan_count >= 32767 THEN
    scan_count := 0;
  ELSE
    scan_count := scan_count + 1;
  END_IF;

  (* Overvoltage Protection Logic (Threshold: 250V) *)
  IF V_scaled > 25000 THEN
    (* FAULT DETECTED: Trip all assigned breakers *)
{trip_actions}
  ELSE
    (* GRID NORMAL: Keep breakers closed *)
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
