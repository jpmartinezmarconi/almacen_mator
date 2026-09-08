import logging
import os
import json

import requests

logger = logging.getLogger(__name__)


def enviar_telegram(mensaje):
    token = (os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.getenv("TELEGRAM_CHAT_ID") or "").strip()

    if not token or not chat_id:
        logger.error(
            "TELEGRAM_TOKEN o TELEGRAM_CHAT_ID no están configurados como variables de entorno"
        )
        print("TELEGRAM_TOKEN o TELEGRAM_CHAT_ID no están configurados como variables de entorno")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = {"chat_id": chat_id, "text": mensaje}
    try:
        response = requests.post(url, data=data, timeout=15)
        response.raise_for_status()
        try:
            resultado = json.loads(response.text)
        except (TypeError, ValueError):
            resultado = {"ok": response.ok, "description": "Respuesta no JSON"}

        if not resultado.get("ok", False):
            logger.error(
                "Telegram rechazo el mensaje: %s",
                resultado.get("description", "respuesta desconocida"),
            )
            return False

        logger.info(
            "Respuesta de Telegram: status_code=%s, text=%s",
            response.status_code,
            response.text,
        )
        return True
    except requests.RequestException as error:
        logger.error("Error al enviar el mensaje de Telegram: %s", error)
        return False
