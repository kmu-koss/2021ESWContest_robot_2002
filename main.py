from Actuator.Motion import Motion
from imutils import video
from Sensor.LineDetector import LineDetector
from Brain.Controller import Robot
from Sensor.ImageProcessor import ImageProcessor
import cv2

def main():
    robot = Robot()
    while True:
        robot.tracking_cube()

if __name__ == "__main__":
    main()
