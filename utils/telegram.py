import os
import logging
import requests

logger = logging.getLogger(__name__)


def enviar_telegram(mensaje):
    token = os.getenv("TELEGRAM_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.error(
            "TELEGRAM_TOKEN o TELEGRAM_CHAT_ID no están configurados como variables de entorno"
        )
        print("TELEGRAM_TOKEN o TELEGRAM_CHAT_ID no están configurados como variables de entorno")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": mensaje}
    logger.info(
        "Enviando mensaje de Telegram (token[:10]=%s, chat_id=%s)",
        token[:10],
        chat_id,
    )
    try:
        response = requests.post(url, data=data, timeout=15)
        response.raise_for_status()
        logger.info(
            "Respuesta de Telegram: status_code=%s, text=%s",
            response.status_code,
            response.text,
        )
        return response.ok
    except requests.RequestException:
        logger.exception("Error al enviar el mensaje de Telegram")
        return False
