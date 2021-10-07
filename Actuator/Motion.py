# -*- coding: utf-8 -*-

import platform
import argparse
import cv2
import serial
import time
import sys
from threading import Thread, Lock

#-----------------------------------------------

class Motion:
    head_angle1 = 'UPDOWN_CENTER'
    head_angle2 = 'LEFTRIGHT_CENTER'

    def __init__(self, DEBUG):
        self.serial_use = 1
        self.serial_port = None
        self.Read_RX = 0
        self.receiving_exit = 1
        self.threading_Time = 0.01
        self.lock = Lock()
        self.distance = 0
        self.debug = DEBUG
        BPS = 4800  # 4800,9600,14400, 19200,28800, 57600, 115200

        # ---------local Serial Port : ttyS0 --------
        # ---------USB Serial Port : ttyAMA0 --------
        if not self.debug:
            self.serial_port = serial.Serial('/dev/ttyS0', BPS, timeout=0.01)
            self.serial_port.flush()  # serial cls
            self.serial_t = Thread(target=self.Receiving, args=(self.serial_port,))
            self.serial_t.daemon = True
            self.serial_t.start()
            time.sleep(0.1)



    def TX_data_py2(self, one_byte):  # one_byte= 0~255
        self.lock.acquire()

        self.serial_port.write(serial.to_bytes([one_byte]))  # python3
        time.sleep(0.02)


    def RX_data(self):
        if self.serial_port.inWaiting() > 0:
            result = self.serial_port.read(1)
            RX = ord(result)
            return RX
        else:
            return 0



    def Receiving(self, ser):
        self.receiving_exit = 1
        while True:
            if self.receiving_exit == 0:
                break
            time.sleep(self.threading_Time)
            # 수신받은 데이터의 수가 0보다 크면 데이터를 읽고 출력
            while ser.inWaiting() > 0:
                # Rx, 수신
                result = ser.read(1)
                RX = ord(result)
                print ("RX=" + str(RX))

                # -----  remocon 16 Code  Exit ------
                if RX == 16:
                    self.receiving_exit = 0
                    break
                elif RX == 200:
                    self.lock.release()
                elif RX != 200:
                     self.distance = RX


    def notice_direction(self, dir):
        """dir={'E', 'W', 'S', 'N'}
        """
        dir_list = {'E':33, 'W':34, 'S':35, 'N':36}
        
        if not self.debug:
            self.TX_data_py2(dir_list[dir])
        else:
            print(dir)



    def notice_area(self,area):
        """area='GREEN' or area='BLACK'
        """
        area_list = {'GREEN':67,'BLACK':68}
        
        if not self.debug:
            self.TX_data_py2(area_list[area])
        else:
            print(area)



    def set_head(self, dir, angle=0):
        """parameter 설명
        dir: {DOWN, LEFT, RIGHT, UPDOWN_CENTER, LEFTRIGHT_CENTER}
        angle: {DOWN:{10,20,30,35,45,50,55,60,70,75,80,85,90,100},
        LEFT:{30,45,60,90},
        RIGHT:{30,45,60,90}
        }
        """
        if dir == 'DOWN':
            self.head_angle1 = angle
        elif dir == 'LEFT' or dir == 'RIGHT':
            self.head_angle2 = angle
        elif dir == 'UPDOWN_CENTER':
            self.head_angle1 = dir
        elif dir == 'LEFTRIGHT_CENTER':
            self.head_angle2 = dir

        center_list = {'UPDOWN_CENTER':46, 'LEFTRIGHT_CENTER':55}
        dir_list = {
            'DOWN':{
            10:37, 20:80, 30:38, 35:39, 45:40, 50:84, 55:81, 60:41, 70:82, 75:42, 80:43, 85:83, 90:44, 100:45
            },
            'LEFT':{
                30:47, 45:48, 60:49, 90:50
            },
            'RIGHT':{
                30:51, 45:52, 60:53, 90:54
            }
        }
        
        if not self.debug:
            if dir in center_list:
                self.TX_data_py2(center_list[dir])
            else:
                self.TX_data_py2(dir_list[dir][angle])
        else:
            if dir in center_list:
                print(dir)
            else:
                print(dir, angle)


    def walk(self, dir, loop=1, grab=False):
        dir_list = {'FORWARD':56, 'BACKWARD':57, 'LEFT':58, 'RIGHT':59}
        if grab: dir_list[dir] += 13  # if grab is true, change walk motion with grab
        for _ in range(loop):
            if not self.debug:
                self.TX_data_py2(dir_list[dir])
            else:
                print(dir)


    def turn(self, dir, loop=1, sleep=0.5, grab=False,sliding=False):
        """parameter 설명
        dir = ['SLIDING_LEFT', 'SLIDING_RIGHT', 'LEFT', 'RIGHT']
        """
        dir_list = {'SLIDING_LEFT':60, 'SLIDING_RIGHT':61, 'LEFT':62, 'RIGHT':63}
        if grab:
            dir_list[dir] += 11# if grab is true, change walk motion with grab
            if sliding:
                dir_list[dir]+=9
        for _ in range(loop):
            if not self.debug:
                self.TX_data_py2(dir_list[dir])
                time.sleep(sleep)
            else:
                print(dir)


    def get_IR(self) -> int:
        """get IR value and return self.distance
        """
        if not self.debug:
            self.TX_data_py2(5)
            self.TX_data_py2(5)
        else:
            print("get IR")
            
        return self.distance


    def open_door(self, loop=1):
        for _ in range(loop):
            if not self.debug:
                self.TX_data_py2(66)
            else:
                print("TX 66")



    def grab(self, switch=True):
        """if switch=True then grab ON, else then grab OFF
        """
        tx = 65 if switch else 66
        
        if not self.debug:
            self.TX_data_py2(tx)
        else:
            print(tx)


    def get_head(self):
        """Return vertical, horizontal head angle
        """
        return (self.head_angle1, self.head_angle2)


    def basic_form(self):
        self.TX_data_py2(45)
        self.TX_data_py2(54)
        self.TX_data_py2(10)


    def basic_form(self):
        if not self.debug:
            self.TX_data_py2(46)
            self.TX_data_py2(55)
            self.TX_data_py2(10)
        else:
            print(46)
            print(55)
            print(10)


def move_arm(self, grab=True, level=2):
    """level: if grab is True, {1,2,3} else grab is False, {1,2}
    """
    angle_list = [30, 90, 60]
    if grab:
        self.TX_data_py2(75 + level)
        time.sleep(0.5)
        self.set_head(dir='DOWN', angle=angle_list[level - 1])
    else:
        self.TX_data_py2(73 + level)
        time.sleep(0.5)
        self.set_head(dir='DOWN', angle=100)


# **************************************************
# **************************************************
if __name__ == '__main__':
    motion = Motion()
    motion.TX_data_py2(16)
    
