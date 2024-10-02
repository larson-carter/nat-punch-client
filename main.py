import socket
import requests
import time
import threading
import stun


def get_public_ip_port():
    # Use STUN to get public IP and port
    nat_type, external_ip, external_port = stun.get_ip_info()
    if external_ip and external_port:
        print(f"Public IP: {external_ip}, Public Port: {external_port}")
        return external_ip, external_port
    else:
        raise Exception("Failed to get public IP and port from STUN")


def register_with_server(client_id, public_ip, public_port, server_url):
    payload = {
        'client_id': client_id,
        'public_ip': public_ip,
        'public_port': public_port
    }
    response = requests.post(f"{server_url}/api/register", json=payload)
    if response.status_code == 200:
        print(f"Successfully registered as {client_id}")
    else:
        print(f"Failed to register: {response.content}")


def send_heartbeat(client_id, server_url):
    while True:
        payload = {'client_id': client_id}
        response = requests.post(f"{server_url}/api/heartbeat", json=payload)
        if response.status_code == 200:
            print(f"Heartbeat sent for {client_id}")
        else:
            print(f"Failed to send heartbeat: {response.content}")

        time.sleep(5)  # Send heartbeat every 5 seconds


def udp_hole_punching(my_port, peer_ip, peer_port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('0.0.0.0', my_port))

    print(f"Attempting to connect to {peer_ip}:{peer_port}")

    # Retry sending the message multiple times
    retries = 10  # Increase the number of retries
    for attempt in range(retries):
        print(f"Sending message to {peer_ip}:{peer_port}, attempt {attempt + 1}/{retries}")
        sock.sendto(b"Hello from behind NAT!", (peer_ip, peer_port))
        time.sleep(5)  # Increase wait time to 5 seconds between retries

    try:
        # Listen for response
        sock.settimeout(20)  # Increase timeout for receiving a response
        data, addr = sock.recvfrom(1024)
        print(f"Received message from {addr}: {data.decode()}")
    except socket.timeout:
        print("Did not receive any response, connection might have failed.")


if __name__ == "__main__":
    server_url = "https://nat-puncher.carter.tech"  # Your Laravel server URL

    # Get public IP and port using STUN
    try:
        public_ip, public_port = get_public_ip_port()
    except Exception as e:
        print(f"Error getting public IP and port: {e}")
        exit(1)

    # Ask user if they want to change the port
    change_port = input(f"STUN selected port {public_port}. Do you want to change it? (yes/no): ").strip().lower()

    if change_port == "yes":
        try:
            public_port = int(input("Enter the custom port you want to use: ").strip())
            print(f"Using custom port: {public_port}")
        except ValueError:
            print("Invalid port number, using the STUN-selected port.")

    client_id = input("Enter client ID (A or B): ").strip()
    peer_id = "B" if client_id == "A" else "A"

    # Register with Laravel server
    register_with_server(client_id, public_ip, public_port, server_url)

    # Start sending heartbeats in a separate thread
    threading.Thread(target=send_heartbeat, args=(client_id, server_url)).start()

    # Get peer info (to implement NAT punching)
    response = requests.get(f"{server_url}/api/peer-info/{peer_id}")
    if response.status_code == 200:
        peer_info = response.json()
        print(f"Peer info received: IP={peer_info['public_ip']}, Port={peer_info['public_port']}")
        udp_hole_punching(public_port, peer_info['public_ip'], peer_info['public_port'])
    else:
        print(f"Failed to get peer info: {response.content}")

