import os
import sys

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.parse_case14 import IEEE14Parser
from core.convert_case14 import IEEE14Converter
from core.build_ieee14 import IEEE14Builder

base_dir = os.path.dirname(__file__)
case14_path = os.path.abspath(os.path.join(base_dir, "../data/case14.m"))

parser = IEEE14Parser(case14_path)
bus, gen, branch = parser.parse()
converter = IEEE14Converter(bus, gen, branch)
bus, lines, transformers, generators, loads, shunts = converter.convert()

builder = IEEE14Builder(bus, lines, transformers, generators, loads, shunts)
builder.build()

dss = builder.dss

print("\n--- LOADS ---")
idx = dss.loads.first()
while idx > 0:
    # Activate the load element as a cktelement to get its bus name and power
    element_name = f"Load.{dss.loads.name}"
    dss.circuit.set_active_element(element_name)
    buses = dss.cktelement.bus_names
    powers = dss.cktelement.total_powers  # total active (kW) and reactive (kvar) at term 1
    print(f"{element_name} @ {buses}: kW={dss.loads.kw}, kvar={dss.loads.kvar}, Actual powers={powers}")
    idx = dss.loads.next()

print("\n--- GENERATORS ---")
idx = dss.generators.first()
while idx > 0:
    name = dss.generators.name
    element_name = f"Generator.{name}"
    dss.circuit.set_active_element(element_name)
    buses = dss.cktelement.bus_names
    powers = dss.cktelement.total_powers
    
    # Query Vpu via dss.text
    vpu_setpoint = dss.text(f"? {element_name}.Vpu")
    kw_setpoint = dss.text(f"? {element_name}.kW")
    kvar_setpoint = dss.text(f"? {element_name}.kvar")
    
    # Active/reactive power is entering the element, so negate it to get generation
    p_gen = -powers[0] if len(powers) > 0 else 0.0
    q_gen = -powers[1] if len(powers) > 1 else 0.0
    
    print(f"{element_name} @ {buses}:")
    print(f"  Setpoint: kW={kw_setpoint}, kvar={kvar_setpoint}, Vpu={vpu_setpoint}")
    print(f"  Actual Generation: P={round(p_gen, 2)} kW, Q={round(q_gen, 2)} kvar")
    idx = dss.generators.next()
