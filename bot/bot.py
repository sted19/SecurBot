import socket

from io import BytesIO

from telegram.ext import Updater
from telegram.ext import CommandHandler
import telegram
import threading

import os
import time

lock = threading.Lock()

TOKEN_PATH = os.path.join(os.getcwd(),"token.txt")
token_file = open(TOKEN_PATH,"r")
token = token_file.readline().strip("\n")

#l'updater eseguirà le sue funzioni in un thread separato
updater = Updater(token=token)
bot = telegram.Bot(token=token)
dispatcher = updater.dispatcher

active_sockets = {}

class ClientHandler(threading.Thread):
   def __init__(self, conn):
      threading.Thread.__init__(self)
      self.conn = conn
    
   def run(self):
      print ("Thread '" + self.name + "' started")
      handle(self.conn)

class CheckerThread(threading.Thread):
   def __init__(self):
      threading.Thread.__init__(self)
    
   def run(self):
      print ("Thread '" + self.name + "' started")
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
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as s:
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

def id(bot,update):
    bot.send_message(chat_id=update.message.chat_id, text="your id is {}".format(update.message.chat_id))

def grant(bot,update):
    found = False
    key_found = None
    lock.acquire()
    for key in active_sockets:
        if str(key) == str(update.message.chat_id):
            active_sockets[key][0].sendall(b'Access granted')
            found = True
            key_found = key
            break
    lock.release()
    if found:
        bot.send_message(chat_id = update.message.chat_id, text="Access granted!")
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
    image = conn.recv(98304)
    conn.sendall(b'image received')
    id_num = str(conn.recv(1024).decode("utf-8"))
    print("image and id have been received, this is the id_num: ",id_num)

    bio = BytesIO(image)
    bot.sendPhoto(id_num,bio)

    lock.acquire()
    active_sockets[id_num] = [conn,0]
    lock.release()

def check():
    while True:
        lock.acquire()
        for key in active_sockets:
            if active_sockets[key][1] >= 10:
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

if __name__ == "__main__":
    run_telegram_bot()
    run_checker()
    run_server()