import websockets

# given an image, and id, send everything to the telegram bot at address url
async def send_message(url, image, id):
    async with websockets.connect(url) as websocket:
        await websocket.send(image)
        await websocket.send(id)
        print("image and id have been sent")