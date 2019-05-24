import cv2 as cv
import asyncio
import os

import message_handler

ID_DIR = os.path.join(os.getcwd(),"data")
ID_PATH = os.path.join(ID_DIR,"id.txt")


def get_id():
    id = None
    if not os.path.isdir(ID_DIR):
        os.makedirs(ID_DIR)
    if os.path.exists(ID_PATH):
        id_file = open(ID_PATH,"r")
        id = id_file.read().strip("\n")
        id_file.close()
    else:
        id_file = open(ID_PATH,"w")
        id = input("insert yout telegram ID (to get yours send '/id' to AtMyDoor bot)\n")
        id_file.write(id)
        id_file.close()
    return id

    

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

def camera_loop(cap,id):
    cap = cv.VideoCapture(0)
    if (not cap.isOpened()):
        print("failed to open videocapture\n")
        exit(1)

    face_cascade = cv.CascadeClassifier("./xmls/haarcascade_frontalface_default.xml")
    profile_cascade = cv.CascadeClassifier("./xmls/haarcascade_profileface.xml")
    
    count = 0 
    present = 0
    present_limit = 30
    not_present_limit = 50
    image_number = 0
    frame = None

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
            if count >= not_present_limit:
                present = 0
                present_limit = 30
        # someone has been detected
        else:
            count = 0 
            present += 1
        
        # someone has been in front of the camera for x seconds, save an image of him
        if (present >= present_limit):
            # websocket sends image to telegram bot
            encoded, buffer = cv.imencode(".jpg",frame)
            asyncio.get_event_loop().run_until_complete(message_handler.send_message("ws://127.0.0.1:8082",buffer.tobytes(),id))

            present = 0
            present_limit += present_limit
            image_number += 1
            
        # show camera frames
        cv.imshow("frame", gray_frame)

        if cv.waitKey(10) & 0xFF == ord("q"):
            break

    cap.release()
    cv.destroyAllWindows()

if __name__ == "__main__":
    id = get_id()
    if (id == None):
        print("there were some problems getting the ID\n")
        exit(-1)

    camera_loop(id)