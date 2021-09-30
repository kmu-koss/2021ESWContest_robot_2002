import cv2
import numpy as np
import time
import platform
import os
from imutils.video import WebcamVideoStream
from imutils.video import FileVideoStream
from imutils.video import FPS
from imutils import auto_canny, grab_contours

if __name__ == "__main__":
    from HashDetector import HashDetector
    from Target import Target, setLabel
    from LineDetector import LineDetector
    from ColorChecker import ColorPreProcessor
    from LaneLines import intersect, median, left_right_lines
else:
    from Sensor.HashDetector import HashDetector
    from Sensor.Target import Target, setLabel
    from Sensor.LineDetector import LineDetector
    from Sensor.ColorChecker import ColorPreProcessor
    from Sensor.LaneLines import intersect, median, left_right_lines


class ImageProcessor:

    def __init__(self, video_path : str = ""):
        if video_path and os.path.exists(video_path):
            self._cam = FileVideoStream(path=video_path).start()
        else:
            if platform.system() == "Linux":
                self._cam = WebcamVideoStream(src=-1).start()
            else:
                self._cam = WebcamVideoStream(src=0).start()
        # 개발때 알고리즘 fps 체크하기 위한 모듈. 실전에서는 필요없음
        self.fps = FPS()
        if __name__ == "__main__":
            self.hash_detector4door = HashDetector(file_path='EWSN/')
            self.hash_detector4room = HashDetector(file_path='ABCD/')
            self.hash_detector4arrow = HashDetector(file_path='src/arrow/')

        else:

            self.hash_detector4door = HashDetector(file_path='Sensor/EWSN/')
            self.hash_detector4room = HashDetector(file_path='Sensor/ABCD/')
            self.hash_detector4arrow = HashDetector(file_path='Sensor/src/arrow/')

        self.line_detector = LineDetector()
        self.color_preprocessor = ColorPreProcessor()
        self.COLORS = self.color_preprocessor.COLORS

        shape = (self.height, self.width, _) = self.get_image().shape
        print(shape)  # 이미지 세로, 가로 (행, 열) 정보 출력
        time.sleep(2)

    def get_image(self, visualization=False):
        src = self._cam.read()
        if src is None:
            exit()
        if visualization:
            cv2.imshow("src", src)
            cv2.waitKey(1)
        return src


    def get_door_alphabet(self, visualization: bool = False) -> str:
        src = self.get_image()
        if visualization:
            canvas = src.copy()
            roi_canvas = canvas.copy()
        no_canny_targets = []
        canny_targets = []
        # 그레이스케일화
        gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
        # ostu이진화, 어두운 부분이 true(255) 가 되도록 THRESH_BINARY_INV
        _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        canny = auto_canny(mask)
        cnts1, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts2, _ = cv2.findContours(canny, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in cnts1:
            approx = cv2.approxPolyDP(cnt, cv2.arcLength(cnt, True) * 0.02, True)
            vertice = len(approx)
            if vertice == 4 and cv2.contourArea(cnt) > 2500:
                target = Target(contour=cnt)
                no_canny_targets.append(target)
                if visualization:
                    setLabel(canvas, cnt, "no_canny")

        for cnt in cnts2:
            approx = cv2.approxPolyDP(cnt, cv2.arcLength(cnt, True) * 0.02, True)
            vertice = len(approx)
            if vertice == 4 and cv2.contourArea(cnt) > 2500:
                target = Target(contour=cnt)
                canny_targets.append(target)
                if visualization:
                    setLabel(canvas, cnt, "canny", color=(0,0,255))

        target = Target.non_maximum_suppression4targets(canny_targets, no_canny_targets, threshold=0.7)

        if visualization:
            cv2.imshow("src", cv2.hconcat([canvas, roi_canvas]))
            # cv2.imshow("mask", mask)
            # cv2.imshow("canny", canny)
            # cv2.imshow("canvas", canvas)
            cv2.waitKey(1)

        if target is None:
            return None
        roi = target.get_target_roi(src=src)
        roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, roi_mask = cv2.threshold(roi_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if visualization:
            pos = target.get_pts()
            setLabel(roi_canvas, target.get_pts(), label="roi", color=(255,0,0))
            roi_canvas[pos[1]:pos[1]+pos[3],pos[0]:pos[0]+pos[2]] = cv2.cvtColor(roi_mask, cv2.COLOR_GRAY2BGR)
            cv2.imshow("src", cv2.hconcat(
                [canvas, roi_canvas]))
            cv2.waitKey(1)
        answer, _ = self.hash_detector4door.detect_alphabet_hash(roi_mask)
        return answer

    def get_slope_degree(self, visualization: bool = False):
        src = self.get_image()
        return self.line_detector.get_slope_degree(src)

    def get_room_alphabet(self, visualization: bool = False):

        src = self.get_image()
        if visualization:
            canvas = src.copy()

        hls = cv2.cvtColor(src, cv2.COLOR_BGR2HLS)
        h, l, s = cv2.split(hls)
        _, mask = cv2.threshold(l, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        canny = auto_canny(mask)
        candidates = []


        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in cnts:
            approx = cv2.approxPolyDP(cnt, cv2.arcLength(cnt, True) * 0.02, True)
            vertice = len(approx)
            if vertice <= 4 and 2000 <= cv2.contourArea(cnt):
                target = Target(contour=cnt)
                candidates.append(target)

        curr_candidate = None
        curr_hamming_distance = 1

        for candidate in candidates:
            roi = candidate.get_target_roi(src)
            roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            _, roi_mask = cv2.threshold(roi_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            roi_thresholded = cv2.bitwise_and(roi,roi,mask=roi_mask)
            setLabel(canvas, candidate.get_pts(), color=(255, 255, 255))
            alphabet, hamming_distance = self.hash_detector4room.detect_alphabet_hash(roi_mask, threshold=0.2)
            if alphabet is None:
                continue
            if hamming_distance < curr_hamming_distance:
                curr_candidate = candidate
                curr_hamming_distance = hamming_distance
                # h_value = self.color_preprocessor.get_mean_value_for_non_zero(roi_thresholded)
                color = self.color_preprocessor.check_red_or_blue(roi)
                # if 95 <= h_value <= 135:
                #     candidate.set_color("BLUE")
                # elif h_value <= 20 or h_value >= 140 :
                #     candidate.set_color("RED")
                candidate.set_color(color)
                candidate.set_name(alphabet)

        if visualization:
            if curr_candidate:
                setLabel(canvas, candidate.get_pts(), f"{candidate.get_name()}-:{candidate.get_color()}", color=(0, 0, 255))
            cv2.imshow("src", cv2.hconcat([canvas, cv2.cvtColor(canny,cv2.COLOR_GRAY2BGR)]))
            cv2.waitKey(1)

        if curr_candidate:
            return curr_candidate.get_name(), curr_candidate.get_color()

        return None

    def get_arrow_direction(self):
        src = self.get_image()
        direction, _ = self.hash_detector4arrow.detect_arrow(src)
        return direction

    def get_area_color(self, threshold: float = 0.5, visualization: bool = False):
        src = self.get_image()
        hsv = cv2.cvtColor(src, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)
        h = h.astype(v.dtype)

        # red mask
        red_mask = self.color_preprocessor.get_red_mask(h)

        # blue mask
        blue_mask = self.color_preprocessor.get_blue_mask(h)

        # mask denoise
        mask = cv2.bitwise_or(red_mask, blue_mask)
        mask = cv2.GaussianBlur(mask, (5, 5), 0)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.bitwise_not(mask)

        # background : white, target: green, red, blue, black
        # ostu thresholding inverse : background -> black, target -> white
        _, roi_mask = cv2.threshold(v, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        roi_mask = cv2.morphologyEx(roi_mask, cv2.MORPH_OPEN, kernel)
        roi_mask = cv2.morphologyEx(roi_mask, cv2.MORPH_CLOSE, kernel)

        # subtract blue and red mask to ostu thresholded mask
        # masking
        roi_mask = cv2.bitwise_and(mask, roi_mask)
        h = cv2.bitwise_and(h, h, mask=roi_mask)

        # get mean value about non_zero value
        h_mean = self.color_preprocessor.get_mean_value_for_non_zero(h)

        # green
        green_upper = 85
        green_lower = 35
        green = np.where(h > green_lower, h, 0)
        green = np.where(green < green_upper, green, 0)

        pixel_rate = np.count_nonzero(green) / np.count_nonzero(h)

        if visualization:
            dst = cv2.bitwise_and(src, src, mask=roi_mask)
            cv2.imshow("dst", dst)
            cv2.waitKey(1)

        if green_lower <= h_mean <= green_upper and pixel_rate >= threshold:
            return "GREEN"
        else:
            return "BLACK"

    def get_yellow_line_corner_pos(self, visualization=False):
        pos = None
        src = self.get_image()
        src, yellow_img_mask = self.get_color_binary_image(src=src, color=self.COLORS["YELLOW"]["HOME"])
        yellow_img = cv2.bitwise_and(src,src,mask=yellow_img_mask)
        canny_img = auto_canny(yellow_img_mask)
        lines = cv2.HoughLinesP(canny_img, 2, np.pi / 180, threshold=50, minLineLength=50, maxLineGap=60)
        if lines is not None:
            if visualization:
                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    slope = (y2 - y1) / (x2 - x1)

                    if 0 <= slope < 1: # 노란색선
                        cv2.line(src, (x1, y1), (x2, y2), (0, 255, 255), 2)
                    elif slope >= 1: # 하늘색선
                        cv2.line(src, (x1, y1), (x2, y2), (255, 255, 0), 2)
                    elif slope <= -1 : # 초록색선
                        cv2.line(src, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    elif -1 < slope < 0: # 빨간색선
                        cv2.line(src, (x1, y1), (x2, y2), (255, 0, 255), 2)
                    else:
                        cv2.line(src, (x1, y1), (x2, y2), (255, 255, 255), 2)

            filtered_left_lns, filtered_right_lns = left_right_lines(lines)
            median_left_f = median(filtered_left_lns, [], [])
            median_right_f = median(filtered_right_lns, [], [])
            if median_left_f is not None and median_right_f is not None:
                intersect_pt = intersect(median_left_f, median_right_f)
                if intersect_pt is not None:
                    pos = tuple(intersect_pt)
                    print(pos)
                    if visualization :
                        center = (cx, cy) = (self.width // 2, self.height // 2)
                        x_range = 10
                        y_range = 20
                        if cx-x_range*10 <= pos[0] <= cx+x_range*10 :
                            cv2.circle(src, pos, 10, (255, 0, 0), -1)
                            cv2.putText(src, "IN", pos, cv2.FONT_HERSHEY_SIMPLEX, 1,(255, 0, 0), thickness=2)
                        else:
                            cv2.circle(src, pos, 10, (0, 0, 255), -1)
                            cv2.putText(src, "NOT IN", pos, cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), thickness=2)

                        cv2.line(src, (cx - x_range * 10, cy), (cx + x_range * 10, cy), (255, 0, 0), 2)
                        cv2.circle(src, center, 10, (255, 0, 0), 2)
                        for x_r in range(x_range + 1):
                            if x_r == 0 or x_r == x_range:
                                x_r *= 10
                                if x_r != 0:
                                    cv2.putText(src, "-%d" % x_r, (cx - x_r, cy - y_range), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                                (255, 0, 0), thickness=2)
                                    cv2.putText(src, "-%d" % x_r, (cx + x_r, cy - y_range), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                                (255, 0, 0), thickness=2)
                                else:
                                    cv2.putText(src, "0", (cx, cy - y_range), cv2.FONT_HERSHEY_SIMPLEX, 1,
                                                (255, 0, 0), thickness=2)

                                cv2.line(src, (cx - x_r, cy - y_range), (cx - x_r, cy + y_range), (255, 0, 0), 2)
                                cv2.line(src, (cx + x_r, cy - y_range), (cx + x_r, cy + y_range), (255, 0, 0), 2)
                            else:
                                y_r = y_range // 2
                                x_r *= 10
                                cv2.line(src, (cx - x_r, cy - y_r), (cx - x_r, cy + y_r), (255, 0, 0), 1)
                                cv2.line(src, (cx + x_r, cy - y_r), (cx + x_r, cy + y_r), (255, 0, 0), 1)
        else:
            if visualization:
                cv2.imshow("yellow_mask", yellow_img)
                cv2.imshow("canny", canny_img)
                cv2.imshow("line", src)
                cv2.waitKey(1)
            return None

        if visualization:
            cv2.imshow("yellow_mask", yellow_img)
            cv2.imshow("canny", canny_img)
            cv2.imshow("line", src)
            cv2.waitKey(1)
        return pos
    
    def get_cube_saferoom(self):
        img = self.get_image()
        
        red_lower = np.array([160, 100, 20])
        red_upper = np.array([179, 255, 255])

        blue_lower = np.array([100, 60, 60])
        blue_upper = np.array([140, 255, 255])
        
        kernel = np.ones((5, 5), np.uint8)
        
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        
        red_mask = cv2.inRange(hsv, red_lower, red_upper)
        red_mask = cv2.erode(red_mask, kernel, iterations=2)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
        red_mask = cv2.dilate(red_mask, kernel, iterations=1)
        
        (cnts, _) = cv2.findContours(red_mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        center = None
        if len(cnts) > 0:
            cnt = sorted(cnts, key = cv2.contourArea, reverse = True)[0]
            ((x, y), radius) = cv2.minEnclosingCircle(cnt)
            M = cv2.moments(cnt)
            center = (int(M['m10'] / M['m00']), int(M['m01'] / M['m00']))
            
            return center
        return None, None
    
    def get_saferoom_position(self):
        img = self.get_image()
        
        h, w = img.shape[:2]

        frame_center_x = w / 2
        frame_center_y = h / 2

        green_lower = np.array([40, 40, 40])
        green_upper = np.array([70, 255, 255])
        
        kernel = np.ones((5, 5), np.uint8)
        
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        _, saturation, _ = cv2.split(hsv)
        
        green_mask = cv2.inRange(hsv, green_lower, green_upper)
        green_mask = cv2.erode(green_mask, kernel, iterations=2)
        green_mask = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, kernel)
        green_mask = cv2.dilate(green_mask, kernel, iterations=1)
        
        _, binary = cv2.threshold(saturation, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        green_area_mask = cv2.bitwise_and(green_mask, binary)

        cnts, _ = cv2.findContours(green_area_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnt = None
        center = None, None

        if len(cnts) > 0:
            cnt = sorted(cnts, key = cv2.contourArea, reverse = True)[0]
            ((x, y), radius) = cv2.minEnclosingCircle(cnt)
            M = cv2.moments(cnt)
            center = (int(M['m10'] / M['m00']), int(M['m01'] / M['m00']))
        
        def distance(pt1, pt2):
            from math import sqrt
            return sqrt((pt1[0] - pt2[0]) ** 2 + (pt1[1] - pt2[1]) ** 2)
        
        max_dist = 0
        max_pos = 0, 0
        for pos in cnt:
            if max_dist < distance((frame_center_x, 0), pos[0]):
                max_pos = pos[0]

        return max_pos

    def line_tracing(self, color: str = "YELLOW", line_visualization:bool=False, edge_visualization:bool=False):
        src = self.get_image()
        result = (line_info, edge_info, src) = self.line_detector.get_all_lines(src=src, color=color, line_visualization = line_visualization, edge_visualization = edge_visualization)
        if line_visualization or edge_visualization :
            cv2.imshow("line", src)
            cv2.waitKey(1)
        return result


    def test(self):
        src = self.get_image(visualization=True)
        ycrcb = cv2.cvtColor(src, cv2.COLOR_BGR2YCrCb)
        hsv = cv2.cvtColor(src, cv2.COLOR_BGR2HSV)
        y, cr, cb = cv2.split(ycrcb)
        h, s, v = cv2.split(hsv)

        n_cr = cv2.normalize(cr, None, 0, 255, cv2.NORM_MINMAX)
        n_cb = cv2.normalize(cb, None, 0, 255, cv2.NORM_MINMAX)
        #y = cv2.normalize(y, None, 0, 255, cv2.NORM_MINMAX)
        v = cv2.normalize(v, None, 0, 255, cv2.NORM_MINMAX)

        _, y_mask = cv2.threshold(y, thresh=0, maxval=255, type=cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)
        ycrcb = cv2.merge([y, cr, cb])
        dst = cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)
        dst = cv2.bitwise_and(dst, dst, mask=y_mask)
        v1 = cv2.hconcat([n_cr, n_cb])
        v2 = cv2.hconcat([src, dst])
        v3 = cv2.hconcat([y, v])
        cv2.imshow("result", cv2.vconcat([v1, v3]))

        #cv2.imshow("crcb", v1)
        cv2.imshow('dst', v2)
        cv2.waitKey(1)

    def test1(self):
        src = self.get_image()
        # b, g, r = cv2.split(src)
        # hls = cv2.cvtColor(src, cv2.COLOR_BGR2HLS)
        # h, l, s = cv2.split(hls)
        # hls = cv2.hconcat([h, l, s])
        # cv2.putText(hls, "HLS", (70, 70), cv2.FONT_HERSHEY_SIMPLEX, 3, (255,255,255),5)
        # hsv = cv2.cvtColor(src, cv2.COLOR_BGR2HSV)
        # h, s, v = cv2.split(hsv)
        # hsv = cv2.hconcat([h,s,v])
        # cv2.putText(hsv, "HSV", (70, 70), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 255), 5)
        # lab = cv2.cvtColor(src, cv2.COLOR_BGR2LAB)
        # l, a, b = cv2.split(lab)
        # lab = cv2.hconcat([l, a, b])
        # cv2.putText(lab, "LAB", (70, 70), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 255), 5)
        # xyz = cv2.cvtColor(src, cv2.COLOR_BGR2XYZ)
        # x, y, z = cv2.split(xyz)
        # xyz = cv2.hconcat([x, y, z])
        # cv2.putText(xyz, "XYZ", (70, 70), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 255), 5)
        ycrcb = cv2.cvtColor(src, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)
        ycrcb = cv2.hconcat([y, cr, cb])
        cv2.putText(ycrcb, "YCrCb", (70, 70), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 255), 5)
        cr = cv2.normalize(cr, None, 0, 255, cv2.NORM_MINMAX)
        cb = cv2.normalize(cb, None, 0, 255, cv2.NORM_MINMAX)
        y = cv2.normalize(y, None, 0, 255, cv2.NORM_MINMAX)
        normalized_ycrcb = cv2.hconcat([y, cr, cb])
        cv2.putText(normalized_ycrcb, "normalized_YCrCb", (70, 70), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 255, 255), 5)
        #result = cv2.vconcat([hls, hsv, lab, xyz, ycrcb])
        result = cv2.vconcat([ycrcb, normalized_ycrcb])

        cv2.imshow("result", result)

        cv2.waitKey(1)

    def test2(self):
        src = self.get_image()
        hls = cv2.cvtColor(src, cv2.COLOR_BGR2HLS)
        h, l, s = cv2.split(hls)
        #g = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(s, 40, 255, cv2.THRESH_BINARY)
        green_upper = 80
        green_lower = 20
        ycrcb = cv2.cvtColor(src, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)
        self.color_preprocessor.get_green_mask(h)
        cr = cv2.bitwise_and(cr, cr, mask=mask)
        cb = cv2.bitwise_and(cb, cb, mask=mask)
        cr = cv2.normalize(cr, None, 0, 255, cv2.NORM_MINMAX)
        cb = cv2.normalize(cb, None, 0, 255, cv2.NORM_MINMAX)
        _, cr = cv2.threshold(cr, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        _, cb = cv2.threshold(cb, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        ycrcb = cv2.hconcat([y, cr, cb])
        cv2.imshow("mask", ycrcb)
        cv2.waitKey(1)

    def get_alphabet_info(self, visualization=False) -> tuple:
        src = self.get_image()
        if visualization:
            canvas = src.copy()
        alphabet_info = None
        candidates = []
        blur = cv2.GaussianBlur(src, (5, 5), 0)
        hls = cv2.cvtColor(blur, cv2.COLOR_BGR2HLS)
        h, l, s = cv2.split(hls)
        _, mask = cv2.threshold(s, 70, 255, cv2.THRESH_BINARY)

        #red_mask = self.color_preprocessor.get_red_mask(h)
        #blue_mask = self.color_preprocessor.get_blue_mask(h)
        #color_mask = cv2.bitwise_or(blue_mask, red_mask)
        #mask = cv2.bitwise_and(mask, color_mask)
        _, _, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)
        for idx, centroid in enumerate(centroids):  # enumerate 함수는 순서가 있는 자료형을 받아 인덱스와 데이터를 반환한다.
            if stats[idx][0] == 0 and stats[idx][1] == 0:
                continue

            if np.any(np.isnan(centroid)): # 배열에 하나이상의 원소라도 참이라면 true (즉, 하나이상의 중심점이 숫자가 아니면)
                continue
            _, _, width, height, area = stats[idx]

            # roi의 가로 세로 종횡비를 구한 뒤 1:1의 비율에 근접한 roi만 통과
            area_ratio = width / height if height < width else height / width
            area_ratio = round(area_ratio, 2)
            if not (800 < area < 8000 and area_ratio <= 1.7):
                continue

            candidate = Target(name=str(area_ratio),stats=stats[idx], centroid=centroid)
            roi = candidate.get_target_roi(src, pad=5)

            # ycrcb 색공간을 이용해

            candidate.set_color(self.color_preprocessor.check_red_or_blue(roi))
            candidate_color = candidate.get_color()

            thresholding = None
            ycrcb = cv2.cvtColor(roi, cv2.COLOR_BGR2YCrCb)
            y, cr, cb = cv2.split(ycrcb)
            if candidate_color == "RED":
                thresholding = cv2.normalize(cr, None, 0, 255, cv2.NORM_MINMAX)

            else:
                thresholding = cv2.normalize(cb, None, 0, 255, cv2.NORM_MINMAX)
            _, roi_mask = cv2.threshold(thresholding, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

            ### 정확도 향상을 위해 아래 함수 수정 요망 ###
            candidate_alphabet,_ = self.hash_detector4room.detect_alphabet_hash(roi_mask, threshold=0.2)
            ####################################

            #if visualization:
            #   cv2.imshow("thresh", cv2.hconcat([thresholding, roi_mask]))

            if candidate_alphabet is None:
                continue
            candidate.set_name(candidate_alphabet)
            if visualization:

                setLabel(canvas, candidate.get_pts(), label=f"{candidate.get_name()}", color=(255, 255, 255))
            candidates.append(candidate)

        if candidates:
            candidates.sort(key=lambda candidate: candidate.get_center_pos()[1])
            selected = candidates[0]
            alphabet_info = (selected.get_color(), selected.get_name())
            if visualization:
                setLabel(canvas, selected.get_pts(), color=(0, 0, 255))

        if visualization:
            cv2.imshow("src", canvas)
            cv2.waitKey(1)

        return alphabet_info

    def get_green_area_corner(self, visualization=True):
        src = self.get_image()
        result = (line_info, edge_info, src) = self.line_detector.get_all_lines(src=src, color="GREEN",
                                                                                line_visualization=False,
                                                                                edge_visualization=False)
        pos = edge_info["EDGE_POS"]
        if visualization:
            if pos:
                (x, y) = pos
                cv2.circle(src, pos, 10, (0, 0, 255), -1)
            cv2.imshow("result", src)
            cv2.waitKey(1)
        return pos



if __name__ == "__main__":

    imageProcessor = ImageProcessor(video_path="src/green_room_test/green_area1.h264")
    #imageProcessor = ImageProcessor(video_path="")
    imageProcessor.fps.start()
    while True:
        result = imageProcessor.get_alphabet_info(visualization=True)
        print(result)
        #imageProcessor.line_tracing(color="GREEN", line_visualization=True)
        #imageProcessor.get_image(visualization=True)
        #imageProcessor.get_green_area_corner()

