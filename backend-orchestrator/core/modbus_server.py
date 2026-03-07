"""
Modbus Slave Server for TRINETRA backend.

This runs a Modbus TCP server that OpenPLC's "Slave Devices" feature polls FROM.
OpenPLC reads our registers into its %IW (Input Words) — which are NEVER overwritten
by the PLC scan cycle, only READ by PLC logic.

Register map (what OpenPLC reads from us):
  - Holding Register 0: voltage_pu * 100   (e.g., 100 = 1.00 pu)
  - Holding Register 1: active_power_kw    (e.g., 500 = 500 kW)
  - Holding Register 2: reactive_power_kw
  - Coil 0:            grid_online          (True/False)
"""
import logging
from pymodbus.server import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.device import ModbusDeviceIdentification
import threading

logger = logging.getLogger("ModbusServer")

class TRINETRAModbusServer:
    """
    A Modbus TCP Slave server embedded in the TRINETRA backend.
    OpenPLC acts as Modbus Master and polls this server for physics data.
    """

    def __init__(self, port: int = 5502):
        self.port = port
        self._thread = None
        self._context = None
        self._setup_datastore()

    def _setup_datastore(self):
        """Initialize Modbus data store with zeroed registers."""
        store = ModbusSlaveContext(
            di=ModbusSequentialDataBlock(0, [0] * 100),   # Discrete Inputs
            co=ModbusSequentialDataBlock(0, [0] * 100),   # Coils
            hr=ModbusSequentialDataBlock(0, [0] * 100),   # Holding Registers
            ir=ModbusSequentialDataBlock(0, [0] * 100),   # Input Registers
        )
        self._context = ModbusServerContext(slaves=store, single=True)

    def update_voltage(self, voltage_pu: float):
        """Write voltage (pu) into register 0 as integer * 100."""
        scaled = int(voltage_pu * 100)
        self._context[0].setValues(3, 0, [scaled])   # FC3 = Holding Register

    def update_coil(self, address: int, value: bool):
        """Update a coil (used for grid_online etc.)."""
        self._context[0].setValues(1, address, [1 if value else 0])

    def get_coil(self, address: int) -> bool:
        """Read a coil value (used to check breaker commands from PLC)."""
        vals = self._context[0].getValues(1, address, count=1)
        return bool(vals[0]) if vals else False

    def start(self):
        """Start the Modbus TCP server in a background thread."""
        def run():
            logger.info(f"TRINETRA Modbus Server listening on port {self.port}...")
            StartTcpServer(
                context=self._context,
                address=("0.0.0.0", self.port)
            )
        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        logger.info(f"Modbus Server thread started on port {self.port}")

    def stop(self):
        """Gracefully stop the Modbus TCP server."""
        try:
            from pymodbus.server import ServerStop
            ServerStop()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
            logger.info(f"TRINETRA Modbus Server stopped on port {self.port}")
        except Exception as e:
            logger.error(f"Error stopping Modbus Server: {e}")
