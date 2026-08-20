import sqlite3

def get_conn():
    return sqlite3.connect("data/albaranes.db", check_same_thread=False)

def init_db():
    conn = get_conn()
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

    conn.commit()
    conn.close()
