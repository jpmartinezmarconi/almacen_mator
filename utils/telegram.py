import logging
import os
import json

import requests

logger = logging.getLogger(__name__)


def enviar_telegram(mensaje, devolver_error=False):
    token = (os.getenv("TELEGRAM_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_id = (os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHAT_ID") or "").strip()

    if not token or not chat_id:
        faltan = []
        if not token:
            faltan.append("TELEGRAM_BOT_TOKEN o TELEGRAM_TOKEN")
        if not chat_id:
            faltan.append("TELEGRAM_CHAT_ID o CHAT_ID")
        detalle = "Faltan variables de entorno: " + ", ".join(faltan)
        logger.error(
            detalle
        )
        print(detalle)
        resultado = (False, detalle)
        return resultado if devolver_error else resultado[0]

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
            resultado = (False, resultado.get("description", "Telegram rechazo el mensaje"))
            return resultado if devolver_error else resultado[0]

        logger.info(
            "Respuesta de Telegram: status_code=%s, text=%s",
            response.status_code,
            response.text,
        )
        resultado = (True, "Mensaje enviado")
        return resultado if devolver_error else resultado[0]
    except requests.RequestException as error:
        logger.error("Error al enviar el mensaje de Telegram: %s", error)
        resultado = (False, str(error))
        return resultado if devolver_error else resultado[0]
