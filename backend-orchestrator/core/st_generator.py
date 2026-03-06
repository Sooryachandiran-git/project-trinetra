import os

class STGenerator:
    """
    Generates Structured Text (.st) code for OpenPLC based on the IED's connected breakers.
    """
    def __init__(self, output_dir: str = "/tmp/trinetra_st"):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def generate_st(self, ied_id: str, controlled_breakers: list) -> str:
        """
        Creates an .st file that maps breakers to Modbus coils.
        Each breaker gets a unique coil address starting from %QX0.0.
        """
        st_content = f"""
PROGRAM trinetra_logic_{ied_id}
  VAR
    {chr(10).join([f"breaker_{b_id} AT %QX0.{i} : BOOL := TRUE;" for i, b_id in enumerate(controlled_breakers)])}
    voltage_sensor AT %QW0 : INT := 0;
  END_VAR

  (* Simple pass-through: In a real IED, we'd add protection logic here *)
  (* But for now, we just expose these as Modbus addresses for the SCADA to control *)
END_PROGRAM

CONFIGURATION Conf0
  RESOURCE Res0 ON PLC
    TASK TaskMain(INTERVAL := T#50ms, PRIORITY := 0);
    PROGRAM Inst0 WITH TaskMain : trinetra_logic_{ied_id};
  END_RESOURCE
END_CONFIGURATION
"""
        filepath = os.path.join(self.output_dir, f"ied_{ied_id}.st")
        with open(filepath, "w") as f:
            f.write(st_content)
        
        return filepath
