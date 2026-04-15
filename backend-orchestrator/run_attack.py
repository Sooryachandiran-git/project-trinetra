import os
import sys
import time
import argparse
import subprocess
import requests

def notify_historian(port: int, attack_type: str, active: bool):
    try:
        requests.post("http://127.0.0.1:8000/api/attack/ml_label", json={
            "port": port,
            "attack_type": attack_type,
            "active": active
        }, timeout=2)
    except Exception as e:
        print(f"[!] Warning: Could not reach Backend API for Historian Labeling: {e}")

def main():
    parser = argparse.ArgumentParser(description="Wrapper to run attack scripts and tag the InfluxDB ML Historian.")
    parser.add_argument("--attack_type", type=str, required=True, help="Name of the attack for the ML dataset (e.g., atk02)")
    parser.add_argument("--port", type=int, default=5020, help="Target IED Port (used to map the attack internally)")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="The python execution command and args")

    args = parser.parse_args()

    cmd = args.command
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]

    if not cmd:
        print("[-] Usage: python run_attack.py --attack_type atk02 --port 5020 -- python attacks/atk02_undervoltage_masking.py ...")
        sys.exit(1)

    print(f"[*] Registering Attack '{args.attack_type}' with InfluxDB Historian...")
    notify_historian(args.port, args.attack_type, active=True)
    time.sleep(1) # Let the DB record the start event fully

    print(f"[*] Executing Attack Payload: {' '.join(cmd)}")
    
    try:
        # Pass through to the real script directly!
        process = subprocess.Popen(cmd)
        process.wait()
    except KeyboardInterrupt:
        process.terminate()
        process.wait()
    except Exception as e:
        print(f"[-] Error: {e}")
    finally:
        print(f"\n[*] Attack complete. Notifying Historian to remove ML labels...")
        notify_historian(args.port, args.attack_type, active=False)

if __name__ == "__main__":
    main()
