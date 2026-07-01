from parse_case14 import IEEE14Parser
from convert_case14 import IEEE14Converter

parser = IEEE14Parser("../data/case14.m")

bus, gen, branch = parser.parse()

converter = IEEE14Converter(bus, gen, branch)

bus, lines, transformers, generators, loads, shunts = converter.convert()

converter.summary()

print("\n================ Lines ================")
print(lines[["FromBus","ToBus","R_ohm","X_ohm"]])

print("\n================ Transformers ================")
print(transformers[["FromBus","ToBus","Tap","HV_kV","LV_kV"]])

print("\n================ Loads ================")
print(loads[["Bus","Pd","Qd","BaseKV"]])

print("\n================ Generators ================")
print(generators[["Bus","Pg","Qg","BaseKV"]])

print("\n================ Shunts ================")
print(shunts[["Bus","Bs","BaseKV"]])