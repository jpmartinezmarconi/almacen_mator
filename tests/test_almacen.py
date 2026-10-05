import os
import sqlite3
import tempfile
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from utils.almacen import (
    analizar_materiales_albaran,
    buscar_stock_materiales,
    obtener_ubicaciones_materiales,
    procesar_albaran,
)


@contextmanager
def conectar_db(ruta):
    conn = sqlite3.connect(ruta)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


class ProcesarAlbaranPrioridadNaveTest(unittest.TestCase):
    def setUp(self):
        self.directorio = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.directorio.name, "almacen.db")
        self._crear_esquema()
        self.get_conn_patch = patch(
            "utils.almacen.get_conn",
            side_effect=lambda: sqlite3.connect(self.db_path),
        )
        self.get_conn_patch.start()

    def tearDown(self):
        self.get_conn_patch.stop()
        self.directorio.cleanup()

    def _crear_esquema(self):
        with conectar_db(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE almacenes (id INTEGER PRIMARY KEY, nombre TEXT);
                CREATE TABLE almacen_secciones (
                    id INTEGER PRIMARY KEY,
                    almacen_id INTEGER,
                    nombre TEXT,
                    activa INTEGER
                );
                CREATE TABLE almacen_ubicaciones (
                    id INTEGER PRIMARY KEY,
                    seccion_id INTEGER,
                    codigo TEXT,
                    activa INTEGER
                );
                CREATE TABLE almacen_stock (
                    id INTEGER PRIMARY KEY,
                    ubicacion_id INTEGER,
                    material TEXT,
                    codigo_material TEXT,
                    palets INTEGER,
                    unidades_por_palet INTEGER,
                    unidades_sueltas INTEGER,
                    actualizado TEXT
                );
                CREATE TABLE almacen_movimientos (
                    id INTEGER PRIMARY KEY,
                    fecha TEXT,
                    tipo TEXT,
                    ubicacion_id INTEGER,
                    material TEXT,
                    codigo_material TEXT,
                    palets INTEGER,
                    unidades_por_palet INTEGER,
                    unidades_sueltas INTEGER,
                    referencia TEXT,
                    albaran_id INTEGER
                );
                CREATE TABLE albaranes (
                    id INTEGER PRIMARY KEY,
                    materiales TEXT,
                    estado TEXT,
                    observaciones TEXT,
                    foto_preparacion TEXT,
                    numero_serie TEXT,
                    procesado_en TEXT
                );
            """)
            conn.executemany(
                "INSERT INTO almacenes (id, nombre) VALUES (?, ?)",
                [(1, "Nave 2"), (2, "Nave 1")],
            )
            conn.executemany(
                "INSERT INTO almacen_secciones (id, almacen_id, nombre, activa) "
                "VALUES (?, ?, ?, 1)",
                [(1, 1, "Sección N2"), (2, 2, "Sección N1")],
            )
            conn.executemany(
                "INSERT INTO almacen_ubicaciones (id, seccion_id, codigo, activa) "
                "VALUES (?, ?, ?, 1)",
                [(1, 1, "N2-A1"), (2, 2, "N1-A1")],
            )
            conn.execute(
                "INSERT INTO albaranes "
                "(id, materiales, estado) VALUES (1, 'Material A - 4 unidades', 'entrada')"
            )

    def _guardar_stock(self, ubicacion_id, unidades, codigo=""):
        with conectar_db(self.db_path) as conn:
            conn.execute(
                "INSERT INTO almacen_stock "
                "(ubicacion_id, material, codigo_material, palets, "
                "unidades_por_palet, unidades_sueltas, actualizado) "
                "VALUES (?, 'Material A', ?, 0, 10, ?, '2026-10-05')",
                (ubicacion_id, codigo, unidades),
            )

    def test_descuenta_nave_1_antes_que_nave_2_aunque_tenga_mayor_id(self):
        self._guardar_stock(1, 5)
        self._guardar_stock(2, 3)

        ubicaciones = obtener_ubicaciones_materiales(["Material A"])[
            ("material a", "")
        ]
        resultado = procesar_albaran(1, "", "", "")

        self.assertEqual([fila["nave"] for fila in ubicaciones], ["Nave 1", "Nave 2"])
        self.assertEqual(
            [(fila["nave"], fila["unidades"]) for fila in resultado["descuentos"]],
            [("Nave 1", 3), ("Nave 2", 1)],
        )
        with conectar_db(self.db_path) as conn:
            stock_restante = conn.execute(
                "SELECT a.nombre, s.unidades_sueltas "
                "FROM almacen_stock s "
                "JOIN almacen_ubicaciones u ON u.id=s.ubicacion_id "
                "JOIN almacen_secciones sec ON sec.id=u.seccion_id "
                "JOIN almacenes a ON a.id=sec.almacen_id "
                "ORDER BY a.id"
            ).fetchall()
        self.assertEqual(stock_restante, [("Nave 2", 4)])

    def test_descuenta_de_nave_2_si_es_donde_unicamente_hay_stock(self):
        self._guardar_stock(1, 5)

        resultado = procesar_albaran(1, "", "", "")

        self.assertEqual(
            [(fila["nave"], fila["unidades"]) for fila in resultado["descuentos"]],
            [("Nave 2", 4)],
        )
        self.assertEqual(resultado["faltantes"], [])

    def test_busca_y_descuenta_por_codigo_de_material(self):
        self._guardar_stock(2, 7, "SKU-A")
        self._guardar_stock(2, 9, "SKU-B")
        with conectar_db(self.db_path) as conn:
            conn.execute(
                "UPDATE albaranes SET materiales=? WHERE id=1",
                ("Material A [Codigo: SKU-B] - 4 unidades",),
            )

        pedido = analizar_materiales_albaran(
            "Material A [Codigo: SKU-B] - 4 unidades"
        )
        ubicaciones = obtener_ubicaciones_materiales(pedido)
        resultado = procesar_albaran(1, "", "", "")

        self.assertEqual(pedido[0]["codigo_material"], "SKU-B")
        self.assertEqual(
            [fila["codigo_material"] for fila in ubicaciones[("material a", "sku-b")]],
            ["SKU-B"],
        )
        self.assertEqual(
            [(fila["nave"], fila["unidades"]) for fila in resultado["descuentos"]],
            [("Nave 1", 4)],
        )
        with conectar_db(self.db_path) as conn:
            cantidades = conn.execute(
                "SELECT codigo_material, unidades_sueltas FROM almacen_stock "
                "ORDER BY codigo_material"
            ).fetchall()
        self.assertEqual(cantidades, [("SKU-A", 7), ("SKU-B", 5)])

    def test_busqueda_global_encuentra_fragmentos_de_nombre_y_codigo(self):
        self._guardar_stock(2, 7, "SKU-ABC-123")

        resultados_nombre = buscar_stock_materiales("terial a")
        resultados_codigo = buscar_stock_materiales("abc-12")

        self.assertEqual(len(resultados_nombre), 1)
        self.assertEqual(len(resultados_codigo), 1)
        self.assertEqual(resultados_codigo[0][4], "SKU-ABC-123")
        self.assertEqual(resultados_codigo[0][1], "Sección N1")
        self.assertEqual(resultados_codigo[0][5] * resultados_codigo[0][6] + resultados_codigo[0][7], 7)


if __name__ == "__main__":
    unittest.main()
