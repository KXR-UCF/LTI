import RPi.GPIO as GPIO
import yaml
import time
import socket
import os

# from questdb.ingress import Sender, Protocol
from datetime import datetime
from pytz import timezone
est = timezone('US/Eastern')

from overrideCMD import OverrideManager


class WorkerPi:
    def __init__(self, id, client_ip_address, client_socket: socket):
        self.id = id
        self.ip_address = client_ip_address
        self.socket = client_socket

# conf = (
#     'http::addr=localhost:9000;'
#     'username=admin;'
#     'password=quest;'
#     'auto_flush=on;'
#     'auto_flush_rows=1;'
#     )

# constants
RELAY_PINS = [5, 6, 13, 16, 19, 20, 21, 26]
# Define the server's IP address and port
HOST = '0.0.0.0'  # Accept connections from any IP address
PORT = 9600        # Same port as in the client
CONFIG_FILE_NAME = "config.yaml"



class ControllerServer:
    def __init__(self):
        self.load_config()
        self.setup_gpio()
        self.setup_socket()
        self.switch_map = self.build_switch_map()

        self.worker_pis = {}
        self.cosmo_socket = None
        self.cosmo_address = None
        self.switch_states = {}
        self.abort = False

        self.override_manager = OverrideManager(self)


    def load_config(self):
        module_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(module_dir, CONFIG_FILE_NAME)
        
        with open(config_file_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        # get number of Pis from config file
        self.num_enabled_pis = sum((1 for pi_id in self.config["PIs"] if self.config["PIs"][pi_id]["enabled"]))


    def setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in RELAY_PINS:
            GPIO.setup(pin, GPIO.OUT)


    def setup_socket(self):
        # Create a TCP/IP socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind the socket to the address and port
        self.server_socket.bind((HOST, PORT))

        # Enable the server to accept connections (max 1 connection in the backlog queue)
        self.server_socket.listen(5)
        print(f"Server listening on {HOST}:{PORT}...")


    def build_switch_map(self):
        switch_map = {}
        for pi_id, pi_data in self.config["PIs"].items():
            if pi_data["enabled"]:
                for relay_id, relay_data in pi_data["relays"].items():
                    switch_id = relay_data["switch"]
                    if switch_id not in switch_map:
                        switch_map[switch_id] = []
                    switch_map[switch_id].append({"pi": pi_id, "relay": relay_id})
        return switch_map


    def wait_for_connections(self):
        print(f"Waiting for {self.num_enabled_pis} connections...")
        COSMO_connected = False
        num_connected_workers = 0

        while num_connected_workers < self.num_enabled_pis-1 or not COSMO_connected:
            client_socket, client_address = self.server_socket.accept()
            ip = client_address[0]

            # check for COSMO connection
            if ip == self.config["COSMO"]["ip"]:
                self.cosmo_socket = client_socket
                COSMO_connected = True
                print("COSMO Connection Established")
                continue

            # check for worker Pi connection
            known_worker = False
            for pi_id, data in self.config["PIs"].items():
                if ip == data["ip"]:
                    client_socket.settimeout(0.2)
                    self.worker_pis[str(pi_id)] = WorkerPi(pi_id, client_address, client_socket)
                    print(f"Pi {pi_id} Connection Established")
                    known_worker = True
                    num_connected_workers += 1
                    break

            if not known_worker and not COSMO_connected:
                print(f"Unknown connection from {ip}")

        print("ALL CONNECTIONs ESTABLISHED")


    def send_command_to_worker(self, worker_id, command, max_retries=5):
        print("-"*30)
        print(worker_id)
        if str(worker_id) not in list(self.worker_pis):
            print(f"ERR: Worker {worker_id} not found")
            return False
        
        worker_pi = self.worker_pis[str(worker_id)]

        attempts = 0
        while attempts < max_retries:
            # clear socket buffer
            worker_pi.socket.setblocking(False)
            try:
                while worker_pi.socket.recv(1024): pass
            except BlockingIOError:
                pass
            worker_pi.socket.setblocking(True)

            # send command
            try:
                worker_pi.socket.send(f"{command};".encode())
                print(f"Sent to Pi <{worker_pi.id}>: <{command}>")
                attempts += 1

                response_msg = worker_pi.socket.recv(1024).decode().strip()

                print(f"Recieved Response: <{response_msg}>")
                if f"ACK: {command}" in response_msg:
                    return True
                elif f"ERR: {command}" in response_msg:
                    return False
                
            except socket.timeout:
                print(f"Socket Timeout for Pi {worker_pi.id}")
                attempts += 1
            except socket.error as e:
                print(f"Socket Error for Pi {worker_pi.id}: {e}")
        
        print(f"Max retries reached for Pi {worker_pi.id}")
        return False
            
    # decodes command (FORM: "switch open/close")
    def decode_cmd(self, cmd: str):
        cmd = cmd.strip()
        cmd_lower = cmd.lower()

        if not cmd:
            raise ValueError(f"Empty CMD: <{cmd}>")

        # handle numeric switches
        if cmd[0].isdigit():
            switch_info = cmd_lower.split(' ')
            if len(switch_info) < 2: raise ValueError(f"Invalid Format, <{cmd}>")

            if not switch_info[0].isnumeric():
                raise ValueError(f"Switch id <{switch_info[0]}> not numeric")
            
            switch_id = int(switch_info[0])

            if switch_info[1] == "open" or switch_info[1] == "close":
                state = (switch_info[1] == "open".lower())
            else:
                raise ValueError(f"{switch_id} not open or closed")

        # handle enable fire 
        elif cmd_lower == "enable fire" or cmd_lower == "disable fire":
            switch_id = cmd_lower
            state = (cmd_lower == "enable fire".lower())

        # handle fire
        elif cmd_lower == "fire":
            switch_id = "FIRE"
            state = True

        elif "abort" in cmd_lower:
            self.abort = ("open" in cmd_lower)
            switch_id = 'ABORT'
            state = False

        else:
            raise ValueError(f"Unexpected Command")
        
        return switch_id, state


    # handles abort
    def set_relay(self, pi_id, relay_id, state):
        success = False
        target_state = state

        if self.abort:
            target_state = False

        if str(pi_id) == "controller":
            if target_state:
                GPIO.output(RELAY_PINS[relay_id-1], GPIO.HIGH)
            else:
                GPIO.output(RELAY_PINS[relay_id-1], GPIO.LOW)
                success = True
            print(f"Controller: Relay:{relay_id} State:{target_state}")
            
        else:
            worker_msg = f"{relay_id} {target_state}"
            success = self.send_command_to_worker(pi_id, worker_msg)

        return success and target_state == state



    def handle_command(self, cmd: str):
        print("="*50)
        print(f'CMD: <{cmd}>')
        time_now = datetime.now(tz=est)
        print(f"Time: {time_now}")
        success = False
        
        try:
            switch_id, target_state = self.decode_cmd(cmd)

            target_relays = self.switch_map.get(switch_id, [])
            
            success = True
            # if abort shut off all relays
            
            if self.abort:
                target_state = False # target state of all relays during an abort
                for pi_id in self.config["PIs"]:
                    if self.config["PIs"][pi_id]["enabled"]:
                        for relay_id in self.config["PIs"][pi_id]["relays"]:
                            self.set_relay(pi_id, relay_id, target_state) # shut off each relay

            elif str(switch_id).lower() in OverrideManager.OVERRIDDEN_CMDS:
                success = success and self.override_manager.process_command(switch_id)

            else:
                for relay_data in target_relays:
                    pi_id = relay_data["pi"]
                    relay_id = relay_data["relay"]
                    success = success and self.set_relay(pi_id, relay_id, target_state)
                    # print(f"[DEBUG: After Set Relay]: pid:{pi_id} rid:{relay_id} ts:{target_state} s:{success}")

            # respond to COSMO
            if success:
                self.switch_states[switch_id] = target_state
                self.cosmo_socket.send(f"ACK: {cmd};".encode())
                print("Sent ACK")
            else:
                self.cosmo_socket.send(f"ERR: {cmd};".encode())
                print(f"Sent ERR")

        except ValueError as e:
            print(f"ERR: {e} \n\n CMD: <{cmd}>")
            self.cosmo_socket.send(f"ERR: {cmd};".encode())


    def cleanup(self):
            # Make sure all Relays are off, close the client socket and server socket
            print("Shutting off Relays...")
            for pin in RELAY_PINS:
                GPIO.output(pin, GPIO.LOW)
            
            print("Closing connections...")
            if self.cosmo_socket:
                self.cosmo_socket.close()
            for worker_pi in self.worker_pis.values():
                worker_pi.socket.close()
            if self.server_socket:
                self.server_socket.close()
        
            GPIO.cleanup()
            print("Cleanup complete.")


    def main(self):
        print(f"{'='*50}\n{'='*50}")
        # with Sender.from_conf(conf) as sender:
        # print("Connected to Questdb")
        # print(f"{'='*50}")
        try:
            self.wait_for_connections()
            
            while True:
                msg = self.cosmo_socket.recv(1024)

                # If there's no data, break the loop
                if not msg:
                    print("No data received from COSMO. Closing connection.")
                    break

                # Decode the received data
                msg_str = msg.decode().strip()
                commands = msg_str.rstrip(';').split(';')

                print(f"Received Cmd: {msg_str}")
                for cmd in commands:
                    self.handle_command(cmd)

        except KeyboardInterrupt:
            print("Server interrupted by user.")

        # except (socket.error, ConnectionResetError, BrokenPipeError) as e:
        #     print(f"Socket error or connection lost: {e}")

        finally:
            self.cleanup()


if __name__ == '__main__':
    server = ControllerServer()
    server.main()



                # sender.row(
                #     'controls_data',
                #     columns = {
                #         str(switch): switch_states[switch] for switch in switch_states
                #     },
                #     at=datetime.now()
                # )