from pydantic import BaseModel, Field
from typing import List, Optional

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
    c_nf_per_km: float = 10.0
    max_i_ka: float = 0.4

class SwitchModel(BaseModel):
    id: str
    name: str = "Breaker"
    initial_status: str

class TransformerModel(BaseModel):
    id: str
    name: str = "Transformer"
    hv_bus: str
    lv_bus: str
    use_std_type: bool = True
    std_type: str = "160 MVA 380/110 kV"
    sn_mva: float = 160.0
    vn_hv_kv: float = 380.0
    vn_lv_kv: float = 110.0
    vk_percent: float = 12.2
    vkr_percent: float = 0.26
    pfe_kw: float = 115.0
    i0_percent: float = 0.06
    shift_degree: float = 150.0

class Transformer3WModel(BaseModel):
    id: str
    name: str = "3W Transformer"
    hv_bus: str
    mv_bus: str
    lv_bus: str
    std_type: str = "63/25/38 MVA 110/20/10 kV"

class SgenModel(BaseModel):
    id: str
    name: str = "Static Generator"
    p_mw: float
    q_mvar: float = 0.0

class GenModel(BaseModel):
    id: str
    name: str = "Generator"
    p_mw: float
    vm_pu: float = 1.0

class ElectricalGridModel(BaseModel):
    buses: List[BusModel] = []
    ext_grids: List[ExtGridModel] = []
    loads: List[LoadModel] = []
    lines: List[LineModel] = []
    switches: List[SwitchModel] = []
    transformers: List[TransformerModel] = []
    transformers3w: List[Transformer3WModel] = []
    sgens: List[SgenModel] = []
    gens: List[GenModel] = []


# --- SCADA MODBUS MODELS ---

class IEDModel(BaseModel):
    id: str
    name: str = "IED"
    port: int
    num_breakers: int = 1
    monitors_bus: Optional[str] = None  # React node ID of the Bus this IED monitors.
                                        # Used by grid_builder to build ied_bus_map:
                                        #   { ied_id → pandapower bus index }
                                        # This enables per-bus physics truth extraction
                                        # (bus_v_pu_true) for each IED independently,
                                        # which is the foundation of the dual-source
                                        # anomaly signal (bus_v_delta) in the dataset.
                                        # Falls back to bus index 0 if not set.
    st_code: Optional[str] = None
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
