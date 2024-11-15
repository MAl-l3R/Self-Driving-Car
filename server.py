#!/usr/bin/python
# RUN ON LAPTOP USING PYTHON 3.6
import time
import math
import socket
import vision as vs
from queue import Queue

# This class handles the Server side of the communication between the laptop and the brick.
class Server:
    def __init__(self, host, port):
        # setup server socket
        serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # We need to use the IP address that shows up in ipconfig for the USB ethernet adapter that handles the communication between the PC and the brick
        print("Setting up Server\nAddress: " + host + "\nPort: " + str(port))

        serversocket.bind((host, port))
        # queue up to 5 requests
        serversocket.listen(5)
        self.cs, addr = serversocket.accept()
        print("Connected to: " + str(addr))

    # Sends set of commands to the brick via TCP.
    # Input:
    #   direction [Float]: Degrees to turn the center axle motor (steering angle)
    #   duration [Float]: Time in seconds to move the rear wheels
    #   speed [Integer]: Speed percentage for the rear wheels (0 to 100)
    #   queue [Thread-safe Queue]: Mutable data structure to store (and return) the messages received from the client
    def sendData(self, direction, duration, speed, queue):
        # Format in which the client expects the data: "direction,duration,speed"
        data = f"{direction},{duration},{speed}"
        print(f"Sending Data: ({data}) to robot.")
        self.cs.send(data.encode("UTF-8"))
        # Waiting for the client (EV3 brick) to let the server know that it is done moving
        reply = self.cs.recv(128).decode("UTF-8")
        queue.put(reply)

    # Sends a termination message to the client. This will cause the client to exit "cleanly", after stopping the motors.
    def sendTermination(self):
        self.cs.send("EXIT".encode("UTF-8"))

    # Lets the client know that it should enable safety mode on its end
    def sendEnableSafetyMode(self):
        self.cs.send("SAFETY_ON".encode("UTF-8"))

    # Lets the client know that it should disable safety mode on its end
    def sendDisableSafetyMode(self):
        self.cs.send("SAFETY_OFF".encode("UTF-8"))



host = "169.254.45.54"
port = 9999
server = Server(host, port)
queue = Queue()

MAX_STEERING_ANGLE = 45  # degrees
MAX_MOTOR_SPEED = 1050  # degrees per second
MAX_DURATION = 5  # seconds (max duration for turns to prevent overly long turns)
TOLERANCE = 3  # degrees (tolerance for angle to the marker)
WHEEL_DIAMETER = 5.6  # cm
WHEELBASE = 15.0  # cm (distance between front and rear axles)

# Calculate maximum linear speed (circumference * rotations per second)
WHEEL_CIRCUMFERENCE = math.pi * WHEEL_DIAMETER
MAX_ROTATIONS_PER_SEC = MAX_MOTOR_SPEED / 360.0
MAX_SPEED_CM_PER_SEC = WHEEL_CIRCUMFERENCE * MAX_ROTATIONS_PER_SEC

vision = vs.Vision()
print("Tracker Initializing...")
time.sleep(5)  # Wait for the tracker to initialize

if __name__ == "__main__":

    while True:
        # Get vision data
        angle = vision.angle
        distance = vision.distance
        color = vision.color

        # Determine speed
        if color == 'green':
            speed = 50
        elif color == 'yellow':
            speed = 25
        elif color == 'red':
            speed = 0
        else:
            speed = 0  # Default to 0 speed

        # Move robot
        if angle is not None:
            # Rotate the robot until robot is facing the marker
            if abs(angle) > TOLERANCE:
                # Rotate robot towards the marker
                speed = 25  # Slow speed to make the turn
                # Desired change in heading angle (Δϕ)
                desired_angle = angle
                # Steering angle (θ) is limited by robot's capability. Can be equal to any angle, even vision.angle.
                steering_angle = max(min(angle, MAX_STEERING_ANGLE), -MAX_STEERING_ANGLE)

                # Calculate duration needed to make the turn
                steering_angle_rad = abs(steering_angle) * (math.pi / 180.0)
                if steering_angle_rad == 0:
                    duration = 0
                else:
                    # Calculate turning radius
                    R = WHEELBASE / math.tan(steering_angle_rad)
                    # Convert desired change in heading angle to radians
                    desired_angle_rad = abs(desired_angle) * (math.pi / 180.0)
                    # Calculate arc length
                    arc_length = R * desired_angle_rad  # cm
                    # Calculate linear speed
                    speed_cm_per_sec = (speed / 100.0) * MAX_SPEED_CM_PER_SEC  # cm/s
                    if speed_cm_per_sec > 0:
                        duration = arc_length / speed_cm_per_sec  # seconds
                        # Limit the duration of turn to prevent overly long turns
                        duration = min(duration, MAX_DURATION)
                    else:
                        duration = 0

                if duration > 0:
                    print(f"Rotating robot by {desired_angle:.2f} degrees towards marker over {duration:.2f} seconds.")

                    # Send command to robot
                    server.sendData(steering_angle, duration, speed, queue)
                    # Wait for robot to complete the action
                    reply = queue.get()
                    print("Robot reply:", reply)

                    # Reset center axle motor rotation back to 0 position
                    # Send command to robot
                    server.sendData(-steering_angle, 0, 0, queue)
                    # Wait for robot to complete the action
                    reply = queue.get()
                    print("Robot reply:", reply)

                    continue  # Continue adjusting until angle is approximately zero, i.e. robot is facing the marker

                else:
                    print("Speed is zero or duration is zero, not moving.")

            else:
                # Angle is approximately zero; move straight towards the marker
                direction = 0

                if distance is not None and speed > 0:
                    # Calculate linear speed
                    speed_cm_per_sec = (speed / 100.0) * MAX_SPEED_CM_PER_SEC  # cm/s

                    # Calculate duration to move based on distance
                    duration = distance / speed_cm_per_sec  # seconds

                    print(f"Moving forward {distance:.2f} centimeters at {speed}% speed for {duration:.2f} seconds.")

                    # Send command to robot
                    server.sendData(direction, duration, speed, queue)
                    # Wait for robot to complete the action
                    reply = queue.get()
                    print("Robot reply:", reply)

                else:
                    print("No valid distance or speed is zero, not moving.")

        else:
            # No marker detected, robot is idle
            print("No marker detected, robot is idle.")
            time.sleep(1)
