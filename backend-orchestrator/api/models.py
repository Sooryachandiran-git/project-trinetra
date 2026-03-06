from pydantic import BaseModel, Field
from typing import List

# --- ELECTRICAL GRID MODELS ---

class BusModel(BaseModel):
    id: str
    name: str = "Bus"
    vn_kv: float

class ExtGridModel(BaseModel):
    id: str
    name: str = "Ext Grid"
    vm_pu: float = 1.0
    va_degree: float = 0.0

class LoadModel(BaseModel):
    id: str
    name: str = "Load"
    p_mw: float
    q_mvar: float

class LineModel(BaseModel):
    id: str
    from_node: str
    to_node: str
    type: str = "generic_line"
    length_km: float = 1.0
    r_ohm_per_km: float = 0.1
    x_ohm_per_km: float = 0.1

class SwitchModel(BaseModel):
    id: str
    name: str = "Breaker"
    initial_status: str

class ElectricalGridModel(BaseModel):
    buses: List[BusModel] = []
    ext_grids: List[ExtGridModel] = []
    loads: List[LoadModel] = []
    lines: List[LineModel] = []
    switches: List[SwitchModel] = []


# --- SCADA MODBUS MODELS ---

class IEDModel(BaseModel):
    id: str
    name: str = "IED"
    port: int
    num_breakers: int = 1
    st_code: str = None
    protocols: List[str]

class ControlMappingModel(BaseModel):
    ied_id: str
    breaker_id: str
    type: str = "modbus_coil"

class ScadaSystemModel(BaseModel):
    ieds: List[IEDModel] = []
    control_mappings: List[ControlMappingModel] = []


# --- ROOT DEPLOYMENT PAYLOAD ---

class DeploymentPayload(BaseModel):
    metadata: dict
    electrical_grid: ElectricalGridModel
    scada_system: ScadaSystemModel
