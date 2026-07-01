import math
import pandas as pd

BASE_MVA = 100.0
FREQ = 60



class IEEE14Converter:

    def __init__(self, bus, gen, branch):

        self.bus = bus.copy()
        self.gen = gen.copy()
        self.branch = branch.copy()

        # Physical voltage levels used by our OpenDSS model
        self.bus_voltage = {
            1: 69.0,
            2: 69.0,
            3: 69.0,
            4: 69.0,
            5: 69.0,
            6: 13.8,
            7: 13.8,
            8: 13.8,
            9: 13.8,
            10: 13.8,
            11: 13.8,
            12: 13.8,
            13: 13.8,
            14: 13.8
        }

    ###############################################################

    def assign_voltage_levels(self):

        self.bus["BaseKV"] = self.bus["Bus"].map(self.bus_voltage)

    ###############################################################

    def convert_lines(self):

        lines = self.branch[self.branch["Tap"] == 0].copy()

        r_list, x_list, c1_list = [], [], []

        for _, row in lines.iterrows():

            kv = self.bus_voltage[int(row["FromBus"])]

            zbase = (kv ** 2) / BASE_MVA
            ybase = 1 / zbase

            r_list.append(row["R"] * zbase)
            x_list.append(row["X"] * zbase)

            b_siemens = row["B"] * ybase
            c_farads = b_siemens / (2 * math.pi * FREQ)
            c1_list.append(c_farads * 1e9)  # nF, length=1km in builder

        lines["R_ohm"], lines["X_ohm"], lines["C1_nF"] = r_list, x_list, c1_list

        return lines

    ###############################################################

    def convert_transformers(self):

        transformers = self.branch[self.branch["Tap"] != 0].copy()

        hv = []
        lv = []

        for _, row in transformers.iterrows():

            hv.append(self.bus_voltage[int(row["FromBus"])])
            lv.append(self.bus_voltage[int(row["ToBus"])])

        transformers["HV_kV"] = hv
        transformers["LV_kV"] = lv

        return transformers

    ###############################################################

    def convert_generators(self):

        generators = self.gen.copy()

        generators["BaseKV"] = generators["Bus"].map(self.bus_voltage)

        return generators

    ###############################################################

    def convert_loads(self):

        loads = self.bus[self.bus["Pd"] > 0].copy()

        loads["BaseKV"] = loads["Bus"].map(self.bus_voltage)

        return loads

    ###############################################################

    def convert_shunts(self):

        shunts = self.bus[self.bus["Bs"] != 0].copy()

        shunts["BaseKV"] = shunts["Bus"].map(self.bus_voltage)

        return shunts

    ###############################################################

    def summary(self):

        print("\n========== NETWORK SUMMARY ==========")

        print(f"Buses         : {len(self.bus)}")
        print(f"Lines         : {len(self.convert_lines())}")
        print(f"Transformers  : {len(self.convert_transformers())}")
        print(f"Generators    : {len(self.convert_generators())}")
        print(f"Loads         : {len(self.convert_loads())}")
        print(f"Shunts        : {len(self.convert_shunts())}")

    ###############################################################

    def convert(self):

        self.assign_voltage_levels()

        return (
            self.bus,
            self.convert_lines(),
            self.convert_transformers(),
            self.convert_generators(),
            self.convert_loads(),
            self.convert_shunts()
        )