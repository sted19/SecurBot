import numpy as np
import cv2 as cv
import request_handler
import base64
import asyncio


face_cascade = cv.CascadeClassifier("./xmls/haarcascade_frontalface_default.xml")
profile_cascade = cv.CascadeClassifier("./xmls/haarcascade_profileface.xml")

cap = cv.VideoCapture(0)
if (not cap.isOpened()):
    print("failed to open videocapture\n")
    exit(1)

fourcc = cv.VideoWriter_fourcc(*"XVID")
writer = cv.VideoWriter("./videotape_0.avi",fourcc,float(24),(640,480),False)

count = 0
present = 0
limit = 50
w_num = 0
image_number = 0

# function that detects faces and draws rectangles
def detect_face(g_frame,cascade):
    faces = cascade.detectMultiScale(g_frame, 1.3, 5)
    if (len(faces) == 0):
        return 0
    else:
        for (x,y,w,h) in faces:
            cv.rectangle(g_frame, (x,y), (x+w,y+h), (255,0,0), 2)
        return 1

# function that detects profiles and draws rectangles
def detect_profile(g_frame,  cascade):
    profiles = cascade.detectMultiScale(g_frame, 1.3, 5)
    if (len(profiles) == 0):
        return 0
    else:
        for (x,y,w,h) in profiles:
            cv.rectangle(g_frame, (x,y), (x+w,y+h), (0,0,255), 2)
        return 1




while(cap.isOpened()):
    ret, frame = cap.read()
    if (ret == False):
        print("no frames have been grabbed\n")
        exit(1)
    gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

    # check for faces or profiles
    ret_f = detect_face(gray_frame, face_cascade)
    ret_p = detect_profile(gray_frame, profile_cascade)

    # no-one is in front the camera
    if (ret_f == 0 and ret_p == 0):
        count += 1
        if count >= 50:
            present = 0
            limit = 50
            if(writer.isOpened()):
                print("releasing videoWriter\n")
                writer.release()
                w_num += 1
    # someone has been detected
    else:
        count = 0 
        present += 1
        if (writer.isOpened()):
            pass
        else:
            writer = cv.VideoWriter("./videotape_{}.avi".format(w_num),fourcc,24.0,(640,480))
    
    # someone has been in front of the camera for x seconds, save an image of him
    if (present >= limit):
        print("saving an image of the guest\n")
        cv.imwrite("./images/image_{}.jpg".format(image_number),frame)

        # http module sends image to telegram bot
        encoded, buffer = cv.imencode(".jpg",frame)
        asyncio.get_event_loop().run_until_complete(request_handler.send_request("ws://127.0.0.1:8082",buffer.tobytes(),190))

        image_number += 1
        present = 0
        limit += limit
    
    if (writer.isOpened()):
        writer.write(gray_frame)
           
    
    cv.imshow("frame", gray_frame)

    if cv.waitKey(10) & 0xFF == ord("q"):
        break

cap.release()
writer.release()
cv.destroyAllWindows()