import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from utils.db import get_conn
from utils.espacio_palets import (
    limpiar_espacio_palets,
    mostrar_espacio_palets,
    resumir_ocupacion_por_seccion,
)


class EspacioPaletsTest(unittest.TestCase):
    def test_acepta_palets_completos_y_quintos(self):
        self.assertEqual(limpiar_espacio_palets("Palet completo"), 1.0)
        self.assertEqual(limpiar_espacio_palets("1/5 de palet"), 0.2)
        self.assertEqual(limpiar_espacio_palets("0,2"), 0.2)
        self.assertEqual(limpiar_espacio_palets(None), 1.0)
        self.assertEqual(mostrar_espacio_palets(0.2), "1/5 de palet")
        self.assertEqual(mostrar_espacio_palets(1.0), "Palet completo")

    def test_rechaza_fracciones_no_admitidas(self):
        with self.assertRaises(ValueError):
            limpiar_espacio_palets("1/2")

    def test_resumen_separa_materiales_y_suma_ocupacion_por_area(self):
        equipos = pd.DataFrame(
            [
                {"nombre": "Material A", "cantidad": 2, "espacio_palets": 0.2, "seccion": "Zona 1"},
                {"nombre": "Material A", "cantidad": 1, "espacio_palets": 1.0, "seccion": "Zona 1"},
                {"nombre": "Material B", "cantidad": 3, "espacio_palets": 0.2, "seccion": "Zona 1"},
                {"nombre": "Material B", "cantidad": 1, "espacio_palets": 1.0, "seccion": "Zona 2"},
            ]
        )

        resumen = resumir_ocupacion_por_seccion(equipos)
        ocupacion = {
            (fila["Sección"], fila["Material"]): fila["Espacio ocupado (palets)"]
            for _, fila in resumen.iterrows()
        }

        self.assertEqual(ocupacion, {
            ("Zona 1", "Material A"): 1.4,
            ("Zona 1", "Material B"): 0.6,
            ("Zona 2", "Material B"): 1.0,
        })
        self.assertEqual(resumen["Material"].nunique(), 2)

    def test_database_migration_preserves_existing_equipment(self):
        with tempfile.TemporaryDirectory() as directorio:
            ruta_db = os.path.join(directorio, "almacen.db")
            conn = sqlite3.connect(ruta_db)
            conn.execute("""
                CREATE TABLE equipos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    cantidad INTEGER NOT NULL,
                    numero_serie TEXT NOT NULL,
                    seccion TEXT NOT NULL,
                    fecha_alta TEXT NOT NULL
                )
            """)
            conn.execute(
                "INSERT INTO equipos (nombre, cantidad, numero_serie, seccion, fecha_alta) "
                "VALUES (?, ?, ?, ?, ?)",
                ("Artículo existente", 1, "serie-1", "Zona A", "2026-10-02"),
            )
            conn.commit()
            conn.close()

            with patch("utils.db.DB_PATH", ruta_db):
                conn = get_conn()
                fila = conn.execute(
                    "SELECT nombre, espacio_palets FROM equipos WHERE id = 1"
                ).fetchone()
                conn.close()

        self.assertEqual(fila, ("Artículo existente", 1.0))


if __name__ == "__main__":
    unittest.main()
