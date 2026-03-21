import socket
import threading
import sys

# Configurations
CONTROLLER_IP = '192.168.1.30'
PORT = 9600

def receive_messages(sock):
    """Listens for incoming messages (ACK/ERR) in the background."""
    while True:
        try:
            msg = sock.recv(1024).decode().strip()
            if not msg:
                print("\nDisconnected from server.")
                break
            # Print response and reset prompt
            print(f"\n{msg}\nCMD> ", end="", flush=True)
        except Exception:
            break

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        s.connect((CONTROLLER_IP, PORT))
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)

    # Start the listening thread
    recv_thread = threading.Thread(target=receive_messages, args=(s,), daemon=True)
    recv_thread.start()

    try:
        while True:
            cmd = input("CMD> ").strip()
            
            if cmd.lower() in ['quit', 'exit']:
                break
                
            if cmd:
                if not cmd.endswith(';'):
                    cmd += ';'
                s.send(cmd.encode())
                
    except KeyboardInterrupt:
        pass
    finally:
        s.close()

if __name__ == '__main__':
    main()