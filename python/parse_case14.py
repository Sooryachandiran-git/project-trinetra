import re
import pandas as pd


class IEEE14Parser:

    def __init__(self, filename):

        with open(filename, "r") as f:
            self.text = f.read()

    ########################################################

    def extract_matrix(self, name):

        pattern = rf"mpc\.{name}\s*=\s*\[(.*?)\];"

        match = re.search(pattern, self.text, re.S)

        if not match:
            raise Exception(f"{name} not found")

        rows = []

        for line in match.group(1).split("\n"):

            line = line.strip()

            if line == "":
                continue

            if line.startswith("%"):
                continue

            line = line.replace(";", "")

            rows.append(line.split())

        return pd.DataFrame(rows)

    ########################################################

    def parse(self):

        bus = self.extract_matrix("bus")

        gen = self.extract_matrix("gen")

        branch = self.extract_matrix("branch")

        # Convert every value to float
        bus = bus.astype(float)
        gen = gen.astype(float)
        branch = branch.astype(float)

        ####################################################
        # Bus Columns
        ####################################################

        bus.columns = [
            "Bus",
            "Type",
            "Pd",
            "Qd",
            "Gs",
            "Bs",
            "Area",
            "Vm",
            "Va",
            "BaseKV",
            "Zone",
            "Vmax",
            "Vmin"
        ]

        ####################################################
        # Generator Columns
        ####################################################

        gen.columns = [
            "Bus",
            "Pg",
            "Qg",
            "Qmax",
            "Qmin",
            "Vg",
            "mBase",
            "Status",
            "Pmax",
            "Pmin",
            "Pc1",
            "Pc2",
            "Qc1min",
            "Qc1max",
            "Qc2min",
            "Qc2max",
            "RampAGC",
            "Ramp10",
            "Ramp30",
            "RampQ",
            "APF"
        ]

        ####################################################
        # Branch Columns
        ####################################################

        branch.columns = [
            "FromBus",
            "ToBus",
            "R",
            "X",
            "B",
            "RateA",
            "RateB",
            "RateC",
            "Tap",
            "Shift",
            "Status",
            "AngMin",
            "AngMax"
        ]

        return bus, gen, branch


############################################################

if __name__ == "__main__":

    parser = IEEE14Parser("../data/case14.m")

    bus, gen, branch = parser.parse()

    print("======= Bus =======")

    print(bus.head())

    print()

    print("======= Generator =======")

    print(gen.head())

    print()

    print("======= Branch =======")

    print(branch.head())