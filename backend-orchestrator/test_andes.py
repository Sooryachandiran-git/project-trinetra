import andes
from core.andes_solver import solve_andes_powerflow
from api.models import ElectricalGridModel

# Create a mock ElectricalGridModel
grid_dict = {
    "buses": [{"id": "bus1", "name": "Bus 1", "vn_kv": 110.0}, {"id": "bus2", "name": "Bus 2", "vn_kv": 110.0}],
    "ext_grids": [{"id": "ext1", "name": "Ext Grid", "vm_pu": 1.0, "va_degree": 0.0}],
    "loads": [],
    "sgens": [],
    "gens": [],
    "lines": [
        {"id": "line_ext", "name": "Line Ext", "from_node": "ext1", "to_node": "bus1", "length_km": 0.0, "r_ohm_per_km": 0.0, "x_ohm_per_km": 0.0, "c_nf_per_km": 0.0, "max_i_ka": 0.4, "type": "generic_line"},
        {"id": "line1", "name": "Line 1", "from_node": "bus1", "to_node": "bus2", "length_km": 1.0, "r_ohm_per_km": 0.1, "x_ohm_per_km": 0.1, "c_nf_per_km": 10.0, "max_i_ka": 0.4, "type": "generic_line"}
    ],
    "transformers": [],
    "transformers3w": [],
    "switches": []
}

grid = ElectricalGridModel(**grid_dict)
res = solve_andes_powerflow(grid)
print("Result:", res)
