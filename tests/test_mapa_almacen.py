import os
import unittest

from utils.mapa_almacen import PALETA_MAPA, color_seccion, crear_html_mapa


class MapaAlmacenTest(unittest.TestCase):
    def setUp(self):
        self.ruta_mapa = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "assets",
            "mapa_nave1.xlsx",
        )

    def test_colores_del_mapa_coinciden_por_familia_y_por_stock(self):
        self.assertEqual(color_seccion("A1"), PALETA_MAPA["ak"])
        self.assertEqual(color_seccion("Z11"), PALETA_MAPA["z"])
        self.assertEqual(color_seccion("S7"), PALETA_MAPA["s1"])
        self.assertEqual(color_seccion("SP 2"), PALETA_MAPA["sp"])
        self.assertEqual(color_seccion("EST A"), PALETA_MAPA["est"])
        self.assertEqual(color_seccion("S17"), PALETA_MAPA["s8"])
        self.assertEqual(color_seccion("S31"), PALETA_MAPA["s18"])
        self.assertEqual(color_seccion("ELE 3"), PALETA_MAPA["ele"])
        self.assertEqual(color_seccion("STOCK 8"), PALETA_MAPA["stock8"])

    def test_mapa_muestra_ocupacion_con_slots_libres_y_detalle_de_materiales(self):
        secciones = [(1, "S18", "", 1, 1, 2.5, 1.2, 1.2, 8, 1)]
        ubicaciones = {
            1: [(10, "S18-R01-C01", 1, 1, 8, 2.5, 1.2, 1.2, 1, 6)]
        }
        stock = [
            (10, "S18-R01-C01", "S18", "Material A", "SKU-A", 6, 20, 0, 1)
        ]

        contenido, sin_mapa = crear_html_mapa(
            self.ruta_mapa, secciones, ubicaciones, stock
        )

        self.assertEqual(sin_mapa, [])
        self.assertIn("6 / 8 palets (75.0%)", contenido)
        self.assertIn("Material A (SKU-A): 6 palets", contenido)
        self.assertIn("href=\"#detail-s18\"", contenido)
        self.assertEqual(contenido.count('class="slot"'), 8)
        self.assertEqual(contenido.count('pointer-events="none"'), 6)

    def test_ubicaciones_libres_y_secciones_sin_correspondencia_se_indican(self):
        secciones = [
            (1, "S18", "", 1, 1, 2.5, 1.2, 1.2, 8, 1),
            (2, "Zona sin plano", "", 1, 1, 2.5, 1.2, 1.2, 2, 1),
        ]
        ubicaciones = {
            1: [(10, "S18-R01-C01", 1, 1, 8, 2.5, 1.2, 1.2, 1, 0)],
            2: [(20, "ZONA-R01-C01", 1, 1, 2, 2.5, 1.2, 1.2, 1, 0)],
        }

        contenido, sin_mapa = crear_html_mapa(
            self.ruta_mapa, secciones, ubicaciones, []
        )

        self.assertEqual(sin_mapa, ["Zona sin plano"])
        self.assertIn("0 / 8 palets (0.0%)", contenido)
        self.assertIn("Sin materiales registrados.", contenido)
        self.assertEqual(contenido.count('class="slot"'), 8)
        self.assertEqual(contenido.count('pointer-events="none"'), 0)


if __name__ == "__main__":
    unittest.main()
