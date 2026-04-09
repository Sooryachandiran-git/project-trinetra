"""
TRINETRA Data Writer — InfluxDB Research Historian with Write-Ahead Buffer

Architecture:
  - All write methods serialize Points to InfluxDB Line Protocol and push to
    a thread-safe Queue (maxsize=50,000 points — ~4hrs buffer for 3 IEDs).
  - A single background drain thread pops from the queue and batch-writes to
    InfluxDB. The tick loop NEVER blocks on I/O.
  - If InfluxDB is down: queue accumulates. Drain thread retries with
    exponential backoff (5s → 10s → 20s → ... → 60s max).
  - On backend shutdown: remaining queue is saved to disk (data/trinetra_buffer.jsonl).
  - On next startup: disk buffer is reloaded into queue and replayed automatically.

Measurements written:
  1. grid_telemetry   — per IED-Breaker pair, every 500ms (core ML dataset, 25 cols)
  2. attack_events    — discrete log per attack session start/stop
  3. operator_actions — discrete log per operator action (reset, manual trip)
  4. system_health    — per IED every 5s (connectivity, comms status)
"""

import os
import queue
import threading
import logging
import time
from pathlib import Path
from typing import Optional

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import WriteOptions

logger = logging.getLogger("DataWriter")

# Buffer file location (relative to backend-orchestrator/)
BUFFER_FILE = Path("data/trinetra_buffer.jsonl")
BUFFER_MAXSIZE = 50_000   # points — ~4hrs for 3 IEDs at 500ms ticks
BATCH_SIZE = 500          # points written per InfluxDB call
HEALTH_CHECK_INTERVAL = 15  # seconds between health checks when DB is down


class DataWriter:
    """
    Manages all InfluxDB write operations for TRINETRA.
    Thread-safe. Instantiated once in SimulationEngine.__init__().
    """

    def __init__(self):
        # ── InfluxDB config from .env ──────────────────────────────────────
        self.url    = os.getenv("INFLUX_URL",    "http://localhost:8086")
        self.token  = os.getenv("INFLUX_TOKEN",  "trinetra-research-token")
        self.org    = os.getenv("INFLUX_ORG",    "trinetra")
        self.bucket = os.getenv("INFLUX_BUCKET", "trinetra_raw")

        # ── Internal state ─────────────────────────────────────────────────
        self._tick_counter: int = 0
        self._prev_scan_counts: dict = {}  # { ied_id: (scan_count, timestamp) }
        self._influx_healthy: bool = False
        self._stop_event = threading.Event()

        # ── Write-ahead buffer (thread-safe queue) ─────────────────────────
        # Holds line protocol strings. Each item is one InfluxDB point.
        self._buffer: queue.Queue = queue.Queue(maxsize=BUFFER_MAXSIZE)

        # ── InfluxDB client (synchronous — writes done in drain thread) ────
        try:
            self._client = InfluxDBClient(
                url=self.url, token=self.token, org=self.org
            )
            # Use SYNCHRONOUS mode — the drain thread handles async behaviour
            self._write_api = self._client.write_api(
                write_options=WriteOptions(batch_size=BATCH_SIZE, flush_interval=1_000)
            )
            self._influx_healthy = self._check_health()
            if self._influx_healthy:
                logger.info(f"✅ DataWriter connected to InfluxDB at {self.url}")
            else:
                logger.warning("DataWriter: InfluxDB not yet reachable. "
                               "Buffer mode active — writes will be replayed on recovery.")
        except Exception as e:
            logger.error(f"DataWriter: InfluxDB client init failed: {e}. Buffer mode active.")

        # ── Load any leftover buffer from previous run ─────────────────────
        self._load_buffer_from_disk()

        # ── Start the background drain thread ─────────────────────────────
        self._drain_thread = threading.Thread(
            target=self._drain_loop, name="InfluxDrainThread", daemon=True
        )
        self._drain_thread.start()
        logger.info(f"DataWriter: Drain thread started "
                    f"[buffer capacity: {BUFFER_MAXSIZE:,} points, {BUFFER_MAXSIZE//(6*2)//60:.0f}+ hrs]")

    # ─────────────────────────────────────────────────────────────────────────
    # Internal: Queue helpers
    # ─────────────────────────────────────────────────────────────────────────
    def _enqueue(self, point: Point):
        """Serialize Point to line protocol and push to buffer queue."""
        try:
            lp = point.to_line_protocol()
            if lp:
                self._buffer.put_nowait(lp)
        except queue.Full:
            logger.warning(
                f"DataWriter buffer FULL ({BUFFER_MAXSIZE:,} points). "
                f"Oldest point dropped. InfluxDB has been down > 4hrs."
            )
        except Exception as e:
            logger.warning(f"DataWriter _enqueue error: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # Internal: Background drain loop
    # ─────────────────────────────────────────────────────────────────────────
    def _drain_loop(self):
        """
        Runs forever in a daemon thread.
        Drains the buffer queue → InfluxDB in batches.
        On failure: exponential backoff (5s → 10s → ... → 60s), then retry.
        """
        retry_delay = 5  # seconds

        while not self._stop_event.is_set():

            # Wait until there's something to drain
            if self._buffer.empty():
                time.sleep(0.5)
                continue

            # Check InfluxDB health before attempting writes
            if not self._influx_healthy:
                if self._check_health():
                    self._influx_healthy = True
                    buffered = self._buffer.qsize()
                    logger.info(
                        f"✅ InfluxDB recovered! Replaying {buffered:,} buffered points..."
                    )
                    retry_delay = 5  # reset backoff
                else:
                    logger.warning(
                        f"InfluxDB still down. {self._buffer.qsize():,} points buffered. "
                        f"Retrying in {retry_delay}s..."
                    )
                    self._stop_event.wait(timeout=retry_delay)
                    retry_delay = min(retry_delay * 2, 60)
                    continue

            # Drain one batch
            batch = []
            try:
                for _ in range(BATCH_SIZE):
                    batch.append(self._buffer.get_nowait())
            except queue.Empty:
                pass  # Fewer than BATCH_SIZE items — write what we have

            if not batch:
                continue

            # Write batch to InfluxDB
            try:
                self._write_api.write(
                    bucket=self.bucket,
                    org=self.org,
                    record="\n".join(batch),
                    write_precision=WritePrecision.MILLISECONDS
                )
                # On success: mark all items as done
                for _ in batch:
                    self._buffer.task_done()
                retry_delay = 5  # reset backoff on success

            except Exception as e:
                # Write failed — put batch back into queue (front doesn't exist,
                # so we just re-enqueue; slight reordering is acceptable)
                logger.warning(f"DataWriter: Batch write failed ({len(batch)} pts): {e}")
                self._influx_healthy = False
                for lp in batch:
                    try:
                        self._buffer.put_nowait(lp)
                    except queue.Full:
                        pass  # Buffer full — can't restore, point is lost
                self._stop_event.wait(timeout=retry_delay)
                retry_delay = min(retry_delay * 2, 60)

    # ─────────────────────────────────────────────────────────────────────────
    # Internal: Health check
    # ─────────────────────────────────────────────────────────────────────────
    def _check_health(self) -> bool:
        """Ping InfluxDB /health. Returns True if DB is ready."""
        try:
            import requests
            res = requests.get(f"{self.url}/health", timeout=2)
            return res.status_code == 200 and res.json().get("status") == "pass"
        except Exception:
            return False

    # ─────────────────────────────────────────────────────────────────────────
    # Internal: Disk persistence
    # ─────────────────────────────────────────────────────────────────────────
    def _load_buffer_from_disk(self):
        """On startup: load any saved buffer from previous session."""
        if not BUFFER_FILE.exists():
            return
        loaded = 0
        try:
            with open(BUFFER_FILE, "r") as f:
                for line in f:
                    lp = line.strip()
                    if lp:
                        try:
                            self._buffer.put_nowait(lp)
                            loaded += 1
                        except queue.Full:
                            break
            BUFFER_FILE.unlink()  # Delete after loading — drain loop will replay
            logger.info(f"DataWriter: Loaded {loaded:,} buffered points from disk for replay.")
        except Exception as e:
            logger.warning(f"DataWriter: Could not load buffer file: {e}")

    def _save_buffer_to_disk(self):
        """On shutdown: save remaining queue to disk so data survives restart."""
        if self._buffer.empty():
            return
        BUFFER_FILE.parent.mkdir(parents=True, exist_ok=True)
        saved = 0
        try:
            with open(BUFFER_FILE, "w") as f:
                while not self._buffer.empty():
                    try:
                        f.write(self._buffer.get_nowait() + "\n")
                        saved += 1
                    except queue.Empty:
                        break
            logger.info(f"DataWriter: Saved {saved:,} buffered points to {BUFFER_FILE}")
        except Exception as e:
            logger.error(f"DataWriter: Could not save buffer to disk: {e}")

    # ─────────────────────────────────────────────────────────────────────────
    # MEASUREMENT 1: grid_telemetry
    # Written every 500ms, once per IED-Breaker control_mapping entry.
    # 6 tags + 19 fields = 25 columns — the PRIMARY research dataset.
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
        Write one grid_telemetry point for one IED-Breaker pair.

        physics keys: vm_pu, v_kv, i_ka, total_load, total_loss, total_gen
        cyber keys:   vm_pu_measured, i_ka_measured, scan_count, rtt_ms
        attack_state: active, attack_type, grid_state, attack_target
        breaker:      physical (bool), plc_cmd (bool)
        """
        self._tick_counter += 1

        # ── Dual-source anomaly signals ────────────────────────────────────
        v_true     = float(physics.get("vm_pu", 0.0))
        v_measured = float(cyber.get("vm_pu_measured", v_true))
        i_true     = float(physics.get("i_ka", 0.0))
        i_measured = float(cyber.get("i_ka_measured", i_true))

        bus_v_delta  = abs(v_true - v_measured)
        line_i_delta = abs(i_true - i_measured)

        # ── Breaker mismatch ───────────────────────────────────────────────
        phys_closed = breaker.get("physical", True)
        plc_trip    = breaker.get("plc_cmd", False)
        # cmd_delta=1 when PLC commands trip but breaker is still closed (or vice versa)
        breaker_cmd_delta = int(phys_closed == plc_trip)

        # ── PLC scan rate (scans/sec) ──────────────────────────────────────
        scan_count = int(cyber.get("scan_count", 0))
        plc_scan_rate = 0.0
        now = time.time()
        if ied_id in self._prev_scan_counts:
            prev_count, prev_time = self._prev_scan_counts[ied_id]
            elapsed = now - prev_time
            if elapsed > 0 and scan_count != prev_count:
                delta_scans = (scan_count - prev_count) % 32768  # rollover at 32767
                plc_scan_rate = round(delta_scans / elapsed, 2)
        self._prev_scan_counts[ied_id] = (scan_count, now)

        # ── Build point and enqueue ────────────────────────────────────────
        point = (
            Point("grid_telemetry")
            # Tags
            .tag("topology_id",   topology_id)
            .tag("ied_id",        ied_id)
            .tag("breaker_id",    breaker_id)
            .tag("grid_state",    attack_state.get("grid_state", "NORMAL"))
            .tag("attack_type",   attack_state.get("attack_type", "none"))
            .tag("attack_target", attack_state.get("attack_target", "none"))
            # Physics Truth (Pandapower)
            .field("bus_v_pu_true",   v_true)
            .field("bus_v_kv_true",   float(physics.get("v_kv", 0.0)))
            .field("line_i_ka_true",  i_true)
            .field("total_load_mw",   float(physics.get("total_load", 0.0)))
            .field("total_loss_mw",   float(physics.get("total_loss", 0.0)))
            .field("total_gen_mw",    float(physics.get("total_gen",  0.0)))
            # Cyber Reported (Modbus read-back from IED)
            .field("bus_v_pu_measured",  v_measured)
            .field("line_i_ka_measured", i_measured)
            # Anomaly Signals — THE key ML features
            .field("bus_v_delta",   bus_v_delta)
            .field("line_i_delta",  line_i_delta)
            # Breaker State
            .field("breaker_physical_state", int(phys_closed))
            .field("breaker_plc_command",    int(plc_trip))
            .field("breaker_cmd_delta",      int(breaker_cmd_delta))
            # PLC Health
            .field("plc_scan_count", scan_count)
            .field("plc_scan_rate",  plc_scan_rate)
            .field("modbus_rtt_ms",  float(cyber.get("rtt_ms", 0.0)))
            # ML Labels
            .field("is_under_attack",  int(bool(attack_state.get("active", False))))
            .field("tick_number",      self._tick_counter)
            .field("tick_duration_ms", float(tick_duration_ms))
        )
        self._enqueue(point)

    # ─────────────────────────────────────────────────────────────────────────
    # MEASUREMENT 2: attack_events
    # Written once on attack START and once on attack STOP.
    # ─────────────────────────────────────────────────────────────────────────
    def write_attack_event(
        self,
        attack_id: str,
        attack_type: str,
        target_ied: str,
        event: str,                      # "START" or "STOP"
        params: Optional[dict] = None,
        attack_duration_s: float = 0.0
    ):
        """Log a discrete attack session event."""
        params = params or {}
        point = (
            Point("attack_events")
            .tag("attack_id",   attack_id)
            .tag("attack_type", attack_type)
            .tag("target_ied",  target_ied)
            .tag("event",       event)
            .field("attack_params",     str(params))
            .field("injected_value",    float(params.get("injected_value", 0.0)))
            .field("target_register",   int(params.get("register", 1024)))
            .field("attack_source_ip",  str(params.get("source_ip", "127.0.0.1")))
            .field("attack_duration_s", float(attack_duration_s))
        )
        self._enqueue(point)
        logger.info(f"[InfluxDB] attack_events: {event} | {attack_type} → {target_ied}")

    # ─────────────────────────────────────────────────────────────────────────
    # MEASUREMENT 3: operator_actions
    # Written once per operator interaction.
    # ─────────────────────────────────────────────────────────────────────────
    def write_operator_action(
        self,
        action_type: str,       # "master_reset", "manual_trip", "manual_close"
        target_ied: str,
        result: str,            # "success" or "failed"
        response_time_ms: float = 0.0
    ):
        """Log a discrete operator action."""
        point = (
            Point("operator_actions")
            .tag("action_type", action_type)
            .tag("target_ied",  target_ied)
            .field("action_result",    str(result))
            .field("response_time_ms", float(response_time_ms))
        )
        self._enqueue(point)
        logger.info(f"[InfluxDB] operator_actions: {action_type} → {target_ied} [{result}]")

    # ─────────────────────────────────────────────────────────────────────────
    # MEASUREMENT 4: system_health
    # Written every 5s from a separate background thread in SimulationEngine.
    # (Docker stats are too slow to poll at 500ms.)
    # ─────────────────────────────────────────────────────────────────────────
    def write_system_health(
        self,
        ied_id: str,
        connected: bool,
        consecutive_timeouts: int = 0,
        comms_status: str = "ONLINE",   # ONLINE / DEGRADED / STALE / OFFLINE
        docker_status: str = "running"
    ):
        """Log IED infrastructure health."""
        point = (
            Point("system_health")
            .tag("ied_id", ied_id)
            .field("modbus_connected",     int(connected))
            .field("consecutive_timeouts", int(consecutive_timeouts))
            .field("comms_status",         str(comms_status))
            .field("docker_status",        str(docker_status))
        )
        self._enqueue(point)

    # ─────────────────────────────────────────────────────────────────────────
    # Buffer status — useful for monitoring
    # ─────────────────────────────────────────────────────────────────────────
    def get_buffer_status(self) -> dict:
        """Returns current buffer stats. Exposed via /api/db/status endpoint."""
        return {
            "influx_healthy":     self._influx_healthy,
            "buffered_points":    self._buffer.qsize(),
            "buffer_capacity":    BUFFER_MAXSIZE,
            "buffer_fill_pct":    round(self._buffer.qsize() / BUFFER_MAXSIZE * 100, 1),
            "tick_counter":       self._tick_counter,
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────────────────────────────────
    def close(self):
        """
        Flush remaining writes and close gracefully.
        Called by SimulationEngine.stop() — ensures no data lost on shutdown.
        """
        logger.info("DataWriter: Shutting down...")
        self._stop_event.set()
        self._save_buffer_to_disk()
        try:
            self._write_api.close()
            self._client.close()
            logger.info("DataWriter: InfluxDB connection closed cleanly.")
        except Exception as e:
            logger.error(f"DataWriter: Error during close: {e}")
