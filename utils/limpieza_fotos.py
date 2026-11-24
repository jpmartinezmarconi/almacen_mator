import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone

from utils.db import BASE_DIR, get_conn


_LOG = logging.getLogger(__name__)
_LOCK = threading.Lock()
_THREAD = None
RETENCION_FOTOS = timedelta(days=7)
INTERVALO_LIMPIEZA_SEGUNDOS = 60


def limpiar_fotos_vencidas(ahora=None):
    ahora = ahora or datetime.now(timezone.utc)
    if ahora.tzinfo is None:
        raise ValueError("La fecha de limpieza debe incluir zona horaria.")
    limite = ahora - RETENCION_FOTOS
    conn = get_conn()
    try:
        fotos = conn.execute(
            "SELECT id, foto_preparacion, procesado_en FROM albaranes "
            "WHERE foto_preparacion IS NOT NULL AND foto_preparacion <> ''"
        ).fetchall()
        eliminadas = 0
        for albaran_id, ruta, procesado_en in fotos:
            esperada = os.path.join("data", f"albaran_{albaran_id}_preparacion.jpg")
            if os.path.normpath(ruta) != esperada:
                _LOG.error("Ruta de foto inesperada para el albaran %s: %s", albaran_id, ruta)
                continue
            archivo = os.path.join(BASE_DIR, esperada)
            try:
                modificacion = os.stat(archivo, follow_symlinks=False).st_mtime
            except FileNotFoundError:
                modificacion = None

            if procesado_en:
                try:
                    fecha_foto = datetime.fromisoformat(procesado_en)
                    if fecha_foto.tzinfo is None:
                        raise ValueError("fecha sin zona horaria")
                except ValueError:
                    _LOG.error("Fecha de foto invalida para el albaran %s: %s", albaran_id, procesado_en)
                    continue
            elif modificacion is not None:
                fecha_foto = datetime.fromtimestamp(modificacion, timezone.utc)
            else:
                fecha_foto = None

            if fecha_foto is not None and fecha_foto > limite:
                continue

            resultado = conn.execute(
                "UPDATE albaranes SET foto_preparacion=NULL "
                "WHERE id=? AND foto_preparacion=? "
                "AND (procesado_en=? OR (procesado_en IS NULL AND ? IS NULL))",
                (albaran_id, ruta, procesado_en, procesado_en),
            )
            if resultado.rowcount != 1:
                conn.rollback()
                continue
            try:
                os.unlink(archivo)
            except FileNotFoundError:
                pass
            except OSError:
                conn.rollback()
                _LOG.exception("No se pudo borrar la foto del albaran %s.", albaran_id)
                continue
            conn.commit()
            eliminadas += 1
        return eliminadas
    finally:
        conn.close()


def _ejecutar_limpieza():
    while True:
        try:
            eliminadas = limpiar_fotos_vencidas()
            if eliminadas:
                _LOG.info("Se eliminaron %s fotos de preparacion vencidas.", eliminadas)
        except Exception:
            _LOG.exception("Error al eliminar fotos de preparacion vencidas.")
        time.sleep(INTERVALO_LIMPIEZA_SEGUNDOS)


def iniciar_limpieza_automatica():
    global _THREAD
    with _LOCK:
        if _THREAD and _THREAD.is_alive():
            return
        _THREAD = threading.Thread(
            target=_ejecutar_limpieza,
            name="limpieza-fotos-albaranes",
            daemon=True,
        )
        _THREAD.start()
