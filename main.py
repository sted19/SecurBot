from sklearn.neighbors import NearestNeighbors
import cv2 as cv
import os
import asyncio
import websockets
import time
import socket
import threading
import struct



UTILS = os.path.join(os.getcwd(),"utils")
DATA = os.path.join(os.getcwd(),"data")

ID_DIR = os.path.join(DATA,"id")
ID_PATH = os.path.join(ID_DIR,"id.txt")

id_num = None
url = "ws://127.0.0.1:8082"

IMAGES_PATH = os.path.join(DATA,"images")
GRANTED_PATH = os.path.join(IMAGES_PATH,"granted")
threshold = 0.7

ACCESS_GRANTED = 17
ACCESS_DENIED = -17

NUM_NEIGHBORS = 6

OPEN_FACE_PATH = os.path.join(UTILS,"opencv-face-recognition")
EMBEDDER_PATH = os.path.join(OPEN_FACE_PATH,"openface_nn4.small2.v1.t7")

HAARCASCADE_PATH = os.path.join(UTILS,"haarcascade_xmls")
FRONTAL_FACE_XML_PATH = os.path.join(HAARCASCADE_PATH,"haarcascade_frontalface_default.xml")
PROFILE_FACE_XML_PATH = os.path.join(HAARCASCADE_PATH,"haarcascade_profileface.xml")

embedder = cv.dnn.readNetFromTorch(EMBEDDER_PATH)

class SenderThread(threading.Thread):
   def __init__(self, image_to_send,image_to_save):
      threading.Thread.__init__(self)
      self.image_to_send = image_to_send
      self.image_to_save = image_to_save
    
   def run(self):
      print ("Thread '" + self.name + "' avviato")
      res = nearest_neighbors(self.image_to_save)
      websocket_handler(res,self.image_to_send,self.image_to_save)

def image_to_feature_vector(img):
    # create 4-dimensional tensor, (1,3,96,96) with every element scaled of a factor of 255, with zeroes subtracted from each RGB value, with no swapping R and B channels nor cropping
    img_blob = cv.dnn.blobFromImage(img,1.0 / 255,(96, 96), (0, 0, 0), swapRB=True, crop=False)
    embedder.setInput(img_blob)
    vec = embedder.forward().flatten()
    return vec

def nearest_neighbors(image_to_check):
    feature_vectors = []

    if not os.path.isdir(GRANTED_PATH):
        if not os.path.isdir(IMAGES_PATH):
            os.makedirs(IMAGES_PATH)
        os.makedirs(GRANTED_PATH)

    if len(os.listdir(GRANTED_PATH)) >= NUM_NEIGHBORS:
        dataset_images = sorted(os.listdir(GRANTED_PATH))
        for image_name in dataset_images:
            image_path = os.path.join(GRANTED_PATH,image_name)
            image = cv.imread(image_path)
            feature_vector = image_to_feature_vector(image)
            feature_vectors.append(feature_vector)
            #print("loaded image numer: {} with name {}".format(num,image_name))


        neigh = NearestNeighbors(n_neighbors = NUM_NEIGHBORS)
        neigh.fit(feature_vectors)

        image_to_check = [image_to_feature_vector(image_to_check)]
        result = neigh.kneighbors(image_to_check)
        print(result)
        distances = result[0][0]
        image_numbers = result[1][0]
        if distances[0] < threshold:
            print("Access granted through facial recognition")
            return 1
        return 0
    
    return 0


# given an image, and id, send everything to the telegram bot at address url
def websocket_handler(granted,image,image_to_save):
    # to handle different communication in case of facial recognition (it's the same for now)
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
        s.connect(("127.0.0.1",8083))

        to_send = struct.pack("<q",granted)
        s.sendall(to_send)

        image_len = struct.pack("<q",len(image))
        s.sendall(image_len)

        s.sendall(image)

        id_to_send = struct.pack("<q",int(id_num))
        s.sendall(id_to_send)

        #access already granted, double check to see if it's correct
        try:
            answer = receive_bytes(s,8)
            answer = struct.unpack("<q",answer)[0]
            if answer == ACCESS_GRANTED:
                next_number = str(int(sorted(os.listdir(GRANTED_PATH))[-1].split(".")[0]) + 1)
                cv.imwrite(os.path.join(GRANTED_PATH,next_number+".jpg"),image_to_save)
                print("image saved")
            elif granted == 0 and answer == ACCESS_DENIED:
                print("access denied")
            else:
                pass
        except RuntimeError:
            print("socket closed, no answer")
            


def get_id():
    id = None
    if not os.path.isdir(DATA):
        os.makedirs(DATA)
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

    

# function that detects faces and draws rectangles, max_area behaviour still not specified if two or more people are in front of the camera
def detect_face(frame,g_frame,cascade):
    faces = cascade.detectMultiScale(g_frame, 1.3, 5)
    if (len(faces) == 0):
        return 0,0,None
    else:
        for (x,y,w,h) in faces:
            cv.rectangle(g_frame, (x,y), (x+w,y+h), (255,0,0), 2)
            area = w*h
            crop = frame[y:y+h,x:x+w]
        return 1,area,crop

# function that detects profiles and draws rectangles
def detect_profile(g_frame,  cascade):
    profiles = cascade.detectMultiScale(g_frame, 1.3, 5)
    if (len(profiles) == 0):
        return 0
    else:
        for (x,y,w,h) in profiles:
            cv.rectangle(g_frame, (x,y), (x+w,y+h), (0,0,255), 2)
        return 1

def camera_loop():
    cap = cv.VideoCapture(0)
    if (not cap.isOpened()):
        print("failed to open videocapture\n")
        exit(1)

    face_cascade = cv.CascadeClassifier(FRONTAL_FACE_XML_PATH)
    profile_cascade = cv.CascadeClassifier(PROFILE_FACE_XML_PATH)
    
    count = 0 
    present = 0
    present_limit = 30
    not_present_limit = 50
    image_number = 0
    frame = None

    max_area = 0
    image_to_save = None

    while(cap.isOpened()):
        ret, frame = cap.read()
        if (ret == False):
            print("no frames have been grabbed\n")
            exit(1)
        gray_frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

        # check for faces or profiles
        ret_f,area,crop = detect_face(frame, gray_frame, face_cascade)
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
            if area > max_area:
                max_area = area
                image_to_save = crop
                

        
        # someone has been in front of the camera for x seconds, save an image of him
        if (present >= present_limit):
            # websocket sends image to telegram bot
            encoded, buffer = cv.imencode(".jpg",frame)

            print(len(buffer))
            
            image_to_send = buffer.copy().tobytes()


            sender = SenderThread(image_to_send,image_to_save.copy())
            sender.start()

            area = 0
            present = 0
            present_limit = present_limit * 100
            image_number += 1
            
        # show camera frames
        cv.imshow("frame", gray_frame)

        if cv.waitKey(1) & 0xFF == ord("q"):
            break
        
        time.sleep(0.009)


    cap.release()
    cv.destroyAllWindows()

def receive_bytes(conn, num_bytes):
    message = b''
    while len(message) < num_bytes:
        message += conn.recv(num_bytes - len(message))
        if message == b'':
            raise RuntimeError("Socket connection broken")
    return message

if __name__ == "__main__":
    id_num = get_id()
    if (id_num == None):
        print("there were some problems getting the ID number\n")
        exit(-1)
    
    camera_loop()