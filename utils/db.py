import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "albaranes.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)

    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS albaranes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            empresa TEXT,
            solicitado_por TEXT,
            materiales TEXT,
            comentario TEXT,
            envio_recogida TEXT,
            estado TEXT,
            observaciones TEXT,
            mensaje_final TEXT,
            fecha TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS equipos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            numero_serie TEXT NOT NULL,
            seccion TEXT NOT NULL,
            fecha_alta TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS reparaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_entrada TEXT NOT NULL,
            empresa TEXT NOT NULL,
            reparacion TEXT NOT NULL,
            piezas_pendientes TEXT,
            presupuesto_monto REAL,
            presupuesto_archivo TEXT,
            estado TEXT NOT NULL DEFAULT 'en reparacion',
            fotos TEXT,
            fecha_finalizacion TEXT
        )
    """)

    repair_columns = {
        row[1] for row in cur.execute("PRAGMA table_info(reparaciones)").fetchall()
    }
    if "presupuesto_estado" not in repair_columns:
        cur.execute(
            "ALTER TABLE reparaciones ADD COLUMN presupuesto_estado TEXT DEFAULT 'pendiente'"
        )

    conn.commit()
    return conn


def init_db():
    conn = get_conn()
    conn.close()
