import cv2
import time
import threading
import numpy as np

##### HSV Colour Ranges ##########################################
# Red color ranges
redLower1 = np.array([0, 120, 70])
redUpper1 = np.array([10, 255, 255])
redLower2 = np.array([170, 120, 70])
redUpper2 = np.array([180, 255, 255])

# Yellow color range
yellowLower = np.array([20, 100, 100])
yellowUpper = np.array([30, 255, 255])

# Green color range
greenLower = np.array([40, 70, 70])
greenUpper = np.array([80, 255, 255])
##################################################################

##### Camera Parameters ##########################################
baseline = 0.10  # Distance between the two cameras in meters
focal_length = 500  # Focal length in pixels
size_threshold = 0.2  # Tolerance level for size similarity (20%)
largest_marker_radius = 80  # Largest detectable marker's radius
##################################################################


class Vision:
    
    def __init__(self):
        self.distance = None
        self.angle = None
        self.color = None

        # self.TrackerThread()  # Use this instead of the threading code below if on macOS if you want to see camera view
        thread = threading.Thread(target=self.TrackerThread, daemon=True)
        thread.start()
        
    def TrackerThread(self):
        print("Tracker Started")
        # Get the cameras
        vc_left = cv2.VideoCapture("http://192.168.199.77:8080/video")
        vc_right = cv2.VideoCapture("http://192.168.199.16:8080/video")

        # Set frame rates
        vc_left.set(cv2.CAP_PROP_FPS, 30)
        vc_right.set(cv2.CAP_PROP_FPS, 30)
        
        # Try to get the first frames
        if vc_left.isOpened() and vc_right.isOpened():
            rval_left, frame_left = vc_left.read()
            rval_right, frame_right = vc_right.read()
        else:
            print("\t\tERROR: Could not open video streams")
            rval_left = False
            rval_right = False
        
        while rval_left and rval_right:
            # Get the frames
            rval_left, frame_left = vc_left.read()
            rval_right, frame_right = vc_right.read()
            
            # Process the frames
            circle_left, color_left = self.GetLocation(frame_left)     # Left frame
            circle_right, color_right = self.GetLocation(frame_right)  # Right frame
            
            # Draw the detected circles
            self.DrawCircle(frame_left, circle_left, color_left)
            self.DrawCircle(frame_right, circle_right, color_right)
            
            # Initialize flag
            same_marker_detected = False
            
            # Verify that both cameras detected the same marker
            if circle_left is not None and circle_right is not None:
                # Check if colors match
                if color_left == color_right:
                    self.color = color_left
                    # Check if sizes (radii) are similar within tolerance
                    radius_left = circle_left[2]
                    radius_right = circle_right[2]
                    size_difference = abs(radius_left - radius_right) / max(radius_left, radius_right)
                    if size_difference <= size_threshold:
                        same_marker_detected = True
                        
                        # Image center (principal point)
                        image_width = frame_left.shape[1]
                        c_x = image_width / 2
                        # Positions of the marker in left and right images
                        x_left = circle_left[0]
                        x_right = circle_right[0]
                        
                        # Compute disparity, depth, and angle
                        self.StereoVision(c_x, x_left, x_right)
                                
                        # Overlay the information on the video frames
                        if self.distance is not None and self.angle is not None and self.color is not None:
                            cv2.putText(frame_left, f"Distance: {self.distance:.2f} cm", (10, 30),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                            cv2.putText(frame_left, f"Angle: {self.angle:.2f} deg", (10, 60),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                            cv2.putText(frame_left, f"Color: {self.color}", (10, 90),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                            
                            cv2.putText(frame_right, f"Distance: {self.distance:.2f} cm", (10, 30),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                            cv2.putText(frame_right, f"Angle: {self.angle:.2f} deg", (10, 60),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                            cv2.putText(frame_right, f"Color: {self.color}", (10, 90),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                        
                    else:
                        # Marker sizes do not match, likely not the same marker.
                        # print("\t\tERROR: Marker sizes do not match, likely not the same marker.")
                        self.distance = None
                        self.angle = None
                        self.color = None
                else:
                    # Colors do not match, so not the same marker
                    # print("\t\tERROR: Colors do not match")
                    self.distance = None
                    self.angle = None
                    self.color = None
            
            # If the same marker is not detected
            if not same_marker_detected:
                self.distance = None  # Reset distance and color when markers don't match
                self.color = None
                
                # Determine which camera sees the larger marker
                if circle_left is not None and circle_right is not None:
                    radius_left = circle_left[2]
                    radius_right = circle_right[2]
                    if radius_left > radius_right:
                        self.angle = -20
                    elif radius_right > radius_left:
                        self.angle = 20
                    else:
                        print("\t\tERROR: Markers have equal size; cannot determine direction.")
                        self.angle = 0
  
                elif circle_left is not None and circle_right is None:
                    self.angle = -20
                elif circle_left is None and circle_right is not None:
                    self.angle = 20
                else:
                    self.angle = None  # No markers detected in either frame
                
                if self.angle is not None:
                    cv2.putText(frame_left, "Same marker not detected in both frames", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    cv2.putText(frame_left, f"Angle: Try {self.angle:.2f} deg", (10, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    
                    cv2.putText(frame_right, "Same marker not detected in both frames", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                    cv2.putText(frame_right, f"Angle: Try {self.angle:.2f} deg", (10, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Display the result (Does not work on macOS with threading. So comment out for macOS, uncomment for Windows)
            cv2.imshow("Left Camera", frame_left)
            cv2.imshow("Right Camera", frame_right)
            
            # Check if esc key pressed
            if cv2.waitKey(1) & 0xFF == 27:
                break
        
        vc_left.release()
        vc_right.release()
        cv2.destroyAllWindows()
        print("Tracker Ended")
    
    def StereoVision(self, c_x, x_left, x_right):        
        disparity = abs(x_left - x_right)  # In pixels
        
        if disparity != 0:
            # Calculate depth (Z)
            Z = (focal_length * baseline) / disparity  # Depth in meters
            self.distance = Z * 100  # Depth in centimeters
            
            # Calculate the average x-position of the marker
            x_center_image = (x_left + x_right) / 2  # In pixels
            
            # Calculate horizontal displacement (X)
            X = (x_center_image - c_x) * Z / focal_length  # In meters
            
            # Calculate the angle in radians
            angle_rad = np.arctan2(X, Z)
            # Convert to degrees
            self.angle = np.degrees(angle_rad)

        else:
            print("\t\tERROR: Disparity is zero, cannot compute depth")
            self.distance = None
            self.angle = None
            self.color = None
        
    def GetLocation(self, frame):
        # Convert the frame to HSV color space
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Initialize list to hold contours with their colors
        contours_with_color = []
        
        # Process red color
        # Red mask may span across the hue range, so combine two masks
        mask1 = cv2.inRange(hsv, redLower1, redUpper1)
        mask2 = cv2.inRange(hsv, redLower2, redUpper2)
        red_mask = cv2.bitwise_or(mask1, mask2)
        # Morphological operations
        mask = cv2.erode(red_mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        # Find contours
        contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            contours_with_color.append(('red', c))
        
        # Process yellow color
        yellow_mask = cv2.inRange(hsv, yellowLower, yellowUpper)
        mask = cv2.erode(yellow_mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            contours_with_color.append(('yellow', c))
        
        # Process green color
        green_mask = cv2.inRange(hsv, greenLower, greenUpper)
        mask = cv2.erode(green_mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        contours, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            contours_with_color.append(('green', c))
            
        # Proceed only if at least one contour was found
        if len(contours_with_color) > 0:
            # Sort the contours by area in descending order
            contours_with_color.sort(key=lambda x: cv2.contourArea(x[1]), reverse=True)
            
            # Iterate through the sorted contours to find the first valid one
            for color, contour in contours_with_color:
                # Determine the circle enclosing the current contour
                ((x, y), radius) = cv2.minEnclosingCircle(contour)
                if 10 < radius <= largest_marker_radius:
                    # Return the circle parameters and the color
                    return np.array([x, y, radius]), color
        
        return None, None

    def DrawCircle(self, frame, circle, color_name):
        if circle is not None:
            # Convert the circle parameters to integers
            x, y, r = np.round(circle).astype("int")
            # Draw the circle in the output image
            cv2.circle(frame, (x, y), r, (0, 255, 0), 2)
            # Set the dotColor based on color_name
            if color_name == 'red':
                dotColor = (0, 0, 255)       # Red in BGR
            elif color_name == 'yellow':
                dotColor = (0, 255, 255)     # Yellow in BGR
            elif color_name == 'green':
                dotColor = (0, 255, 0)       # Green in BGR
            else:
                dotColor = (255, 255, 255)   # White as default
            # Draw a rectangle corresponding to the center of the circle
            cv2.rectangle(frame, (x - 5, y - 5), (x + 5, y + 5), dotColor, -1)

if __name__ == "__main__":
    vision = Vision()
    print("Tracker Initializing...")
    time.sleep(5)  # Wait for the tracker to initialize
    
    while True:
        # Output the distance, angle, and color
        if vision.angle is not None:
            if vision.distance is not None:
                print(f"Distance to the marker: {vision.distance:.2f} centimeters")

            print(f"Angle to the marker: {vision.angle:.2f} degrees")
            
            if vision.color is not None:
                print(f"Color of the marker: {vision.color}")
        
        else:
            print("\t\tERROR: No markers detected in either frame")
        time.sleep(1)
