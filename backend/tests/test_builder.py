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

builder = IEEE14Builder(
    bus,
    lines,
    transformers,
    generators,
    loads,
    shunts
)

builder.build()