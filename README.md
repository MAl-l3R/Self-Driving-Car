# 🛠️ Self-Driving Robot Using Single and Stereo Camera Vision  

## 🚀 Overview  
This project implements a self-driving robot capable of navigating towards a sequence of markers using:  
- **Stereo Vision**: Utilizes two cameras to calculate depth and angle using disparity.  
- **Single-Camera Vision**: Estimates the distance and angle to the marker through scaling, based on known reference measurements.  

The robot dynamically adjusts its movement based on the marker's color (green, yellow, or red) and the marker’s position.  

Video Demo: https://drive.google.com/file/d/1f2Zs8-B_L2gvpKYR5BC-QMHg9-b_ek6E/view?usp=sharing

---

## ✨ Features  
- **Dual Vision Modes**:  
  - Stereo Vision for precise depth and angle estimation.  
  - Single-Camera Vision for simplified setups with intelligent fallback strategies.  
- **Color-Based Speed Control**:  
  - **Green**: Move at full speed.  
  - **Yellow**: Move at a slow speed.  
  - **Red**: Stop.  
- **Dynamic Navigation**:  
  - Adjusts direction and speed to navigate towards the next marker.  
  - Rotates to search for markers outside the field of view.  
- **Error Handling**:  
  - Contour completeness checks for reliable distance estimation.  
  - Handles partial marker visibility and limited fields of view.  

---

## 🛠️ Technologies Used  
- **Hardware**:  
  - LEGO EV3 brick.  
  - Two cameras (or one camera for single-camera mode).  
- **Software**:  
  - Python: OpenCV for computer vision, EV3Dev2 for robot control.  
  - IP Webcam for live, wireless video streaming.  
- **Networking**:  
  - TCP server-client architecture for communication between the robot and a laptop.  

---

## 📋 How It Works  
### 🔍 Stereo Vision Mode  
1. **Disparity Calculation**: Depth is computed using the difference in marker positions between the left and right camera frames.  
2. **Angle Calculation**: The horizontal displacement from the center of the cameras determines the angle.  
3. **Robot Movement**: Adjusts the front wheel's angle and speed to navigate towards the marker.  

### 🔍 Single-Camera Vision Mode  
1. **Scaling for Distance**:  
   - Distance (cm) = ( Reference Distance (cm) × Reference Marker's Radius (px)) ÷ Next Marker's Radius (px) 
2. **Angle Calculation**: Based on the horizontal displacement of the marker from the center of the frame.  
3. **Fallback Strategies**: Rotates left and right to locate markers outside the frame.  

---

## 🏗️ Design
### Steering Mechanism
The steering mechanism uses **5 gears** to ensure precise control:
- A **center gear** (connected to the center axle) turns two **outer gears** of the same size via **smaller intermediary gears**.
- This configuration ensures equal steering angles for the left and right wheels, maintaining proper alignment during turns.

<img src="https://github.com/user-attachments/assets/ea95dbe6-f0a6-4622-becb-3600ecfdf066" alt="Steering Mechanism" width="500"/>
<img src="https://github.com/user-attachments/assets/11118b19-6cfa-460a-9eac-175836df2c20" alt="Robot Design" width="500"/>

