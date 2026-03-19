import cv2
import time
import os

cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
time.sleep(2)

ret, frame = cam.read()

if ret:
    path = os.path.abspath("test_photo.jpg")
    cv2.imwrite(path, frame)
    print("Photo saved at:", path)
else:
    print("Camera not working")

cam.release()





