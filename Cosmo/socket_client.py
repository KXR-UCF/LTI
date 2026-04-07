import socket
import serial
import time
import os

controller_pi_address = "192.168.1.30"
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

start_time = time.time()
connected = False
print(f"Attempting to connect to {controller_pi_address}")
while not connected:
    try:
        s.connect((controller_pi_address, 9600))
        connected = True
    except OSError as e:
        program_time = time.time() - start_time
        print(f"{program_time:<5.2f}s Failed to connect... Attempting to connect")
        time.sleep(1)
if connected:
    print(f"Connected to {controller_pi_address}")

# s.connect(("192.168.1.30", 9600))
ser = serial.Serial("/dev/ttyACM0", 9600)

# Create named pipe for sharing switch states with server.js
PIPE_PATH = '/tmp/switch_pipe'
if not os.path.exists(PIPE_PATH):
    os.mkfifo(PIPE_PATH)
    print(f"Created named pipe: {PIPE_PATH}")

# Track current switch states to resend on reconnection
current_switch_states = {
    'switch1': False,   # NOX FILL
    'switch2': False,   # NOX VENT
    'switch3': False,   # NOX RELIEF
    'switch4': False,   # DOME VENT
    'switch5': False,   # FUEL/NOX MAIN
    'switch6': False,   # N2 FILL
    'switch7': False,   # N2 VENT
    'switch8': False,   # FUEL/N2 RELIEF
    'switch9': False,   # SERVO PWR
    'switch10': False,  # SERVO MOVE
    'continuity': False, # CONTINUITY (not mapped to hardware switch)
    'launchKey': False,
    'abort': False
}

# Function to open/reopen pipe
def open_pipe():
    try:
        pipe_fd = os.open(PIPE_PATH, os.O_WRONLY | os.O_NONBLOCK)
        pipe = os.fdopen(pipe_fd, 'w')
        print(f"✅ Opened named pipe for writing")
        return pipe
    except OSError as e:
        print(f"⚠️  Could not open pipe (server.js may not be running): {e}")
        return None

# Function to parse and track switch state from message
def parse_and_track_state(msg_str):
    """Parse message and update current_switch_states. Returns True if it's a switch message."""
    # "1 Open" / "1 Close" → switches (multi-digit like "10 Open" supported)
    if len(msg_str) >= 3 and (msg_str.endswith('Open') or msg_str.endswith('Close')):
        parts = msg_str.split()
        if len(parts) >= 2 and parts[0].isdigit():
            switch_num = parts[0]
            state = msg_str.endswith('Open')
            switch_map = {
                '1': 'switch1',   # NOX FILL
                '2': 'switch2',   # NOX VENT
                '3': 'switch3',   # NOX RELIEF
                '4': 'switch4',   # DOME VENT
                '5': 'switch5',   # FUEL/NOX MAIN
                '6': 'switch6',   # N2 FILL
                '7': 'switch7',   # N2 VENT
                '8': 'switch8',   # FUEL/N2 RELIEF
                '9': 'switch9',   # SERVO PWR
                '10': 'switch10', # SERVO MOVE
            }
            if switch_num in switch_map:
                current_switch_states[switch_map[switch_num]] = state
                return True

    # "ENABLE FIRE" / "DISABLE FIRE"
    if msg_str == 'ENABLE FIRE' or msg_str == 'DISABLE FIRE':
        current_switch_states['launchKey'] = (msg_str == 'ENABLE FIRE')
        return True

    # "ABORT Open" / "ABORT Close"
    if msg_str == 'ABORT Open' or msg_str == 'ABORT Close':
        current_switch_states['abort'] = (msg_str == 'ABORT Open')
        return True

    return False

# Function to resend all current switch states
def resend_all_states(pipe):
    """Send all current switch states to pipe after reconnection."""
    if not pipe:
        return

    print(f"📡 Resending current switch states to reconnected pipe...")

    # Map switch states back to hardware message format
    switch_to_num = {
        'switch1': '1',
        'switch2': '2',
        'switch3': '3',
        'switch4': '4',
        'switch5': '5',
        'switch6': '6',
        'switch7': '7',
        'switch8': '8',
        'switch9': '9',
        'switch10': '10',
    }

    try:
        # Send switch 1-10 states
        for switch_name in ['switch1', 'switch2', 'switch3', 'switch4', 'switch5', 'switch6', 'switch7', 'switch8', 'switch9', 'switch10']:
            switch_num = switch_name.replace('switch', '')
            state = current_switch_states[switch_name]
            msg = f"{switch_num} {'Open' if state else 'Close'}"
            pipe.write(msg + '\n')
            pipe.flush()
            print(f"  → {msg}")

        # Send launchKey state
        launch_msg = 'ENABLE FIRE' if current_switch_states['launchKey'] else 'DISABLE FIRE'
        pipe.write(launch_msg + '\n')
        pipe.flush()
        print(f"  → {launch_msg}")

        # Send abort state
        abort_msg = 'ABORT Open' if current_switch_states['abort'] else 'ABORT Close'
        pipe.write(abort_msg + '\n')
        pipe.flush()
        print(f"  → {abort_msg}")

        print(f"✅ All states resent successfully")
    except Exception as e:
        print(f"⚠️  Error resending states: {e}")
        return None

    return pipe

# Open pipe initially
pipe = open_pipe()
if pipe:
    # Resend current states on initial connection
    pipe = resend_all_states(pipe)

# set socket timeout
try:
    while True:
        # receive data from the server and decoding to get the string.
        msg = ser.readline().decode().strip()
        msg_payload = f"{msg};".encode()

        if len(msg) == 0:
            continue

        # send until error or ack repsonse
        response_ack = False
        response_err = False
        attempts = 0
        while not (response_ack or response_err):

            # clear socket buffer
            s.setblocking(False)
            try:
                s.recv(1024)
            except BlockingIOError:
                pass
            s.setblocking(True)
            s.settimeout(0.5)

            # if no response after 5 attempts give up
            if attempts > 5:
                print(f"No responses: <{msg_payload.decode().strip()}>")
                break

            s.send(msg_payload)
            print(f"Sent: <{msg_payload.decode().strip()}>")
            attempts += 1

            # check for response
            try:
                response_msg = s.recv(1024)
                response_msg = response_msg.decode().strip()
                responses = response_msg.rstrip(';').split(';')
                for response in responses:

                    response_ack = (response == f"ACK: {msg.strip()}")
                    response_err = (response == f"ERR: {msg.strip()}")

                    if response_ack or response_err:
                        break
            except socket.timeout:
                print("No ACK")

        # error check
        if response_err:
            print(f"ERROR: {response_msg}")

        # do something after a successful response
        if response_ack:
            print(f"Received Response: {response_msg}")

            msg_str = msg

            # Track switch state changes
            parse_and_track_state(msg_str)

            # Write switch state to named pipe for server.js
            if pipe:
                try:
                    pipe.write(msg_str + '\n')
                    pipe.flush()
                except BrokenPipeError:
                    print("⚠️  Pipe broken (server.js disconnected) - will attempt reconnection")
                    pipe = None
                except Exception as e:
                    print(f"⚠️  Error writing to pipe: {e}")
                    pipe = None
            else:
                # Try to reconnect pipe
                print(f"🔄 Attempting to reconnect pipe...")
                pipe = open_pipe()
                if pipe:
                    # Resend all current states after reconnection
                    pipe = resend_all_states(pipe)
                    # Try to send current message again
                    if pipe:
                        try:
                            pipe.write(msg_str + '\n')
                            pipe.flush()
                        except Exception as e:
                            print(f"⚠️  Error writing after reconnect: {e}")
                            pipe = None

except KeyboardInterrupt:
    print("Interrupted by user")
    try:
        s.send(b"SHUTDOWN;")
        response_msg = s.recv(1024).decode().strip()
        print(f"Received Response: {response_msg}")
    except Exception:
        pass


finally:
    # close the connection
    s.close()
    if pipe:
        pipe.close()

    # Remove named pipe file
    try:
        if os.path.exists(PIPE_PATH):
            os.unlink(PIPE_PATH)
            print(f"Removed named pipe: {PIPE_PATH}")
    except Exception as e:
        print(f"Warning: Could not remove pipe: {e}")

    print("Connections closed")
