import RPi.GPIO as GPIO
import yaml
import time
import socket
import os

from questdb.ingress import Sender, Protocol
from datetime import datetime
from pytz import timezone
est = timezone('US/Eastern')

from overrideCMD import OverrideManager


class WorkerPi:
    def __init__(self, id, client_ip_address, client_socket: socket):
        self.id = id
        self.ip_address = client_ip_address
        self.socket = client_socket

conf = (
    'tcp::addr=192.168.1.32:9009;'
    'auto_flush=on;'
    'auto_flush_rows=1;'
)

# constants
RELAY_PINS = [5, 6, 13, 16, 19, 20, 21, 26]
# Define the server's IP address and port
HOST = '0.0.0.0'  # Accept connections from any IP address
PORT = 9600        # Same port as in the client
CONFIG_FILE_NAME = "config.yaml"


def print_log(message:str):
    lines = message.split('\n')
    for line in lines:
        print(f"[{datetime.now(tz=est).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] {line}")

class ControllerServer:
    def __init__(self):
        print_log(f"{'='*50}\n{'='*50}\n{'='*50}\nController Started")
        self.load_config()
        self.setup_gpio()
        self.setup_socket()
        self.switch_map = self.build_switch_map()

        self.worker_pis = {}
        self.cosmo_socket = None
        self.cosmo_address = None
        
        self.switch_states = {self._format_col_name(switch_id): False for switch_id in self.switch_map.keys()}
        self.switch_states['ENABLE_FIRE'] = False
        self.switch_states['FIRE'] = False
        self.switch_states['ABORT'] = False
        self.sender = None

        self.abort = False

        self.override_manager = OverrideManager(self)

    def _format_col_name(self, switch_id):
        s = str(switch_id).replace(' ', '_')
        if s.isdigit():
            return f"switch_{s}"
        return s


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
        print_log(f"Server listening on {HOST}:{PORT}...")


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
        print_log(f"Waiting for {self.num_enabled_pis} connections...")
        COSMO_connected = False
        num_connected_workers = 0

        while num_connected_workers < self.num_enabled_pis-1 or not COSMO_connected:
            client_socket, client_address = self.server_socket.accept()
            ip = client_address[0]

            # check for COSMO connection
            if ip == self.config["COSMO"]["ip"]:
                self.cosmo_socket = client_socket
                COSMO_connected = True
                print_log("COSMO Connection Established")
                continue

            # check for worker Pi connection
            known_worker = False
            for pi_id, data in self.config["PIs"].items():
                if ip == data["ip"]:
                    client_socket.settimeout(0.2)
                    self.worker_pis[str(pi_id)] = WorkerPi(pi_id, client_address, client_socket)
                    print_log(f"Pi {pi_id} Connection Established")
                    known_worker = True
                    num_connected_workers += 1
                    break

            if not known_worker and not COSMO_connected:
                print_log(f"Unknown connection from {ip}")

        print_log("ALL CONNECTIONs ESTABLISHED")


    def send_command_to_worker(self, worker_id, command, max_retries=5):
        print_log("-"*30)
        if str(worker_id) not in list(self.worker_pis):
            print_log(f"ERR: Worker {worker_id} not found")
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
                print_log(f"Sent to Pi <{worker_pi.id}>: <{command}>")
                attempts += 1

                response_msg = worker_pi.socket.recv(1024).decode().strip()

                print_log(f"Recieved Response: <{response_msg}>")
                if f"ACK: {command}" in response_msg:
                    return True
                elif f"ERR: {command}" in response_msg:
                    return False
                
            except socket.timeout:
                print_log(f"Socket Timeout for Pi {worker_pi.id}")
                attempts += 1
            except socket.error as e:
                print_log(f"Socket Error for Pi {worker_pi.id}: {e}")
        
        print_log(f"Max retries reached for Pi {worker_pi.id}")
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
            switch_id = "ENABLE FIRE"
            state = (cmd_lower == "enable fire")

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

        if self.abort and state:
            print_log(f"Unable to actuate due to abort")
            return False

        if str(pi_id) == "controller":
            if target_state:
                GPIO.output(RELAY_PINS[relay_id-1], GPIO.HIGH)
            else:
                GPIO.output(RELAY_PINS[relay_id-1], GPIO.LOW)
            success = True
            print_log(f"Controller: Relay:{relay_id} State:{target_state}")
            
        else:
            worker_msg = f"{relay_id} {target_state}"
            success = self.send_command_to_worker(pi_id, worker_msg)

        # return success and target_state == state
        # print_log(f"[DEBUG: end of set relay: sucess: {success}]")
        return success
    
    
    def post_status_to_questdb(self, switch_id, target_state):
        if self.abort:
            for k in self.switch_states:
                self.switch_states[k] = False
            self.switch_states['ABORT'] = True
        else:
            formatted_switch_id = self._format_col_name(switch_id)
            self.switch_states[formatted_switch_id] = target_state
        
        if self.sender is not None:
            try:
                self.sender.row('controls', columns=self.switch_states, at=datetime.now(tz=est))
                self.sender.flush()
                print_log("Posted status to QuestDB")
            except Exception as e:
                print_log(f"QuestDB Error: {e}")

        pass


    def handle_command(self, cmd: str):
        print_log("="*50)
        print_log(f'CMD: <{cmd}>')
        time_now = datetime.now(tz=est)
        print_log(f"Time: {time_now}")
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
                    # print_log(f"[DEBUG: After Set Relay]: pid:{pi_id} rid:{relay_id} ts:{target_state} s:{success}")

            # respond to COSMO
            if success:
                self.post_status_to_questdb(switch_id, target_state)
                self.cosmo_socket.send(f"ACK: {cmd};".encode())
                print_log("Sent ACK")
            else:
                self.cosmo_socket.send(f"ERR: {cmd};".encode())
                print_log(f"Sent ERR")

        except ValueError as e:
            print_log(f"ERR: {e} \n\n CMD: <{cmd}>")
            self.cosmo_socket.send(f"ERR: {cmd};".encode())


    def cleanup(self):
            # Make sure all Relays are off, close the client socket and server socket
            print_log("Shutting off Relays...")
            for pin in RELAY_PINS:
                GPIO.output(pin, GPIO.LOW)
            
            print_log("Closing connections...")
            if self.cosmo_socket:
                self.cosmo_socket.close()
            for worker_pi in self.worker_pis.values():
                worker_pi.socket.close()
            if self.server_socket:
                self.server_socket.close()
            if self.sender is not None:
                try:
                    self.sender.close()
                except Exception:
                    pass
        
            GPIO.cleanup()
            print_log("Cleanup complete.")

    def hold(self):
        print_log("Applying hold positions to all relays due to disconnect...")
        for pi_id, pi_data in self.config["PIs"].items():
            if pi_data["enabled"]:
                for relay_id, relay_data in pi_data["relays"].items():
                    hold_state = relay_data.get("hold_position", False)
                    switch_id = relay_data.get("switch")
                    success = self.set_relay(pi_id, relay_id, hold_state)
                    if success and switch_id is not None:
                        self.post_status_to_questdb(switch_id, hold_state)

    def reconnect_cosmo(self, timeout_seconds=300):
            print_log(f"Attempting to reconnect to COSMO")
            if self.cosmo_socket:
                try:
                    self.cosmo_socket.close()
                except Exception:
                    pass
                self.cosmo_socket = None

            start_time = time.time()
            self.server_socket.settimeout(1.0)  # sets time step to check timer

            while time.time() - start_time < timeout_seconds:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    ip = client_address[0]
                    
                    if ip == self.config["COSMO"]["ip"]:
                        self.cosmo_socket = client_socket
                        self.cosmo_address = client_address
                        self.server_socket.settimeout(None)
                        print_log("COSMO Reconnected successfully!")
                        return True
                    else:
                        print_log(f"Unexpected connection from {ip} during COSMO reconnect. Closing.")
                        client_socket.close()
                        
                except socket.timeout:
                    pass
                
                except Exception as e:
                    print_log(f"Error accepting connection during reconnect: {e}")
                    time.sleep(1)

            self.server_socket.settimeout(None)
            print_log("Reconnect timeout expired. Proceeding to shutdown.")
            return False


    def main(self):
        print_log(f"{'='*50}\n{'='*50}")
        try:
            self.sender = Sender.from_conf(conf).__enter__()
            print_log("Connected to Questdb")
        except Exception as e:
            print_log(f"Warning: Could not connect to QuestDB: {e}. Running without database.")
            self.sender = None
            
        print_log(f"{'='*50}")
        try:
            self.wait_for_connections()
            
            while True:
                try:
                    msg = self.cosmo_socket.recv(1024)

                    # If there's no data, break the loop
                    if not msg:
                        print_log("No data received from COSMO. Reconnecting...")
                        self.hold()
                        if not self.reconnect_cosmo(): break

                        continue

                    # Decode the received data
                    msg_str = msg.decode().strip()
                    commands = msg_str.rstrip(';').split(';')

                    print_log(f"Received Cmd: {msg_str}")
                    for cmd in commands:
                        self.handle_command(cmd)

                except (socket.error, ConnectionResetError, BrokenPipeError) as e:
                    print_log(f"Socket error with COSMO: {e}")
                    self.hold()
                    if not self.reconnect_cosmo(): break

        except KeyboardInterrupt:
            print_log("Server interrupted by user.")

        # except (socket.error, ConnectionResetError, BrokenPipeError) as e:
        #     print_log(f"Socket error or connection lost: {e}")

        finally:
            self.cleanup()


if __name__ == '__main__':
    server = ControllerServer()
    server.main()
