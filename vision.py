import cv2
import numpy as np

##### HSV Colour Ranges #################
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
#########################################

def GetLocation(frame):
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
        # Find the largest contour among all colors
        largest_contour_color, largest_contour = max(contours_with_color, key=lambda x: cv2.contourArea(x[1]))
        # Determine the circle enclosing the largest contour
        ((x, y), radius) = cv2.minEnclosingCircle(largest_contour)
        if radius > 10:
            # Return the circle parameters and the color
            return np.array([x, y, radius]), largest_contour_color
    return None, None

def DrawCircle(frame, circle, color_name):
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
    print("Tracker Setup")
    # Camera parameters
    baseline = 0.1075  # Distance between the two cameras in meters
    focal_length = 700  # Focal length in pixels (example value)
    size_threshold = 0.2  # Tolerance level for size similarity (20%)
    
    # Get the cameras
    vc_left = cv2.VideoCapture("http://10.0.0.66:8080/video")
    vc_right = cv2.VideoCapture("http://10.0.0.123:8080/video")
    if not vc_left.isOpened() or not vc_right.isOpened():
        print("Could not open video streams")
        exit()
    
    while True:
        rval_left, frame_left = vc_left.read()
        rval_right, frame_right = vc_right.read()
        if not rval_left or not rval_right:
            print("Failed to grab frames")
            break
        
        # Process the frames
        circle_left, color_left = GetLocation(frame_left)     # Left frame
        circle_right, color_right = GetLocation(frame_right)  # Right frame
        
        # Draw the detected circles
        DrawCircle(frame_left, circle_left, color_left)
        DrawCircle(frame_right, circle_right, color_right)
        
        # Initialize flags
        same_marker_detected = False
        angle = None
        
        # Verify that both cameras detected the same marker
        if circle_left is not None and circle_right is not None:
            # Check if colors match
            if color_left == color_right:
                # Check if sizes (radii) are similar within tolerance
                radius_left = circle_left[2]
                radius_right = circle_right[2]
                size_difference = abs(radius_left - radius_right) / max(radius_left, radius_right)
                if size_difference <= size_threshold:
                    same_marker_detected = True
                    # Proceed to compute disparity, depth, and angle
                    # Image center (principal point)
                    image_width = frame_left.shape[1]
                    c_x = image_width / 2  # Assuming principal point is at the image center
                    
                    # Positions of the marker in left and right images
                    x_left = circle_left[0]
                    x_right = circle_right[0]
                    disparity = abs(x_left - x_right)  # In pixels
                    
                    if disparity != 0:
                        # Calculate depth (Z)
                        Z = (focal_length * baseline) / disparity  # Depth in meters
                        
                        # Calculate the average x-position of the marker
                        x_center_image = (x_left + x_right) / 2  # In pixels
                        
                        # Calculate horizontal displacement (X)
                        X = (x_center_image - c_x) * Z / focal_length  # In meters
                        
                        # Calculate the angle in radians
                        angle_rad = np.arctan2(X, Z)
                        # Convert to degrees
                        angle = np.degrees(angle_rad)
                        
                        # Output the distance, angle, and color
                        print(f"Distance to the marker: {Z*100:.2f} centimeters")
                        print(f"Angle to the marker: {angle:.2f} degrees")
                        print(f"Color of the marker: {color_left}")
                        
                        # Overlay the information on the video frames
                        cv2.putText(frame_left, f"Distance: {Z*100:.2f} cm", (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                        cv2.putText(frame_left, f"Angle: {angle:.2f} deg", (10, 60),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                        cv2.putText(frame_left, f"Color: {color_left}", (10, 90),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                        
                        cv2.putText(frame_right, f"Distance: {Z*100:.2f} cm", (10, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                        cv2.putText(frame_right, f"Angle: {angle:.2f} deg", (10, 60),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                        cv2.putText(frame_right, f"Color: {color_right}", (10, 90),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    else:
                        print("Disparity is zero, cannot compute depth")
                else:
                    print("Marker sizes do not match, likely not the same marker.")
            else:
                print("Colors do not match")
        
        # If the same marker is not detected
        if not same_marker_detected:
            print("Same marker not detected in both frames.")
            # Determine which camera sees the larger marker
            if circle_left is not None and circle_right is not None:
                radius_left = circle_left[2]
                radius_right = circle_right[2]
                if radius_left > radius_right:
                    angle = -25
                elif radius_right > radius_left:
                    angle = 25
            elif circle_left is not None and circle_right is None:
                angle = -25
            elif circle_left is None and circle_right is not None:
                angle = 25
            else:
                print("No markers detected in either frame.")
            
            if angle:
                print(f"Angle to the marker: Try {angle:.2f} degrees")

                cv2.putText(frame_left, "Same marker not detected in both frames", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(frame_left, f"Angle: Try {angle:.2f} deg", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                cv2.putText(frame_right, "Same marker not detected in both frames", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                cv2.putText(frame_right, f"Angle: Try {angle:.2f} deg", (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Display the result
        cv2.imshow("Left Camera", frame_left)
        cv2.imshow("Right Camera", frame_right)
        if cv2.waitKey(1) & 0xFF == 27:
            break
    
    vc_left.release()
    vc_right.release()
    cv2.destroyAllWindows()
