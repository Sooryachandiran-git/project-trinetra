import py_dss_interface


class IEEE14Builder:

    def __init__(
        self,
        bus,
        lines,
        transformers,
        generators,
        loads,
        shunts
    ):

        self.dss = py_dss_interface.DSS()

        self.bus = bus
        self.lines = lines
        self.transformers = transformers
        self.generators = generators
        self.loads = loads
        self.shunts = shunts

    ############################################################
    # Circuit
    ############################################################

    def create_circuit(self):

        self.dss.text("Clear")

        self.dss.text("Set DefaultBaseFrequency=60")

        self.dss.text(
            "New Circuit.IEEE14 "
            "BasekV=69 "
            "Bus1=Bus1 "
            "pu=1.06 "
            "Angle=0 "
            "MVAsc3=5000 "
            "MVAsc1=3000"
        )

        print("Circuit Created")

    ############################################################
    # Source
    ############################################################

    def create_source(self):

        self.dss.text(
            "Edit Vsource.Source "
            "BasekV=69 "
            "pu=1.06 "
            "Frequency=60"
        )

        print("Source Created")

    ############################################################
    # Transformers
    ############################################################

    def create_transformers(self):

        print("\nCreating Transformers...\n")

        for index, tr in self.transformers.iterrows():

            name = f"T{index}"

            hv_bus = f"Bus{int(tr['FromBus'])}"
            lv_bus = f"Bus{int(tr['ToBus'])}"

            hv = tr["HV_kV"]
            lv = tr["LV_kV"]

            tap = tr["Tap"]

            xhl = tr["X"] * 100

            self.dss.text(
                f"""
New Transformer.{name}
Phases=3
Windings=2
XHL={xhl}

~ Wdg=1
Bus={hv_bus}
Conn=Wye
kV={hv}
kVA=100000

~ Wdg=2
Bus={lv_bus}
Conn=Wye
kV={lv}
kVA=100000
Tap={tap}
"""
            )

            print(name, hv_bus, "-->", lv_bus)

        print("\nTransformers Finished")
    ############################################################
    # Lines
    ############################################################

    def create_lines(self):

        print("\nCreating Lines...\n")

        count = 1

        for _, line in self.lines.iterrows():

            bus1 = f"Bus{int(line['FromBus'])}"
            bus2 = f"Bus{int(line['ToBus'])}"

            r = line["R_ohm"]
            x = line["X_ohm"]

            b = line["B"]

            self.dss.text(
                f"""
New Line.L{count}
Bus1={bus1}
Bus2={bus2}
Phases=3
Length=1
Units=km
R1={r}
X1={x}
C1={b}
"""
            )

            print(f"L{count}: {bus1} -> {bus2}")

            count += 1

        print("\nLines Finished")

    ############################################################
    # Loads
    ############################################################

    def create_loads(self):

        print("\nCreating Loads...\n")

        count = 1

        for _, load in self.loads.iterrows():

            bus = int(load["Bus"])

            kv = load["BaseKV"]

            kw = load["Pd"] * 1000
            kvar = load["Qd"] * 1000

            self.dss.text(
                f"""
New Load.Load{count}
Bus1=Bus{bus}
Phases=3
Conn=Wye
kV={kv}
kW={kw}
kvar={kvar}
"""
            )

            print(f"Load{count} @ Bus{bus}")

            count += 1

        print("\nLoads Finished")

    ############################################################
    # Generators
    ############################################################

    def create_generators(self):

        print("\nCreating Generators...\n")

        count = 1

        for _, gen in self.generators.iterrows():

            bus = int(gen["Bus"])

            kv = gen["BaseKV"]

            kw = gen["Pg"] * 1000
            kvar = gen["Qg"] * 1000

            self.dss.text(
                f"""
New Generator.G{count}
Bus1=Bus{bus}
Phases=3
kV={kv}
kW={kw}
kvar={kvar}
"""
            )

            print(f"G{count} @ Bus{bus}")

            count += 1

        print("\nGenerators Finished")

    ############################################################
    # Shunts
    ############################################################

    def create_shunts(self):

        print("\nCreating Shunts...\n")

        count = 1

        for _, shunt in self.shunts.iterrows():

            bus = int(shunt["Bus"])

            kv = shunt["BaseKV"]

            kvar = shunt["Bs"] * 1000

            self.dss.text(
                f"""
New Capacitor.C{count}
Bus1=Bus{bus}
Phases=3
kV={kv}
kvar={kvar}
"""
            )

            print(f"C{count} @ Bus{bus}")

            count += 1

        print("\nShunts Finished")

    ############################################################
    # Solve
    ############################################################

    def solve(self):

        self.dss.text("CalcVoltageBases")

        self.dss.solution.solve()

        print("\nPower Flow Solved")

    ############################################################
    # Results
    ############################################################

    def results(self):

        print("\n==============================")
        print("Circuit Summary")
        print("==============================")

        print("Converged :", self.dss.solution.converged)

        print("Total Power :", self.dss.circuit.total_power)

        print("Losses :", self.dss.circuit.losses)

        print("\nBus Voltages")

        names = self.dss.circuit.buses_names
        volts = self.dss.circuit.buses_vmag_pu

        for name, v in zip(names, volts):
            print(name, ":", round(v, 4))

    ############################################################

    def build(self):

        self.create_circuit()

        self.create_source()

        self.create_transformers()

        self.create_lines()

        self.create_generators()

        self.create_loads()

        self.create_shunts()

        self.solve()

        self.results()

    ############################################################

    def build_part1(self):

        self.create_circuit()

        self.create_source()

        self.create_transformers()