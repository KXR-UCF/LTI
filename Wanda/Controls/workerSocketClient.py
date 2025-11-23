import RPi.GPIO as GPIO
import socket

RELAY_PINS = [5, 6, 13, 16, 19, 20, 21, 26]

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
for pin in RELAY_PINS:
    GPIO.setup(pin, GPIO.OUT)

controller_pi_address = "192.168.1.30"

controller_pi_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
controller_pi_socket.connect((controller_pi_address, 9600))

try:
    while True:
        # Receive data from COSMO (up to 1024 bytes at a time)
        msg = controller_pi_socket.recv(1024).decode()
        
        # If there's no data, break the loop
        if not msg:
            print("No data received. Closing connection.")
            break
        
        cmds = msg.rstrip(';').split(';')
        for cmd in cmds:
            print(f"Recieved CMD: <{cmd}>")
            success = False

            # decode message
            cmd_info = cmd.split(' ')
            relay = int(cmd_info[0])
            relay_state = cmd_info[1].strip() == "True"

            # change relay state
            if relay_state:
                GPIO.output(RELAY_PINS[relay-1], GPIO.HIGH)
                success = True
            else:
                GPIO.output(RELAY_PINS[relay-1], GPIO.LOW)
                success = True

            if success:
                print(f"Sending ACK\n")
                controller_pi_socket.send(f"ACK: {msg}".encode())
            else:
                print(f"Sending ERR\n")
                controller_pi_socket.send(f"ERR: {msg}".encode())

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