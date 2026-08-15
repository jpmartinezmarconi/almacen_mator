import os
import logging
import requests

logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_telegram(mensaje):
    if not TOKEN or not CHAT_ID:
        logger.error(
            "TELEGRAM_TOKEN o TELEGRAM_CHAT_ID no están configurados como variables de entorno"
        )
        print("TELEGRAM_TOKEN o TELEGRAM_CHAT_ID no están configurados como variables de entorno")
        return
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": mensaje}
    logger.info(
        "Enviando mensaje de Telegram (token[:10]=%s, chat_id=%s)",
        TOKEN[:10],
        CHAT_ID,
    )
    try:
        response = requests.post(url, data=data)
        logger.info(
            "Respuesta de Telegram: status_code=%s, text=%s",
            response.status_code,
            response.text,
        )
    except Exception:
        logger.exception("Error al enviar el mensaje de Telegram")
