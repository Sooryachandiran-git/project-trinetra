"""
TRINETRA Data Writer — InfluxDB Research Historian

Writes 4 measurements to InfluxDB:
  1. grid_telemetry   — per IED-Breaker pair, every 500ms tick (core ML dataset)
  2. attack_events    — discrete log per attack start/stop
  3. operator_actions — discrete log per operator action (reset, manual trip)
  4. system_health    — per IED every 5s (Modbus connectivity, comms status)

All writes are ASYNCHRONOUS — fire-and-forget, zero impact on the 500ms tick loop.
"""

import os
import logging
import time
from typing import Optional
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import ASYNCHRONOUS

logger = logging.getLogger("DataWriter")


class DataWriter:
    """
    Manages all InfluxDB write operations for TRINETRA.
    Instantiated once in SimulationEngine.__init__() and lives for the
    lifetime of the backend process.
    """

    def __init__(self):
        # Read config from .env (loaded by uvicorn at startup)
        self.url    = os.getenv("INFLUX_URL",    "http://localhost:8086")
        self.token  = os.getenv("INFLUX_TOKEN",  "trinetra-research-token")
        self.org    = os.getenv("INFLUX_ORG",    "trinetra")
        self.bucket = os.getenv("INFLUX_BUCKET", "trinetra_raw")

        # Internal state
        self._tick_counter: int = 0
        self._prev_scan_counts: dict = {}   # { ied_id: (scan_count, timestamp) }
        self._available: bool = False

        # Connect
        try:
            self._client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org
            )
            # ASYNCHRONOUS: writes are batched and sent in background thread
            # The tick loop never waits for InfluxDB — zero latency impact
            self._write_api = self._client.write_api(write_options=ASYNCHRONOUS)
            self._available = True
            logger.info(f"✅ DataWriter connected to InfluxDB at {self.url} "
                        f"[org={self.org}, bucket={self.bucket}]")
        except Exception as e:
            logger.error(f"DataWriter failed to connect to InfluxDB: {e}. "
                         f"Simulation will run without data persistence.")

    # ─────────────────────────────────────────────────────────────────────────
    # MEASUREMENT 1: grid_telemetry
    # Written every 500ms, once per IED-Breaker control_mapping entry.
    # This is the PRIMARY research dataset — 6 tags + 19 fields = 25 columns.
    # ─────────────────────────────────────────────────────────────────────────
    def write_telemetry(
        self,
        ied_id: str,
        breaker_id: str,
        topology_id: str,
        physics: dict,
        cyber: dict,
        attack_state: dict,
        breaker: dict,
        tick_duration_ms: float = 0.0
    ):
        """
        Write one grid_telemetry data point for one IED-Breaker pair.

        Args:
            ied_id:          IED identifier (e.g. "node_abc123")
            breaker_id:      Breaker this IED controls (e.g. "node_brk456")
            topology_id:     Run label (e.g. "3bus_fdia_test_1712600000")
            physics: {
                vm_pu:       float — Pandapower truth voltage at IED's monitored bus
                v_kv:        float — Absolute kV truth
                i_ka:        float — Line current truth (kA)
                total_load:  float — Sum of all load active power (MW)
                total_loss:  float — Sum of all line losses (MW)
                total_gen:   float — External grid generation (MW)
            }
            cyber: {
                vm_pu_measured: float — Modbus read-back from IED reg 1024 / 1000
                i_ka_measured:  float — Modbus read-back from IED reg 1025 / 1000
                scan_count:     int   — Modbus read from reg 24 (%QW24)
                rtt_ms:         float — Round-trip time of the Modbus read (ms)
            }
            attack_state: {
                active:       bool   — Is an attack currently running?
                attack_type:  str    — e.g. "fdia_overvoltage", "none"
                grid_state:   str    — "NORMAL", "UNDER_ATTACK", "BLACKOUT"
                attack_target: str   — e.g. "register_mw0", "none"
            }
            breaker: {
                physical: bool — Pandapower net.switch.closed state (truth)
                plc_cmd:  bool — Modbus coil read (%QX0.0) — PLC's output
            }
            tick_duration_ms: Actual time the current tick took to run
        """
        if not self._available:
            return

        self._tick_counter += 1

        # ── Compute derived fields ──────────────────────────────────────────
        v_true     = physics.get("vm_pu", 0.0)
        v_measured = cyber.get("vm_pu_measured", v_true)
        i_true     = physics.get("i_ka", 0.0)
        i_measured = cyber.get("i_ka_measured", i_true)

        bus_v_delta  = abs(v_true - v_measured)
        line_i_delta = abs(i_true - i_measured)

        phys_closed = breaker.get("physical", True)
        plc_trip    = breaker.get("plc_cmd", False)
        # cmd_delta: 1 when PLC commands trip but breaker is still closed, OR vice versa
        breaker_cmd_delta = int(phys_closed == plc_trip)  # mismatch when both same

        # ── PLC Scan Rate ───────────────────────────────────────────────────
        scan_count = cyber.get("scan_count", 0)
        plc_scan_rate = 0.0
        now = time.time()
        if ied_id in self._prev_scan_counts:
            prev_count, prev_time = self._prev_scan_counts[ied_id]
            elapsed = now - prev_time
            if elapsed > 0 and scan_count != prev_count:
                delta_scans = (scan_count - prev_count) % 32768  # handle rollover at 32767
                plc_scan_rate = round(delta_scans / elapsed, 2)
        self._prev_scan_counts[ied_id] = (scan_count, now)

        # ── Build the InfluxDB Point ────────────────────────────────────────
        try:
            point = (
                Point("grid_telemetry")
                # ── Tags (indexed — used for filtering queries) ──
                .tag("topology_id",    topology_id)
                .tag("ied_id",         ied_id)
                .tag("breaker_id",     breaker_id)
                .tag("grid_state",     attack_state.get("grid_state", "NORMAL"))
                .tag("attack_type",    attack_state.get("attack_type", "none"))
                .tag("attack_target",  attack_state.get("attack_target", "none"))

                # ── Physics Truth (Pandapower) ───────────────────
                .field("bus_v_pu_true",   float(v_true))
                .field("bus_v_kv_true",   float(physics.get("v_kv", 0.0)))
                .field("line_i_ka_true",  float(i_true))
                .field("total_load_mw",   float(physics.get("total_load", 0.0)))
                .field("total_loss_mw",   float(physics.get("total_loss", 0.0)))
                .field("total_gen_mw",    float(physics.get("total_gen", 0.0)))

                # ── Cyber Reported (Modbus Read-back) ────────────
                .field("bus_v_pu_measured",  float(v_measured))
                .field("line_i_ka_measured", float(i_measured))

                # ── Anomaly Signals (THE KEY ML FEATURES) ────────
                .field("bus_v_delta",   float(bus_v_delta))
                .field("line_i_delta",  float(line_i_delta))

                # ── Breaker State ─────────────────────────────────
                .field("breaker_physical_state", int(phys_closed))
                .field("breaker_plc_command",    int(plc_trip))
                .field("breaker_cmd_delta",      int(breaker_cmd_delta))

                # ── PLC Health ────────────────────────────────────
                .field("plc_scan_count", int(scan_count))
                .field("plc_scan_rate",  float(plc_scan_rate))
                .field("modbus_rtt_ms",  float(cyber.get("rtt_ms", 0.0)))

                # ── ML Labels ────────────────────────────────────
                .field("is_under_attack",  int(attack_state.get("active", False)))
                .field("tick_number",      int(self._tick_counter))
                .field("tick_duration_ms", float(tick_duration_ms))
            )

            self._write_api.write(
                bucket=self.bucket,
                org=self.org,
                record=point,
                write_precision=WritePrecision.MILLISECONDS
            )

        except Exception as e:
            logger.warning(f"DataWriter: grid_telemetry write failed for {ied_id}: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # MEASUREMENT 2: attack_events
    # Written once when an attack starts and once when it stops.
    # ─────────────────────────────────────────────────────────────────────────
    def write_attack_event(
        self,
        attack_id: str,
        attack_type: str,
        target_ied: str,
        event: str,              # "START" or "STOP"
        params: Optional[dict] = None,
        attack_duration_s: float = 0.0
    ):
        """Log a discrete attack session event (start or stop)."""
        if not self._available:
            return

        params = params or {}
        try:
            point = (
                Point("attack_events")
                .tag("attack_id",   attack_id)
                .tag("attack_type", attack_type)
                .tag("target_ied",  target_ied)
                .tag("event",       event)          # "START" or "STOP"
                .field("attack_params",     str(params))
                .field("injected_value",    float(params.get("injected_value", 0.0)))
                .field("target_register",   int(params.get("register", 1024)))
                .field("attack_source_ip",  str(params.get("source_ip", "127.0.0.1")))
                .field("attack_duration_s", float(attack_duration_s))
            )
            self._write_api.write(bucket=self.bucket, org=self.org, record=point,
                                  write_precision=WritePrecision.MILLISECONDS)
            logger.info(f"[InfluxDB] attack_events: {event} | {attack_type} → {target_ied}")
        except Exception as e:
            logger.warning(f"DataWriter: attack_events write failed: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # MEASUREMENT 3: operator_actions
    # Written once per operator interaction (master reset, manual trip, etc.)
    # ─────────────────────────────────────────────────────────────────────────
    def write_operator_action(
        self,
        action_type: str,        # "master_reset", "manual_trip", "manual_close"
        target_ied: str,
        result: str,             # "success" or "failed"
        response_time_ms: float = 0.0
    ):
        """Log a discrete operator action event."""
        if not self._available:
            return

        try:
            point = (
                Point("operator_actions")
                .tag("action_type", action_type)
                .tag("target_ied",  target_ied)
                .field("action_result",     str(result))
                .field("response_time_ms",  float(response_time_ms))
            )
            self._write_api.write(bucket=self.bucket, org=self.org, record=point,
                                  write_precision=WritePrecision.MILLISECONDS)
            logger.info(f"[InfluxDB] operator_actions: {action_type} → {target_ied} [{result}]")
        except Exception as e:
            logger.warning(f"DataWriter: operator_actions write failed: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # MEASUREMENT 4: system_health
    # Written every 5 seconds from a background thread (NOT per 500ms tick).
    # Docker stats (CPU/memory) are too slow to poll at 500ms.
    # ─────────────────────────────────────────────────────────────────────────
    def write_system_health(
        self,
        ied_id: str,
        connected: bool,
        consecutive_timeouts: int = 0,
        comms_status: str = "ONLINE",   # ONLINE / DEGRADED / STALE / OFFLINE
        docker_status: str = "running"
    ):
        """Log IED connectivity and infrastructure health."""
        if not self._available:
            return

        try:
            point = (
                Point("system_health")
                .tag("ied_id", ied_id)
                .field("modbus_connected",      int(connected))
                .field("consecutive_timeouts",  int(consecutive_timeouts))
                .field("comms_status",          str(comms_status))
                .field("docker_status",         str(docker_status))
            )
            self._write_api.write(bucket=self.bucket, org=self.org, record=point,
                                  write_precision=WritePrecision.MILLISECONDS)
        except Exception as e:
            logger.warning(f"DataWriter: system_health write failed for {ied_id}: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────────────────────
    def close(self):
        """Flush all pending async writes and close the InfluxDB connection.
        Called by SimulationEngine.stop() to ensure no data is lost on shutdown."""
        if not self._available:
            return
        try:
            self._write_api.close()   # Flushes the async write buffer
            self._client.close()
            logger.info("DataWriter: InfluxDB connection closed cleanly.")
        except Exception as e:
            logger.error(f"DataWriter: Error during close: {e}")
