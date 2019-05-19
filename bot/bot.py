from http.server import BaseHTTPRequestHandler, HTTPServer

import telepot
from telepot.loop import MessageLoop

from pprint import pprint

from urllib.parse import urlparse

import json

import time

import os

token_file = open("./token.txt","r")
token = token_file.readline().strip("\n")
my_bot = telepot.Bot(token)
print(my_bot.getMe())

def get_ids():
    chat_ids = open("./ids_dict.txt","r")
    lines = chat_ids.readlines()
    lists = []
    for line in lines:
        lists.append(line.split(";"))
    ids = []
    for line in lists:
        if line[0].strip() != "":
            ids.append(line[0].strip("\n"))
    return ids

ids = get_ids()


class my_http_request_handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        if os.path.isfile("./image.jpeg"):
            img = open("./image.jpeg","rb")
            my_bot.sendPhoto(ids[0],img)
        self.wfile.write(bytes("foto inviata","utf8"))
        return

    # to-implement, actions to do after a POST request containing an image
    def do_POST(self):
        self.send_response(200)

        content_len = int(self.headers.get("Content-Length"))
        body = self.rfile.read(content_len).decode("utf-8")
        obj = json.loads(body)

        print("got {}:".format(obj))
            
        self.send_header('Content-type','text/html')
        self.end_headers()

        print()
        return



# setup of http server
def server_setup():
    print('Avvio del server...')
    server_address = ("127.0.0.1",8081)
    httpd = HTTPServer(server_address,my_http_request_handler)
    httpd.serve_forever()


# function to handle messages received from telegram
def handle_message(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    print(content_type, chat_type, chat_id)

    if (content_type == "text"):
        if msg["text"] == "/start":
            if str(chat_id) not in ids:
                print("saving new user id\n")
                write_ids = open("./ids_dict.txt","a+")
                write_ids.write(str(chat_id)+";"+str(msg["chat"]["username"]))
                write_ids.write(os.linesep)
                write_ids.close()
                ids.append(str(chat_id))
            else:
                print("id found!\n")
        my_bot.sendMessage(chat_id,msg["text"])

if __name__ == "__main__":
    MessageLoop(my_bot,handle_message).run_as_thread()
    server_setup()
