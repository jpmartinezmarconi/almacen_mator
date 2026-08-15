import requests

TOKEN = "8340996429:AAGg7feiA1u3lo_yH5P7mM3VO325YSVM3rU"
CHAT_ID = "8937017185"

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": mensaje}
    requests.post(url, data=data)
