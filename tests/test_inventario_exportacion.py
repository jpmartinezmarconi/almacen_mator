import io
import unittest

from openpyxl import load_workbook

from utils.inventario_exportacion import (
    crear_excel_inventario,
    crear_html_impresion_inventario,
    preparar_inventario,
)


class InventarioExportacionTest(unittest.TestCase):
    def setUp(self):
        self.almacenes = [(1, "Nave 1"), (2, "Nave 2")]
        self.stock = {
            1: [
                (1, "A1", "Zona A", "Material A", "001", 2, 10, 3, 1),
                (2, "A2", "Zona A", "Material A", "001", 0, 10, 7, 0),
                (3, "A3", "Zona A", "=1+1", None, 0, 1, 2, 1),
                (4, "A4", "Zona A", "Sin stock", "", 0, 1, 0, 1),
            ],
            2: [
                (5, "B1", "Zona B", "Material A", "001", 1, 12, 0, 2),
                (6, "B2", "Zona B", "Material A", "002", 0, 1, 5, 1),
            ],
        }

    def test_inventario_por_nave_y_total(self):
        resumen_nave, detalle_nave = preparar_inventario(
            self.almacenes[:1], self.stock.__getitem__
        )
        self.assertIn(("Material A", "001", 30), resumen_nave)
        self.assertEqual(len(detalle_nave), 3)
        self.assertEqual(detalle_nave[0][-2:], (1, 3))
        self.assertEqual(detalle_nave[1][-2:], (0, 0))

        resumen, detalle = preparar_inventario(self.almacenes, self.stock.__getitem__)
        self.assertIn(("Material A", "001", 42), resumen)
        self.assertIn(("Material A", "002", 5), resumen)
        self.assertEqual(len(detalle), 5)
        self.assertEqual({fila[0] for fila in detalle}, {"Nave 1", "Nave 2"})
        self.assertEqual(detalle[3][-1], 2)

        resumen_nave_2, detalle_nave_2 = preparar_inventario(
            self.almacenes[1:], self.stock.__getitem__
        )
        self.assertEqual(resumen_nave_2, [("Material A", "001", 12), ("Material A", "002", 5)])
        self.assertTrue(all(fila[0] == "Nave 2" for fila in detalle_nave_2))

    def test_excel_contiene_datos_y_no_interpreta_texto_como_formula(self):
        resumen, detalle = preparar_inventario(self.almacenes, self.stock.__getitem__)
        libro = load_workbook(io.BytesIO(crear_excel_inventario("Todas las naves", resumen, detalle)))
        self.assertEqual(libro.sheetnames, ["Resumen", "Detalle"])
        normalizar = lambda filas: [
            tuple("" if valor is None else valor for valor in fila) for fila in filas
        ]
        self.assertEqual(libro["Resumen"]["A1"].value, "Inventario: Todas las naves")
        self.assertEqual(normalizar(list(libro["Resumen"].values)[2:]), resumen)
        self.assertEqual(normalizar(list(libro["Detalle"].values)[2:]), detalle)
        self.assertEqual(libro["Resumen"]["A3"].value, "=1+1")
        self.assertEqual(libro["Resumen"]["A3"].data_type, "s")
        self.assertEqual(libro["Detalle"].print_title_rows, "$1:$2")
        self.assertEqual(libro["Detalle"].page_setup.fitToWidth, 1)

    def test_html_de_impresion_escapa_los_datos(self):
        html = crear_html_impresion_inventario(
            "<Nave>", [("<script>", "&", 5)], []
        )
        self.assertIn("window.print()", html)
        self.assertIn("&lt;Nave&gt;", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>", html)
        self.assertIn("&amp;", html)

    def test_inventario_vacio_genera_excel_y_vista_de_impresion(self):
        resumen, detalle = preparar_inventario([], self.stock.__getitem__)
        self.assertEqual((resumen, detalle), ([], []))
        libro = load_workbook(io.BytesIO(crear_excel_inventario("Vacío", resumen, detalle)))
        self.assertEqual(libro["Detalle"].max_row, 2)
        self.assertIn("Detalle por ubicación", crear_html_impresion_inventario("Vacío", resumen, detalle))


if __name__ == "__main__":
    unittest.main()
