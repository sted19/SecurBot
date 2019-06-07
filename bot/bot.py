import socket

from io import BytesIO

from telegram.ext import Updater
from telegram.ext import CommandHandler
import telegram
import threading
import atexit

import os
import time

GRANTED = "GRANTED"

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

def grant(bot,update):
    found = False
    key_found = None
    lock.acquire()
    for key in active_sockets:
        if str(key) == str(update.message.chat_id):
            active_sockets[key][0].sendall(GRANTED.encode("utf-8").strip())
            found = True
            key_found = key
            break
    lock.release()
    if found:
        bot.send_message(chat_id = update.message.chat_id, text="Access granted and Image Saved!")
        lock.acquire()
        try:
            active_sockets[key_found][0].close()
            del active_sockets[key_found]
        except:
            print("socket already closed and removed")
        lock.release()
    else:
        bot.send_message(chat_id = update.message.chat_id, text="You waited too long to answer")

def deny(bot,update):
    found = False
    key_found = None
    lock.acquire()
    for key in active_sockets:
        if str(key) == str(update.message.chat_id):
            active_sockets[key][0].sendall(b'Access denied')
            found = True
            key_found = key
            break
    lock.release()
    if found:
        bot.send_message(chat_id = update.message.chat_id, text="Access denied!")
        lock.acquire()
        try:
            active_sockets[key_found][0].close()
            del active_sockets[key_found]
        except:
            print("socket already closed and removed")
        lock.release()
    else:
        bot.send_message(chat_id = update.message.chat_id, text="You waited too long to answer")
    


def handle(conn):
    granted = str(conn.recv(1024).decode("utf-8"))
    print(granted)

    conn.sendall(b'ack')

    image = conn.recv(98304)
    print(len(image))

    conn.sendall(b'image received')
    
    id_num = str(conn.recv(1024).decode("utf-8"))
    print("image and id have been received, this is the id_num: ",id_num)

    bio = BytesIO(image)
    bot.sendPhoto(id_num,bio)

    if granted == "1":
        bot.send_message(chat_id=id_num, text="Access granted through facial recognition, answer /grant to this message to save the picture")
    else:
        bot.send_message(chat_id=id_num, text="This man/woman is at your door! Send \grant to grant access, /deny to deny it! (/grant will also save the picture)")

    lock.acquire()
    active_sockets[id_num] = [conn,0]
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

if __name__ == "__main__":
    run_telegram_bot()
    run_checker()
    run_server()