import requests

# given an image, and id, send everything to the telegram bot at address "address"
def send_request(address, image, id):
    #message = {"image": image, "id":id}
    message = {"image":"my_image", "text":"ciao"}
    response = requests.post(address,message)
    if response.status_code == 200:
        print("message sent correctly!\n")
    else:
        print("error sending message!\n")