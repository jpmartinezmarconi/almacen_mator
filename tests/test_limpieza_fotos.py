import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from utils.limpieza_fotos import limpiar_fotos_vencidas


class LimpiezaFotosTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.data = os.path.join(self.tmp.name, "data")
        os.mkdir(self.data)
        self.db = os.path.join(self.tmp.name, "test.db")
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute(
                "CREATE TABLE albaranes (id INTEGER PRIMARY KEY, foto_preparacion TEXT, "
                "procesado_en TEXT, estado TEXT, materiales TEXT)"
            )
        self.ahora = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
        self.base_patch = patch("utils.limpieza_fotos.BASE_DIR", self.tmp.name)
        self.conn_patch = patch(
            "utils.limpieza_fotos.get_conn", side_effect=lambda: sqlite3.connect(self.db)
        )
        self.base_patch.start()
        self.conn_patch.start()
        self.addCleanup(self.base_patch.stop)
        self.addCleanup(self.conn_patch.stop)

    def crear_albaran(self, id_, fecha, estado="finalizado", crear_foto=True):
        ruta = os.path.join("data", f"albaran_{id_}_preparacion.jpg")
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute(
                "INSERT INTO albaranes VALUES (?, ?, ?, ?, ?)",
                (id_, ruta, fecha, estado, "Material original"),
            )
        archivo = os.path.join(self.tmp.name, ruta)
        if crear_foto:
            with open(archivo, "wb") as foto:
                foto.write(b"foto")
        return archivo

    def test_elimina_al_cumplir_siete_dias_sin_borrar_datos(self):
        antigua = self.crear_albaran(1, (self.ahora - timedelta(days=7)).isoformat())
        reciente = self.crear_albaran(
            2, (self.ahora - timedelta(days=7) + timedelta(seconds=1)).isoformat(),
            estado="procesando",
        )
        en_proceso = self.crear_albaran(
            3, (self.ahora - timedelta(days=8)).isoformat(), estado="procesando"
        )
        self.assertEqual(limpiar_fotos_vencidas(self.ahora), 2)
        self.assertFalse(os.path.exists(antigua))
        self.assertTrue(os.path.exists(reciente))
        self.assertFalse(os.path.exists(en_proceso))
        with closing(sqlite3.connect(self.db)) as conn, conn:
            filas = conn.execute(
                "SELECT id, foto_preparacion, estado, materiales FROM albaranes ORDER BY id"
            ).fetchall()
        self.assertEqual(filas[0], (1, None, "finalizado", "Material original"))
        self.assertIsNotNone(filas[1][1])
        self.assertEqual(filas[1][2:], ("procesando", "Material original"))
        self.assertEqual(filas[2], (3, None, "procesando", "Material original"))
        self.assertEqual(limpiar_fotos_vencidas(self.ahora), 0)

    def test_fotos_sin_fecha_usan_fecha_archivo_y_admiten_archivo_ausente(self):
        antigua = self.crear_albaran(1, None)
        reciente = self.crear_albaran(2, None)
        self.crear_albaran(3, None, crear_foto=False)
        os.utime(antigua, ((self.ahora - timedelta(days=8)).timestamp(),) * 2)
        os.utime(reciente, (self.ahora.timestamp(),) * 2)
        self.assertEqual(limpiar_fotos_vencidas(self.ahora), 2)
        self.assertFalse(os.path.exists(antigua))
        self.assertTrue(os.path.exists(reciente))
        with closing(sqlite3.connect(self.db)) as conn, conn:
            self.assertEqual(
                conn.execute("SELECT id FROM albaranes WHERE foto_preparacion IS NOT NULL").fetchall(),
                [(2,)],
            )

    def test_no_borra_rutas_inesperadas_y_fechas_invalidas(self):
        archivo = self.crear_albaran(1, "fecha incorrecta")
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute(
                "INSERT INTO albaranes VALUES (2, ?, NULL, 'finalizado', 'datos')",
                (os.path.join("data", "..", "otro.jpg"),),
            )
        with self.assertLogs("utils.limpieza_fotos", level="ERROR"):
            self.assertEqual(limpiar_fotos_vencidas(self.ahora), 0)
        self.assertTrue(os.path.exists(archivo))
        with closing(sqlite3.connect(self.db)) as conn, conn:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM albaranes WHERE foto_preparacion IS NOT NULL").fetchone()[0],
                2,
            )

    def test_error_al_borrar_conserva_referencia(self):
        self.crear_albaran(1, (self.ahora - timedelta(days=8)).isoformat())
        archivo2 = self.crear_albaran(2, (self.ahora - timedelta(days=8)).isoformat())
        unlink = os.unlink

        def borrar(archivo):
            if archivo == archivo2:
                return unlink(archivo)
            raise PermissionError("sin permiso")

        with patch("utils.limpieza_fotos.os.unlink", side_effect=borrar):
            with self.assertLogs("utils.limpieza_fotos", level="ERROR"):
                self.assertEqual(limpiar_fotos_vencidas(self.ahora), 1)
        with closing(sqlite3.connect(self.db)) as conn, conn:
            filas = conn.execute(
                "SELECT foto_preparacion FROM albaranes ORDER BY id"
            ).fetchall()
        self.assertIsNotNone(filas[0][0])
        self.assertIsNone(filas[1][0])


if __name__ == "__main__":
    unittest.main()
