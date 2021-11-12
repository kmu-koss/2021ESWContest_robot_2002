    @classmethod
    def setting_head_black(cls) -> bool:
        if (cls.robot.direction == 'RIGHT' and 0 < cls.robot.line_info["ALL_X"][0] < 300) or (cls.robot.direction == 'LEFT' and cls.robot.line_info["ALL_X"][1] > 340):
            if cls.robot.line_info["ALL_Y"][1] >= 215 :
                cls.return_head = 45
                cls.robot._motion.set_head(dir='DOWN', angle=cls.return_head)
            return True
        else:
            cls.robot._motion.turn(dir=cls.robot.direction.name, loop=1, grab=True)
        return False
    
    @classmethod
    def find_corner_black(cls) -> bool:
        if cls.robot.edge_info["EDGE_POS"]:
            if 280 < cls.robot.edge_info["EDGE_POS"][0] < 360 :
                return True
        else:
            cls.robot._motion.turn(dir=cls.robot.direction.name, loop=1, grab=True)
        return False

    @classmethod
    def go_to_corner_black(cls) -> bool:
        if cls.return_head in [60, 45]:
            if cls.robot.line_info["ALL_Y"][1] >= 215 :
                cls.return_head -= 15
                cls.robot._motion.set_head(dir='DOWN', angle=cls.return_head)
                time.sleep(0.2)

        if cls.robot.edge_info["EDGE_POS"][1] > 450:
            cls.robot._motion.grab(switch=False)
            cls.robot._motion.walk(dir='FORWARD', loop=1)
            cls.robot._motion.turn(dir=cls.robot.direction.name , sliding= True, loop=1)
            return True

        else:
            cls.robot._motion.walk(dir='FORWARD', loop=1)