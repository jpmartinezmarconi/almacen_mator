import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from utils.db import get_conn


_LOG = logging.getLogger(__name__)
_SCHEDULER_LOCK = threading.Lock()
_SCHEDULER_THREAD = None
FINALIZACION_AUTOMATICA_HORAS = 24
INTERVALO_FINALIZACION_SEGUNDOS = 60


def finalizar_albaranes_vencidos(ahora=None):
    ahora = ahora or datetime.now(timezone.utc)
    if ahora.tzinfo is None:
        ahora = ahora.replace(tzinfo=timezone.utc)
    fecha_limite = (ahora - timedelta(hours=FINALIZACION_AUTOMATICA_HORAS)).isoformat(
        timespec="seconds"
    )

    conn = get_conn()
    try:
        vencidos = conn.execute(
            "SELECT id, fecha, nombre, empresa, solicitado_por, materiales "
            "FROM albaranes WHERE estado='procesando' AND procesado_en<=? "
            "ORDER BY id",
            (fecha_limite,),
        ).fetchall()

        finalizados = 0
        for albaran_id, fecha, nombre, empresa, solicitado_por, materiales in vencidos:
            actualizacion = conn.execute(
                "UPDATE albaranes SET estado='finalizado' "
                "WHERE id=? AND estado='procesando' AND procesado_en<=?",
                (albaran_id, fecha_limite),
            )
            if actualizacion.rowcount != 1:
                continue

            for linea in (materiales or "").splitlines():
                linea = linea.strip()
                if not linea:
                    continue

                material = linea
                unidades = ""
                if " - " in linea:
                    material, unidades_texto = linea.rsplit(" - ", 1)
                    unidades = unidades_texto.replace("unidades", "").strip()

                conn.execute(
                    "INSERT INTO albaranes_finalizados "
                    "(albaran_id, fecha, nombre, empresa, solicitado_por, material, unidades) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT (albaran_id, material, unidades) DO NOTHING",
                    (
                        albaran_id,
                        fecha,
                        nombre,
                        empresa,
                        solicitado_por,
                        material,
                        unidades,
                    ),
                )
            finalizados += 1

        conn.commit()
        return finalizados
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ejecutar_finalizador():
    while True:
        try:
            finalizados = finalizar_albaranes_vencidos()
            if finalizados:
                _LOG.info("Se finalizaron automaticamente %s albaranes vencidos.", finalizados)
        except Exception:
            _LOG.exception("Error al finalizar automaticamente los albaranes vencidos.")
        time.sleep(INTERVALO_FINALIZACION_SEGUNDOS)


def iniciar_finalizador_automatico():
    global _SCHEDULER_THREAD

    with _SCHEDULER_LOCK:
        if _SCHEDULER_THREAD and _SCHEDULER_THREAD.is_alive():
            return
        _SCHEDULER_THREAD = threading.Thread(
            target=_ejecutar_finalizador,
            name="finalizador-automatico-albaranes",
            daemon=True,
        )
        _SCHEDULER_THREAD.start()
