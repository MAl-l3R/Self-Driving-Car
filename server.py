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
        data = f"{direction:.2f},{duration:.2f},{speed}"
        print(f"\tSending Data: ({data}) to robot.")
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



host = "169.254.182.18"
port = 9999
server = Server(host, port)
queue = Queue()

MAX_STEERING_ANGLE = 40  # degrees
MAX_MOTOR_SPEED = 1050  # degrees per second
MAX_DURATION = 5  # seconds (max duration for turns to prevent overly long turns)   ##### Can actually be 2 theoretically. CHECK #####
TOLERANCE = 15  # degrees (tolerance for angle to the marker)
WHEEL_DIAMETER = 5.6  # cm
WHEELBASE = 14.75  # cm (distance between front and rear axles)
# CALIBRATION_FACTOR = 3.45  # Derived from practical tests (1.90 / 0.55 ≈ 3.45)

# Calculate maximum linear speed (circumference * rotations per second)
WHEEL_CIRCUMFERENCE = math.pi * WHEEL_DIAMETER
MAX_ROTATIONS_PER_SEC = MAX_MOTOR_SPEED / 360.0
MAX_SPEED_CM_PER_SEC = WHEEL_CIRCUMFERENCE * MAX_ROTATIONS_PER_SEC

vision = vs.Vision()
print("Tracker Initializing...")
time.sleep(5)  # Wait for the tracker to initialize


def calculateRotation(angle):
    # Rotate robot towards the marker
    angle = angle * 1.5  # (Overshoot just in case it's a sharp turn)
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
            # duration = duration * CALIBRATION_FACTOR
            # Limit the duration of turn to prevent overly long turns
            duration = min(duration, MAX_DURATION)
        else:
            duration = 0
    return desired_angle, steering_angle, duration, speed

def rotateRobot(desired_angle, steering_angle, duration, speed, towards=True):
    if duration > 0:
        if towards:
            print(f"ROTATE: Rotating robot by {desired_angle:.2f} degrees towards marker over {duration:.2f} seconds.")
        else:
            print(f"ROTATE: Rotating robot by {desired_angle:.2f} degrees backwards over {duration:.2f} seconds.")

        # Send command to robot
        server.sendData(steering_angle, duration, speed, queue)
        # Wait for robot to complete the action
        reply = queue.get()
        print("\tRobot reply:", reply)

    else:
        print("Speed is zero or duration is zero, not moving.")


if __name__ == "__main__":
    
    checked_left = False
    checked_right = False

    while True:
        print()
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
        if angle is not None and color != 'red':
            # Marker detected, so reset checked_left and checked_right
            checked_left = False
            checked_right = False
            
            # Rotate the robot until robot is facing the marker
            if round(abs(angle)) > TOLERANCE or color is None:
                desired_angle, steering_angle, duration, speed = calculateRotation(angle)
                rotateRobot(desired_angle, steering_angle, duration, speed)

            else:
                # Angle is approximately zero; move straight towards the marker
                if color == 'green':
                    distance = distance - 20  # (Undershoot extra for fast speed to be able to see the next marker)
                else:
                    distance = distance - 15  # (Undershoot to be able to see the next marker)
                direction = 0

                if distance is not None:
                    # Calculate linear speed
                    speed_cm_per_sec = (speed / 100.0) * MAX_SPEED_CM_PER_SEC  # cm/s

                    # Calculate duration to move based on distance
                    duration = distance / speed_cm_per_sec  # seconds

                    print(f"MOVE: Moving forward {distance:.2f}cm at {speed*2}% speed for {duration:.2f} seconds.")

                    # Send command to robot
                    server.sendData(direction, duration, speed, queue)
                    # Wait for robot to complete the action
                    reply = queue.get()
                    print("\tRobot reply:", reply)

                else:
                    print("ERROR: No valid distance, not moving.")

        else:
            # Red marker detected, so stop
            if color == 'red':
                print("STOP: Red!")
                time.sleep(1)

            # No marker detected, robot is idle
            else:
                print("No marker detected.")
                
                if not checked_left and not checked_right:
                    # Check left side first
                    checked_left = True
                    print("\tRobot is checking left side for markers.")
                    desired_angle, steering_angle, duration, speed = calculateRotation(-20)
                    rotateRobot(desired_angle, steering_angle, duration, speed)
                elif checked_left and not checked_right:
                    # Check right side, but first reverse back to original track
                    desired_angle, steering_angle, duration, speed = calculateRotation(-20)
                    rotateRobot(desired_angle, steering_angle, duration, -speed, towards=False)
                    
                    checked_right = True
                    print("\tRobot is checking right side for markers.")
                    desired_angle, steering_angle, duration, speed = calculateRotation(20)
                    rotateRobot(desired_angle, steering_angle, duration, speed)
                else:
                    # Both sides checked, robot is idle
                    print("\tBoth sides checked. No marker detected, robot is idle.")
                    time.sleep(1)
                    
            
