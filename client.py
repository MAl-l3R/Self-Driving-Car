#!/usr/bin/python3       
# RUN ON BRICK
    
import socket
from ev3dev2.motor import LargeMotor, OUTPUT_A, OUTPUT_B, OUTPUT_C, SpeedPercent

center_axle = LargeMotor(OUTPUT_A)
rear_wheel_left = LargeMotor(OUTPUT_B)
rear_wheel_right = LargeMotor(OUTPUT_C)

def move_joints(command):
    direction, duration, speed = command
    direction = -direction  # Reverse the sign because front wheels spin in the opposite direction of center axle

    print(f"Executing command: direction={direction}, duration={duration}, speed={speed}")

    # Turn the center axle to the steering angle first (blocking call)
    center_axle.on_for_degrees(SpeedPercent(100), direction)  # Turn to angle to the marker

    # Move the rear wheels simultaneously
    rear_wheel_left.on_for_seconds(SpeedPercent(speed), duration, block=False)   # Push forward (go straight)
    rear_wheel_right.on_for_seconds(SpeedPercent(speed), duration, block=False)  # Push forward (go straight)

    # Wait for the rear wheels to finish their movements
    rear_wheel_left.wait_while('running')
    rear_wheel_right.wait_while('running')

    print("Movement completed.")


def execute(data):
    raw_command = data.split(',')
    command = [float(value) for value in raw_command]
    move_joints(command)
    client.sendDone()
    


# This class handles the client side of communication. It has a set of predefined messages to send to the server as well as functionality to poll and decode data.
class Client:
    def __init__(self, host, port):
        # We need to use the ipv4 address that shows up in ipconfig in the computer for the USB. Ethernet adapter handling the connection to the EV3
        print("Setting up client\nAddress: " + host + "\nPort: " + str(port))
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        self.s.connect((host, port))                               
        
    # Block until a message from the server is received. When the message is received it will be decoded and returned as a string.
    # Output: UTF-8 decoded string containing the instructions from server.
    def pollData(self):
        print("Waiting for Data")
        data = self.s.recv(128).decode("UTF-8")
        if data:
            execute(data)
            print("Data Received")
            return data
    
    # Sends a message to the server letting it know that the movement of the motors was executed without any inconvenience.
    def sendDone(self):
        self.s.send("DONE".encode("UTF-8"))

    # Sends a message to the server letting it know that there was an isse during the execution of the movement (obstacle avoided) and that the initial jacobian should be recomputed (Visual servoing started from scratch)
    def sendReset(self):
        self.s.send("RESET".encode("UTF-8"))


host = "169.254.45.54"
port = 9999 
client = Client(host, port)
while True:
    client.pollData()
