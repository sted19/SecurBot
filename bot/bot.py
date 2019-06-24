import socket

from io import BytesIO
import struct

from telegram.ext import Updater
from telegram.ext import CommandHandler
import telegram
import threading
import atexit

import os
import time

ACCESS_GRANTED_REC = 1
SAVE_PICTURE = 18
ACCESS_GRANTED = 17
ACCESS_DENIED = -17

lock = threading.Lock()

TOKEN_PATH = os.path.join(os.getcwd(),"token.txt")
token_file = open(TOKEN_PATH,"r")
token = token_file.readline().strip("\n")

#l'updater eseguirà le sue funzioni in un thread separato
updater = Updater(token=token)
bot = telegram.Bot(token=token)
dispatcher = updater.dispatcher

s = None
active_sockets = {}

class ClientHandler(threading.Thread):
   def __init__(self, conn):
      threading.Thread.__init__(self)
      self.conn = conn
    
   def run(self):
      print ("Thread '" + self.name + "' ClientHandler started")
      handle(self.conn)

class CheckerThread(threading.Thread):
   def __init__(self):
      threading.Thread.__init__(self)
    
   def run(self):
      print ("Thread '" + self.name + "' checker started")
      check()

def run_telegram_bot():
    start_handler = CommandHandler("start",start)
    dispatcher.add_handler(start_handler)

    id_handler = CommandHandler("id",id)
    dispatcher.add_handler(id_handler)

    grant_handler = CommandHandler("grant",grant)
    dispatcher.add_handler(grant_handler)

    deny_handler = CommandHandler("deny",deny)
    dispatcher.add_handler(deny_handler)

    save_handler = CommandHandler("save",save)
    dispatcher.add_handler(save_handler)

    updater.start_polling()

def run_server():
    atexit.register(on_exit)
    global s 
    s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    
    # handle fast reconnections to the same address setting the value of socket.SO_REUSEADDR to , remove this line after debugging to have a safer connection
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    s.bind(("127.0.0.1",8083))
    s.listen()
    while True:
        conn, addr = s.accept()
        print("connected by address: ",addr)
        client_handler = ClientHandler(conn)
        client_handler.start()

def run_checker():
    checker = CheckerThread()
    checker.start()
    
def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Welcome to AtMyDoor bot! Your ID number is {}".format(update.message.chat_id))
    bot.send_message(chat_id=update.message.chat_id, text="To start using this bot, insert your ID number in the camera app when requested and launch it!")

def id(bot,update):
    bot.send_message(chat_id=update.message.chat_id, text="your id is {}".format(update.message.chat_id))

def save(bot,update):
    found = False
    lock.acquire()
    for key in active_sockets:
        if str(key) == str(update.message.chat_id):
            if active_sockets[key][2] == ACCESS_GRANTED_REC:
                #send things to save the picture and than close the socket
                active_sockets[key][0].sendall(struct.pack("<q",SAVE_PICTURE))
                found = True
                active_sockets[key][0].close()
                del active_sockets[key]
                break
            else:
                break
    lock.release()
    if found:
        bot.send_message(chat_id = update.message.chat_id, text="Image saved!")
    else:
        bot.send_message(chat_id = update.message.chat_id, text="There's nothing to save anymore!")
    

def grant(bot,update):
    found = False
    lock.acquire()
    for key in active_sockets:
        if str(key) == str(update.message.chat_id):
            # If grant is received afer access has already been granted through facial recognition, do nothing
            if active_sockets[key][2] == ACCESS_GRANTED_REC:
                break
            else:
                # In this way the access is granted and the image is saved 
                active_sockets[key][0].sendall(struct.pack("<q",ACCESS_GRANTED))
                found = True
                active_sockets[key][0].close()
                del active_sockets[key]
                break
    lock.release()
    if found:
        bot.send_message(chat_id = update.message.chat_id, text="Access granted and image saved!")
    else:
        bot.send_message(chat_id = update.message.chat_id, text="There's nothing to grant anymore!")

def deny(bot,update):
    found = False
    lock.acquire()
    for key in active_sockets:
        if str(key) == str(update.message.chat_id):
            if active_sockets[key][2] == ACCESS_GRANTED_REC:
                break
            else:
                active_sockets[key][0].sendall(struct.pack("<q",ACCESS_DENIED))
                found = True
                active_sockets[key][0].close()
                del active_sockets[key]
                break
    lock.release()
    if found:
        bot.send_message(chat_id = update.message.chat_id, text="Access denied!")
    else:
        bot.send_message(chat_id = update.message.chat_id, text="There's nothing to deny anymore!")
    


def handle(conn):
    granted = receive_bytes(conn,8)
    granted = int(struct.unpack("<q",granted)[0])
    if granted:
        print("access already granted through facial recognition")

    image_len = receive_bytes(conn,8)
    image_len = int(struct.unpack("<q",image_len)[0])
    print(image_len)

    image = receive_bytes(conn,image_len)
    print("sent image of size: ",len(image))
    
    id_num = receive_bytes(conn,8)
    id_num = int(struct.unpack("<q",id_num)[0])
    print("image and id have been received, this is the id_num: ",id_num)

    bio = BytesIO(image)
    bot.sendPhoto(id_num,bio)

    if granted == 1:
        bot.send_message(chat_id=id_num, text="Access granted through facial recognition, answer '/save' to save the picture")
    else:
        bot.send_message(chat_id=id_num, text="This person is at your door! Send \grant to grant access, /deny to deny it!")

    lock.acquire()
    active_sockets[id_num] = [conn,0,ACCESS_GRANTED_REC]
    lock.release()

def check():
    while True:
        lock.acquire()
        for key in active_sockets:
            if active_sockets[key][1] >= 50:
                try:
                    active_sockets[key][0].close()
                    del active_sockets[key]
                except:
                    print("socket already closed and removed")
                break
            else:
                active_sockets[key][1] += 5
        lock.release()
        time.sleep(5)

def on_exit():
    lock.acquire()
    for key in active_sockets:
        active_sockets[key][0].close()
        print("closed: ",key)
    lock.release()
    s.close()

def receive_bytes(conn, num_bytes):
    message = b''
    while len(message) < num_bytes:
        message += conn.recv(num_bytes - len(message))
        if message == b'':
            raise RuntimeError("Socket connection broken")
    return message


if __name__ == "__main__":
    run_telegram_bot()
    run_checker()
    run_server()