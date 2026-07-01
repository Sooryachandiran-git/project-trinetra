from parse_case14 import IEEE14Parser
from convert_case14 import IEEE14Converter
from build_ieee14 import IEEE14Builder

parser = IEEE14Parser("../data/case14.m")

bus, gen, branch = parser.parse()

converter = IEEE14Converter(bus, gen, branch)

bus, lines, transformers, generators, loads, shunts = converter.convert()

builder = IEEE14Builder(
    bus,
    lines,
    transformers,
    generators,
    loads,
    shunts
)

builder.build()