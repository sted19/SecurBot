import requests
import json
import asyncio
import websockets

# given an image, and id, send everything to the telegram bot at address url
async def send_request(url, image, id):

    async with websockets.connect(url) as websocket:

        await websocket.send(image)
        print("image sent\n")

        received = await websocket.recv()
        print(received)