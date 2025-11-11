import RPi.GPIO as GPIO
import yaml
import time

from questdb.ingress import Sender, Protocol
from datetime import datetime

import socket
import os

conf = (
    'http::addr=localhost:9000;'
    'username=admin;'
    'password=quest;'
    'auto_flush=on;'
    'auto_flush_rows=1;'
    )

module_path = os.path.abspath(__file__)
module_directory = os.path.dirname(module_path)

CONFIG_FILE_NAME = f"{module_directory}/config.yaml"
with open(CONFIG_FILE_NAME, 'r') as file:
    config = yaml.safe_load(file)

num_enabled_pis = 0
enabled_pis = []
for pi_id in config["PIs"]:
    if config["PIs"][pi_id]["enabled"]:
        enabled_pis.append(pi_id)

num_enabled_pis = len(enabled_pis)

RELAY_PINS = [5, 6, 13, 16, 19, 20, 21, 26]

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
for pin in RELAY_PINS:
    GPIO.setup(pin, GPIO.OUT)

# Define the server's IP address and port
host = '0.0.0.0'  # Accept connections from any IP address
port = 9600        # Same port as in the client

# Create a TCP/IP socket
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Bind the socket to the address and port
server_socket.bind((host, port))

# Enable the server to accept connections (max 1 connection in the backlog queue)
server_socket.listen(1)

print(f"Server listening on {host}:{port}...")

COSMO_socket = None
COSMO_address = None

worker_pi_sockets = [None] * enabled_pis
worker_pi_addresses = [None] * enabled_pis

# # Accept incoming client connections
connected_pis = 0
COSMO_connected = False
while connected_pis < enabled_pis and not COSMO_connected:
    client_socket, client_address = server_socket.accept()
    print(f"Connection established with {client_address}")

    if config["COSMO"]["ip"] == client_address:
        COSMO_socket = client_socket
        COSMO_address = COSMO_address
        COSMO_connected = True

    for pi_id in config["PIs"]:
        if client_address == config["PIs"][pi_id]["ip"]:
            worker_pi_sockets[pi_id-1] = client_socket
            worker_pi_addresses[pi_id-1] = client_address
            connected_pis += 1
    
switch_states = {}

with Sender.from_conf(conf) as sender:
    try:
        while True:
            success = False
            # Receive data from COSMO (up to 1024 bytes at a time)
            msg = COSMO_socket.recv(1024)

            # If there's no data, break the loop
            if not msg:
                print("No data received. Closing connection.")
                break

            # Decode the received data
            msg = msg.decode().strip()
            print(f"Received data: {msg}")

            try:

                # decode command
                if msg[0].isdigit():
                    switch_info = msg.split(' ')

                    if not switch_info[0].isnumeric():
                        raise ValueError(f"Switch id <{switch_info[0]}> not numeric")
                    
                    switch_id = switch_info[0]

                    if switch_info[1] == "Open" or switch_info[1] == "Close":
                        state_open = (switch_info[1] == "Open")
                    else:
                        raise ValueError(f"{switch_id} not open or closed")
                    
                elif msg == "ENABLE FIRE" or msg == "DISABLE FIRE":
                    switch_id = "enable_fire"
                    state_open = (msg == "ENABLE FIRE")

                elif msg == "FIRE":
                    switch_id = "fire"
                    state_open = True

                else:
                    raise ValueError(f"Unexpected Command")
                

                # get config info based on command
                pi_id = config["switches"][str(switch_id)]["Pi"]
                relay = config["switches"][str(switch_id)]["Relay"]


                if not config["PIs"][pi_id]["controller"]:
                    # send to worker pi
                    # TODO: wait for ACK from worker pi
                    pi_socket = worker_pi_sockets[pi_id]
                    pi_socket.send(f"R{relay} {state_open}".encode())

                    # check for response
                    response_ack = False
                    while not response_ack:
                        # if no response within a second, retry send message
                        if time.time() - send_time >= 0.2:
                            pi_socket.send(f"{relay} {state_open}".encode())
                            send_time = time.time()
                            attempts += 1

                        # if no response after 5 attempts give up
                        if attempts > 5:
                            print(f"No response | msg:<{msg}>")
                            break
                        # check for response
                        response_msg = pi_socket.recv(1024).decode().strip()
                        response_ack = (response_msg == f"ACK: {msg.decode().strip()}")
                    
                    success = response_ack

                elif config["PIs"][pi_id]["controller"]:
                    if state_open:
                        GPIO.output(RELAY_PINS[relay-1], GPIO.HIGH)
                    else:
                        GPIO.output(RELAY_PINS[relay-1], GPIO.LOW)
                    success = True
                
                if success:
                    switch_states[switch_id] = state_open

            except ValueError as e:
                print(f"{e} \n\n CMD: <{msg}>")

            if success:
                sender.row(
                    'controls_data',
                    columns = {
                        switch: switch_states[switch] for switch in switch_states
                    },
                    at=datetime.now()
                )

            # respond to COSMO
                COSMO_socket.send(f"ACK: {msg}".encode())
            else:
                print(f"unsuccessful: <{msg}>")

    except KeyboardInterrupt:
        print("Server interrupted by user.")

    finally:
        # Make sure all Relays are off, close the client socket and server socket
        print("Shutting off Relays...")
        for pin in RELAY_PINS:
            GPIO.output(pin, GPIO.LOW)
       
        print("Closing connection...")
        COSMO_socket.close()

        for worker_pi_socket in worker_pi_sockets:
            worker_pi_socket.close()

        server_socket.close()

