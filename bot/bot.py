import asyncio
import websockets

from io import BytesIO
from PIL import Image

from telegram.ext import Updater
from telegram.ext import CommandHandler
import telegram

import time

import os


bio = BytesIO()
token_file = open("./token.txt","r")
token = token_file.readline().strip("\n")

updater = Updater(token=token)
dispatcher = updater.dispatcher
bot = telegram.Bot(token=token)

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

def start(bot, update):
    messaggio = bot.send_message(chat_id=update.message.chat_id, text="Welcome to AtMyDoor bot! Your ID number is {}".format(update.message.chat_id))


async def receive(websocket, path):
    image = await websocket.recv()
    print("image received")
    
    image = Image.open(BytesIO(image))
    bio.name = 'image.jpeg'
    image.save(bio, 'JPEG')
    bio.seek(0)
    
    bot.sendPhoto(ids[0],bio)

    send = "thanks"
    
    await websocket.send(send)


if __name__ == "__main__":
    start_handler = CommandHandler("start",start)
    dispatcher.add_handler(start_handler)
    updater.start_polling()

    start_server = websockets.serve(receive, "localhost", 8082)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
