import RPi.GPIO as GPIO
import socket
import time

# numbered in order 1-8
RELAY_PINS = [5, 6, 13, 16, 19, 20, 21, 26]

# relay pin setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
for pin in RELAY_PINS:
    GPIO.setup(pin, GPIO.OUT)

start_time = time.time()
 
# socket client -> server set up
controller_pi_address = "192.168.1.30"
controller_pi_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
connected = False
print(f"Attempting to connect to {controller_pi_address}")
while not connected:
    try:
        controller_pi_socket.connect((controller_pi_address, 9600))
        connected = True
    except OSError as e:
        program_time = time.time() - start_time
        print(f"{program_time:<5.2f}s Failed to connect... Attempting to connect")
        time.sleep(1)

try:
    while True:
        # Receive data from COSMO (up to 1024 bytes at a time)
        msg = controller_pi_socket.recv(1024).decode()
        
        # If there's no data, break the loop
        if not msg:
            print("No data received. Closing connection.")
            break
        
        # splits message into each command
        cmds = msg.rstrip(';').split(';')
        for cmd in cmds:
            print(f"Recieved CMD: <{cmd}>")
            success = False
            err_msg = ""

            # decode message (FORM: "relay# True/False")
            try:
                # split command into parts
                cmd_info = cmd.split(' ')
                if len(cmd_info) != 2:
                    raise ValueError("Invalid Format")
                
                # get relay number from command
                relay = int(cmd_info[0])
                if not (1 <= relay <= 8):
                    raise ValueError("Invalid Relay Number")
                
                # get relay state from command
                if cmd_info[1].strip() == "True":
                    relay_state = GPIO.HIGH
                elif cmd_info[1].strip() == "False":
                    relay_state = GPIO.LOW    
                else:
                    raise ValueError("Invalid State")
                
                # set relay state
                GPIO.output(RELAY_PINS[relay-1], relay_state)

                # check relay state
                if GPIO.input(RELAY_PINS[relay-1]) == relay_state:
                    success = True
                else:
                    success = False
                    err_msg = "Relay State Mismatch"

            except ValueError as e:
                success = False
                err_msg = e
            
            if success:
                print(f"Sending ACK\n")
                controller_pi_socket.send(f"ACK: {msg}".encode())
            else:
                print(f"Sending ERR\n")
                controller_pi_socket.send(f"ERR: {msg},{err_msg}".encode())

except KeyboardInterrupt:
    print("Interrupted by user")

except (socket.error, ConnectionResetError, BrokenPipeError) as e:
    print(f"Socket error or connection lost: {e}")

finally:
    print("Shutting off Relays...")
    for pin in RELAY_PINS:
        GPIO.output(pin, GPIO.LOW)
    
    print("Closing connection...")
    controller_pi_socket.close()