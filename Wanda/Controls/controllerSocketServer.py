import RPi.GPIO as GPIO
import yaml
import time

from questdb.ingress import Sender, Protocol
from datetime import datetime

import socket
import os

class WorkerPi:

    def __init__(self, id, client_ip_address, client_socket: socket):
        self.id = id
        self.client_ip_address = client_ip_address
        self.client_socket = client_socket

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


class WorkerPi:
    def __init__(self, id: int, client_ip_address, client_socket: socket):
        self.id = id
        self.client_ip_address = client_ip_address
        self.client_socket = client_socket
        self.relays = config["PIs"][pi_id]["relays"]


num_enabled_pis = 0
for pi_id in config["PIs"]:
    if config["PIs"][pi_id]["enabled"]:
        num_enabled_pis += 1

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
worker_pis = []

# Accept incoming client connections
num_connected_pis = 0
COSMO_connected = False
while num_connected_pis < num_enabled_pis-1 or not COSMO_connected:
    client_socket, client_address = server_socket.accept()
    print(f"Connection established with {client_address}")

    if client_address[0] == config["COSMO"]["ip"]:
        COSMO_socket = client_socket
        COSMO_address = COSMO_address
        COSMO_connected = True
        print("COSMO Connection Established")

    for pi_id in config["PIs"]:
        pi_id = pi_id
        if client_address[0] == config["PIs"][pi_id]["ip"]:
            client_socket.settimeout(0.2)
            worker_pi = WorkerPi(pi_id, client_address, client_socket)
            worker_pis.append(worker_pi)
            num_connected_pis += 1
            print(f"Pi {pi_id} Connection Established")
print("ALL CONNECTIONs ESTABLISHED")

switch_states = {}
abort = False

def decode_cmd(cmd: str):
    if len(cmd) == 0:
        raise ValueError(f"Empty CMD: <{cmd}>")

    # decode command
    cmd_lower = cmd.lower()
    if cmd[0].isdigit():
        switch_info = cmd_lower.split(' ')

        if not switch_info[0].isnumeric():
            raise ValueError(f"Switch id <{switch_info[0]}> not numeric")
        
        switch_id = int(switch_info[0])

        if switch_info[1] == "open" or switch_info[1] == "close":
            state_open = (switch_info[1] == "open".lower())
        else:
            raise ValueError(f"{switch_id} not open or closed")
        
    elif cmd_lower == "enable fire" or cmd_lower == "disable fire":
        switch_id = "ENABLE FIRE"
        state_open = (cmd_lower == "enable fire".lower())

    elif cmd_lower == "fire":
        switch_id = "FIRE"
        state_open = True

    elif cmd_lower == "abort open" or cmd_lower == "abort close":
        global abort
        abort = (cmd_lower == "abort open".lower())
        switch_id = 'ABORT'
        # state_open = not abort
        state_open = False

    else:
        raise ValueError(f"Unexpected Command")
    
    return switch_id, state_open
    

def get_affected_relays(switch_id, state_open):
    relays_changed = []
    for pi_id in config["PIs"]:
        pi = config["PIs"][pi_id]

        if not pi["enabled"]:
            continue

        for relay_id in pi["relays"]:
            relay = pi["relays"][relay_id]

            if relay["switch"] == switch_id or abort:
                # NOTE: all relays controlled by this switch would be set to the same state
                if abort:
                    state_open = False
                relays_changed.append({"pi":pi_id, "relay":relay_id, "state":state_open})

    return relays_changed


with Sender.from_conf(conf) as sender:
    print("Connected to Questdb")
    print(f"{'='*50}")
    try:
        while True:
            # Receive data from COSMO (up to 1024 bytes at a time)
            msg = COSMO_socket.recv(1024)

            # If there's no data, break the loop
            if not msg:
                print("No data received. Closing connection.")
                break

            # Decode the received data
            msg = msg.decode().strip()
            cmds = msg.rstrip(';').split(';')

            # print(f"Received data: {msg}")

            for cmd in cmds:
                print("="*50)
                print(f'CMD: <{cmd}>') 
                success = False
                try:
                    switch_id, state_open = decode_cmd(cmd)
                    relays_changed = get_affected_relays(switch_id, state_open)

                    for relay_data in relays_changed:
                        pi_id = relay_data["pi"]
                        relay = relay_data["relay"]
                        relay_open = relay_data["state"]
                        if pi_id == "contoller":
                            if relay_open:
                                GPIO.output(RELAY_PINS[relay-1], GPIO.HIGH)
                            else:
                                GPIO.output(RELAY_PINS[relay-1], GPIO.LOW)
                            print(f"Controller: Relay:{relay} State:{relay_open}")
                            success = True

                        else:
                            worker_pi_socket = None
                            for worker_pi in worker_pis:
                                if str(pi_id) == str(worker_pi.id):
                                    worker_pi_socket = worker_pi.client_socket
                            if worker_pi_socket == None:
                                print("no socket")
                                raise ValueError("No socket server retrieved")
                            else:

                                # check for response
                                response_ack = False
                                response_err = False
                                attempts = 0
                                while not (response_ack or response_err):
                                    print("-"*25)

                                    # clear socket buffer
                                    worker_pi_socket.setblocking(False)
                                    try:
                                        worker_pi_socket.recv(1024)
                                    except BlockingIOError:
                                        pass
                                    worker_pi_socket.setblocking(True)

                                    # if no response within a second, retry send message
                                    worker_pi_msg = f"{relay} {relay_open}"
                                    worker_pi_socket.send(f"{worker_pi_msg};".encode())
                                    print(f"Sent to Pi<{pi_id}>: <{worker_pi_msg}>")
                                    attempts += 1

                                    # if no response after 5 attempts give up
                                    if attempts > 5:
                                        print(f"No response | msg:<{worker_pi_msg}>")
                                        break
                                    # check for response
                                    try:
                                        response_msg = worker_pi_socket.recv(1024).decode().strip()
                                        responses = response_msg.rstrip(';').split(';')

                                        for response in responses:
                                            print(f"Recieved Response: <{response}>")
                                            response_ack = (response == f"ACK: {worker_pi_msg.strip()}")
                                            response_err = (response == f"ERR: {worker_pi_msg.strip()}")

                                            if response_ack or response_err:
                                                break

                                    except socket.timeout:
                                        print("Socket Timeout")
                                
                                success = response_ack

                    if success:
                        switch_states[switch_id] = state_open

                        sender.row(
                            'controls_data',
                            columns = {
                                str(switch): switch_states[switch] for switch in switch_states
                            },
                            at=datetime.now()
                        )

                        # respond to COSMO
                        print("Sending ACK")
                        COSMO_socket.send(f"ACK: {cmd};".encode())
                    else:
                        print(f"Sending ERR")
                        COSMO_socket.send(f"ERR: {cmd};".encode())

                except ValueError as e:
                    print('ERR')
                    print(f"{e} \n\n CMD: <{cmd}>")
                    COSMO_socket.send(f"ERR: {cmd};".encode())
                    continue


    except KeyboardInterrupt:
        print("Server interrupted by user.")

    finally:
        # Make sure all Relays are off, close the client socket and server socket
        print("Shutting off Relays...")
        for pin in RELAY_PINS:
            GPIO.output(pin, GPIO.LOW)
       
        print("Closing connection...")
        COSMO_socket.close()

        for worker_pi in worker_pis:
            worker_pi.client_socket.close()

        server_socket.close()

