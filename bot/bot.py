import asyncio
import websockets

from io import BytesIO

from telegram.ext import Updater
from telegram.ext import CommandHandler
import telegram

import os

TOKEN_PATH = os.path.join(os.getcwd(),"token.txt")
token_file = open(TOKEN_PATH,"r")
token = token_file.readline().strip("\n")
updater = Updater(token=token)
bot = telegram.Bot(token=token)
dispatcher = updater.dispatcher



def run_telegram_bot():
    start_handler = CommandHandler("start",start)
    dispatcher.add_handler(start_handler)

    id_handler = CommandHandler("id",id)
    dispatcher.add_handler(id_handler)

    updater.start_polling()

def run_server():
    start_server = websockets.serve(receive, "localhost", 8082)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()


def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Welcome to AtMyDoor bot! Your ID number is {}".format(update.message.chat_id))

def id(bot,update):
    bot.send_message(chat_id=update.message.chat_id, text="your id is {}".format(update.message.chat_id))


async def receive(websocket, path):
    image = await websocket.recv()
    id_num = await websocket.recv()
    print("image and id have been received")

    bio = BytesIO(image)
    bot.sendPhoto(id_num,bio)


if __name__ == "__main__":
    run_telegram_bot()
    run_server()