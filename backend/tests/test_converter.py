import os
import sys

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.parse_case14 import IEEE14Parser
from core.convert_case14 import IEEE14Converter

base_dir = os.path.dirname(__file__)
case14_path = os.path.abspath(os.path.join(base_dir, "../data/case14.m"))

parser = IEEE14Parser(case14_path)

bus, gen, branch = parser.parse()

converter = IEEE14Converter(bus, gen, branch)

bus, lines, transformers, generators, loads, shunts = converter.convert()

converter.summary()

print("\n================ Lines ================")
print(lines[["FromBus", "ToBus", "R_ohm", "X_ohm", "C1_nF"]])

print("\n================ Transformers ================")
print(transformers[["FromBus", "ToBus", "Tap", "HV_kV", "LV_kV"]])

print("\n================ Loads ================")
print(loads[["Bus", "Pd", "Qd", "BaseKV"]])

print("\n================ Generators ================")
print(generators[["Bus", "Pg", "Qg", "BaseKV"]])

print("\n================ Shunts ================")
print(shunts[["Bus", "Bs", "BaseKV"]])