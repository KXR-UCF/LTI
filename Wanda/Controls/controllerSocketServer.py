import RPi.GPIO as GPIO
import yaml
import time
import socket
import os
from typing import Tuple
from questdb.ingress import Sender, Protocol
from datetime import datetime
from pytz import timezone
est = timezone('US/Eastern')

from overrideCMD import OverrideManager

# class used to make instances of each worker pi (wanda2 and wanda3)
class WorkerPi:
    def __init__(self, id, client_ip_address, client_socket: socket):
        self.id = id
        self.ip_address = client_ip_address
        self.socket = client_socket

# questdb configuration
QUESTDB_CONF = (
    'tcp::addr=192.168.1.32:9009;'
    'auto_flush=on;'
    'auto_flush_rows=1;'
)

# gpio pin numbers for each relay in index order
RELAY_PINS = [5, 6, 13, 16, 19, 20, 21, 26]

# Define the server's IP address and port
HOST = '0.0.0.0'   # Accept connections from any IP address
PORT = 9600        # Same port as in the client

# /Wanda/Controls/config.yaml
CONFIG_FILE_NAME = "config.yaml"

# prints message with current time before each line for logging
def print_log(message:str):
    lines = message.split('\n')
    for line in lines:
        print(f"[{datetime.now(tz=est).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}] {line}")


# contains most of the logic of the control server
class ControllerServer:

    # constructor
    def __init__(self):
        print_log(f"{'='*50}\n{'='*50}\n{'='*50}\nController Started")
        self.load_config()
        self.setup_gpio()
        self.setup_socket()
        self.switch_map = self.build_switch_map()

        self.worker_pis = {}
        self.cosmo_socket = None
        self.cosmo_address = None # unused
        
        self.switch_states = {self._format_col_name(switch_id): False for switch_id in self.switch_map.keys()}
        self.switch_states['FIRE_KEY'] = False
        self.switch_states['FIRE'] = False
        self.switch_states['ABORT'] = False
        self.sender = None

        self.abort = False

        # used to make more complex timing and controls for certain switches
        self.override_manager = OverrideManager(self)


    def _format_col_name(self, switch_id: str) -> str:
        """
        Adds underscores in place of spaces for questdb columns.

        Args:
            switch_id (str): the id of the switch in the command
        
        Returns:
            str: the formatted switch id for column names
        """

        s = str(switch_id).replace(' ', '_')
        if s.isdigit():
            return f"switch_{s}"
        return s


    def load_config(self) -> None:
        """
        Loads data cfrom config file.
        Also determines total number of pis.
        """
        
        # get the absolute path to the config file
        module_dir = os.path.dirname(os.path.abspath(__file__))
        config_file_path = os.path.join(module_dir, CONFIG_FILE_NAME)

        # load config file into memory
        with open(config_file_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        # get number of enabled Pis from config file
        self.num_enabled_pis = sum((1 for pi_id in self.config["PIs"] if self.config["PIs"][pi_id]["enabled"]))


    def setup_gpio(self) -> None:
        """
        Sets up all GPIO pins ahead of using them
        """
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        for pin in RELAY_PINS:
            GPIO.setup(pin, GPIO.OUT)


    def setup_socket(self) -> None:
        """
        Creates socket server for clients to connect to.
        Starts allowing connections.
        """

        # Create a TCP/IP socket
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Bind the socket to the address and port
        self.server_socket.bind((HOST, PORT))

        # Enable the server to accept connections (max 1 connection in the backlog queue)
        self.server_socket.listen(5)
        print_log(f"Server listening on {HOST}:{PORT}...")


    def build_switch_map(self) -> dict:
        """
        Builds switch map based off information in loaded config file

        Note:
            `load_config()` must have been ran before this function can be ran

        Returns:
            dict: uses `switch_id` as an index for each switch. Each switch
                contains a list of dicts with a pi and relay id values.
        """

        switch_map = {}
        # iterates through each pi
        for pi_id, pi_data in self.config["PIs"].items():
            # checks if pi is enabled
            if pi_data["enabled"]:
                # iterates through each relay on the pi
                for relay_id, relay_data in pi_data["relays"].items():
                    # get switch_id relay is tied too and check if it exists in the map
                    switch_id = relay_data["switch"]
                    if switch_id not in switch_map:
                        switch_map[switch_id] = []
                    # add the pi and relay id to the switch in the map
                    switch_map[switch_id].append({"pi": pi_id, "relay": relay_id})
        return switch_map


    def wait_for_connections(self) -> None:
        """Accepts all incomming connections.

        Tracks if COSMO and the expected number of worker pis have connected.
        Uses the config file to check if the ip address of an incoming
        connection matches the ip of an enabled worker pi or cosmo

        TODO:
            * Check hostnames instead of ip addresses
            * Use handshake of some sort 

        Warning:
            This method will block indefinitely if a worker Pi or COSMO fails 
            to connect or has an incorrect IP in the config.
        """

        print_log(f"Waiting for {self.num_enabled_pis} connections...")
        COSMO_connected = False
        num_connected_workers = 0

        # waits until cosmo is connected and the number of connected worker pis is correct
        while num_connected_workers < self.num_enabled_pis-1 or not COSMO_connected:
            # accept incoming connection
            client_socket, client_address = self.server_socket.accept()
            ip = client_address[0]

            # TODO: Do handshake with incoming connection (maybe to get hostname)

            # check for COSMO connection against ip address
            # TODO: Check against hostname instead of ip address
            if ip == self.config["COSMO"]["ip"]:
                self.cosmo_socket = client_socket
                COSMO_connected = True
                print_log("COSMO Connection Established")
                continue

            # check for worker Pi connection against ip address
            known_worker = False
            # iterates through each worker in config
            for pi_id, data in self.config["PIs"].items():
                # ! ISSUE: does not check if pi is enabled
                # checks if incoming ip is the current worker pis ip
                # TODO: Check against hostname instead of ip address
                if ip == data["ip"]:
                    client_socket.settimeout(0.2) # used to check for ACKs when sending commands to worker pis
                    self.worker_pis[str(pi_id)] = WorkerPi(pi_id, client_address, client_socket)
                    print_log(f"Pi {pi_id} Connection Established")
                    known_worker = True
                    num_connected_workers += 1
                    break

            # ! ISSUE: seems like this would not flag unkown connections after cosmo connects
            if not known_worker and not COSMO_connected:
                print_log(f"Unknown connection from {ip}")

        print_log("ALL CONNECTIONs ESTABLISHED")


    def send_command_to_worker(self, worker_id: str, command: str, max_retries:int=5) -> bool:
        """Sends command to worker pis
        
        Uses the worker pi's socket to send a command to the worker pi. Waits for 
        acknowledgement. If no acknowledgement is recieved, the command will be
        resent until either an acknowledgement is recieved or the max number of
        retries is hit.  

        Args:
            worker_id (str): the id of the worker pi
            command (str): the command to be sent to the worker pi
            max_retries (int, optional): The number of retries that will occur in the case 
                the worker pi does not respond. Defaults to 5.

        Returns:
            bool: True if worker pi recieved and acknowledged the command

        Note:
            This method clears the socket buffer before sending to ensure the 
            received ACK belongs to *this* specific command, preventing race conditions.
        """

        print_log("-"*30)
        # checks if worker_id is a valid worker pi
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

                # waits for response from worker pi
                response_msg = worker_pi.socket.recv(1024).decode().strip()

                print_log(f"Recieved Response: <{response_msg}>")
                if f"ACK: {command}" in response_msg:
                    return True
                elif f"ERR: {command}" in response_msg:
                    return False
            
            # times out if not response is received in some time
            except socket.timeout:
                print_log(f"Socket Timeout for Pi {worker_pi.id}")
                attempts += 1
            
            # raised if the socket has disconnected
            except socket.error as e:
                print_log(f"Socket Error for Pi {worker_pi.id}: {e}")
        
        print_log(f"Max retries reached for Pi {worker_pi.id}")
        return False
            
    # decodes command (FORM: "switch open/close")
    def decode_cmd(self, cmd: str) -> Tuple[str, bool]:
        """Decodes a command
        
        Parses the switch id and target state of the switch from the command.
        
        Supported Formats:
            - Numeric: "1 open" -> (1, True)
            - Fire Key: "enable fire" -> ("FIRE KEY", True)
            - Abort: "abort open" -> ("ABORT", False)

        Args:
            cmd (str): the command from COSMO to be decoded

        Returns:
            str: the id of the switch in the command
            bool: the state of the switch in the command

        Raises:
            ValueError: If the command format is unrecognized.
        """

        cmd = cmd.strip()
        cmd_lower = cmd.lower()

        if not cmd:
            raise ValueError(f"Empty CMD: <{cmd}>")

        # handle numeric switches
        if cmd[0].isdigit():
            switch_info = cmd_lower.split(' ') # gets 
            if len(switch_info) < 2: raise ValueError(f"Invalid Format, <{cmd}>")

            if not switch_info[0].isnumeric():
                raise ValueError(f"Switch id <{switch_info[0]}> not numeric")
            
            switch_id = int(switch_info[0])

            if switch_info[1] == "open" or switch_info[1] == "close":
                state = (switch_info[1] == "open".lower())
            else:
                raise ValueError(f"{switch_id} not open or closed")

        # handle fire key 
        elif cmd_lower == "enable fire" or cmd_lower == "disable fire":
            switch_id = "FIRE KEY"
            state = (cmd_lower == "enable fire") # state is true if enable fire

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


    def set_relay(self, pi_id: str, relay_id: int, state: bool) -> bool:
        """Actuates relay

        Accepts the location and target state of the relay to be switched. Handles
        sending commands to worker pis if relay not on this pi.

        Args:
            pi_id (str): the id of the pi the relay will be set on
            relay_id (int): the id of the relay to be switched
            state (bool): the state the relay should be set too

        Returns:
            bool: whether or not the relay was set successfully
        """
        success = False
        target_state = state

        # rejects turning on relays during an abort
        if self.abort and state:
            print_log(f"Unable to actuate due to abort")
            return False

        # handles switches controlled on the controller
        if str(pi_id) == "controller":
            if target_state:
                GPIO.output(RELAY_PINS[relay_id-1], GPIO.HIGH)
            else:
                GPIO.output(RELAY_PINS[relay_id-1], GPIO.LOW)
            success = True
            print_log(f"Controller: Relay:{relay_id} State:{target_state}")
            
        else:
            # sends command to worker pi
            worker_msg = f"{relay_id} {target_state}"
            success = self.send_command_to_worker(pi_id, worker_msg)

        return success
    
    
    def post_status_to_questdb(self, switch_id, target_state) -> None:
        """update controls data in questdb
        
        Args:
            switch_id (str): the id of the switch in the command
            target_state (bool): the state of the switch
        """

        # sets all to false during an abort
        if self.abort:
            for k in self.switch_states:
                self.switch_states[k] = False
            self.switch_states['ABORT'] = True
        else:
            formatted_switch_id = self._format_col_name(switch_id)
            self.switch_states[formatted_switch_id] = target_state
        
        # sends to questdb
        if self.sender is not None:
            try:
                self.sender.row('controls', columns=self.switch_states, at=datetime.now(tz=est))
                self.sender.flush()
                print_log("Posted status to QuestDB")
            except Exception as e:
                print_log(f"QuestDB Error: {e}")

        pass


    def handle_command(self, cmd: str) -> None:
        """Handles the process for a command
        
        If abort is active, this will ignore current command and shut off every relay. 
        If the switch_id is in the override manager, ignores mapped relays and lets 
        the OverrideManager handle the command. If there are no exceptions, the `decode_cmd()` 
        fucntion is uesed to parse information from a command and gets the target relays to be 
        switched based off the command. Afterwards it sets those relays to their target states.
        In addition, responds to COSMO with ACK or ERR.

        Args:
            cmd (str): the command recieved from COSMO
        """

        print_log("="*50)
        print_log(f'CMD: <{cmd}>')
        time_now = datetime.now(tz=est)
        print_log(f"Time: {time_now}")
        success = False
        
        try:
            switch_id, target_state = self.decode_cmd(cmd)
            success = True
            
            # if abort shut off all relays
            if self.abort:
                target_state = False # target state of all relays during an abort
                for pi_id in self.config["PIs"]:
                    if self.config["PIs"][pi_id]["enabled"]:
                        for relay_id in self.config["PIs"][pi_id]["relays"]:
                            self.set_relay(pi_id, relay_id, target_state) # shut off each relay

            # if switch_id is overridden in the OverrideManager, move processing of command to it
            elif str(switch_id).lower() in OverrideManager.OVERRIDDEN_CMDS:
                success = success and self.override_manager.process_command(switch_id, target_state)

            # handle command based off the config file
            else:
                target_relays = self.switch_map.get(switch_id, [])
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


    def cleanup(self) -> None:
            """Cleans up GPIO pins and relays after shutdown

            Turns all relays off on this pi. Closes all socket connections and closes
            socket server. Closes connection to questdb if there was one.
            """
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


    def hold(self) -> None:
        """Sets relays to hold position
        
        Checks if the relay has a specific hold position. If so,
        the relay is set to that position.
        """

        print_log("Applying hold positions to all relays due to disconnect...")
        for pi_id, pi_data in self.config["PIs"].items():
            if pi_data["enabled"]:
                for relay_id, relay_data in pi_data["relays"].items():

                    hold_state = relay_data.get("hold_position", False)
                    if hold_state is None:
                        continue
                    
                    switch_id = relay_data.get("switch")
                    success = self.set_relay(pi_id, relay_id, hold_state)
                    if success and switch_id is not None:
                        self.post_status_to_questdb(switch_id, hold_state)


    def reconnect_cosmo(self, timeout_seconds=300) -> None:
        """Recconnects COSMO during a disconnection

        Args:
            timeout_seconds (int): The seconds to attempt reconnection (defaults to 300)        
        """

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

        # sets up questdb sender
        try:
            self.sender = Sender.from_conf(QUESTDB_CONF).__enter__()
            print_log("Connected to Questdb")
        except Exception as e:
            print_log(f"Warning: Could not connect to QuestDB: {e}. Running without database.")
            self.sender = None
            
        print_log(f"{'='*50}")
        try:
            # gets all connections
            self.wait_for_connections()
            
            # loops for entire controls duration
            while True:
                try:
                    # recieves command from COSMO
                    msg = self.cosmo_socket.recv(1024)

                    # If there's no data, break the loop
                    if not msg:
                        print_log("No data received from COSMO. Reconnecting...")
                        self.hold()
                        if not self.reconnect_cosmo(): 
                            break
                        continue

                    # Decode the received data
                    msg_str = msg.decode().strip()
                    commands = msg_str.rstrip(';').split(';') # if commands buffered, multiple could be concatenated together

                    if 'SHUTDOWN' in commands:
                        print_log("SHUTDOWN command received. Exiting...")
                        break

                    # handles each command
                    for cmd in commands:
                        self.handle_command(cmd)

                # handles cosmo disconnections
                except (socket.error, ConnectionResetError, BrokenPipeError) as e:
                    print_log(f"Socket error with COSMO: {e}")
                    self.hold()
                    if not self.reconnect_cosmo(): 
                        break

        except KeyboardInterrupt:
            print_log("Server interrupted by user.")

        finally:
            self.cleanup()


if __name__ == '__main__':
    server = ControllerServer()
    server.main()