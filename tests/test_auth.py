import ast
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from utils.auth import get_password


class PasswordConfigurationTest(unittest.TestCase):
    def test_get_password_returns_configured_environment_value(self):
        with patch.dict(os.environ, {"ALMACEN_VIRTUAL_PASSWORD": "configured-value"}):
            self.assertEqual(get_password("ALMACEN_VIRTUAL_PASSWORD"), "configured-value")

    def test_get_password_returns_none_when_unconfigured(self):
        with patch.dict(os.environ):
            os.environ.pop("ALMACEN_VIRTUAL_PASSWORD", None)
            self.assertIsNone(get_password("ALMACEN_VIRTUAL_PASSWORD"))


class VirtualWarehouseLoginTest(unittest.TestCase):
    class StopPage(Exception):
        pass

    class SessionState(dict):
        def __setattr__(self, name, value):
            self[name] = value

    def run_login(self, variables, password):
        path = Path(__file__).resolve().parents[1] / "pages" / "07_Almacen.py"
        module = ast.parse(path.read_text(encoding="utf-8"))
        login = next(node for node in module.body if isinstance(node, ast.If))
        code = compile(ast.Module(body=[login], type_ignores=[]), str(path), "exec")
        streamlit = MagicMock()
        streamlit.session_state = self.SessionState()
        streamlit.text_input.return_value = password
        streamlit.stop.side_effect = self.StopPage
        streamlit.rerun.side_effect = self.StopPage
        with patch.dict(os.environ, variables, clear=True):
            with self.assertRaises(self.StopPage):
                exec(code, {"st": streamlit, "get_password": get_password})
        return streamlit

    def test_todas_las_claves_configuradas_autorizan_el_acceso(self):
        variables = {
            "ALMACEN_VIRTUAL_PASSWORD": "primera",
            "ALMACEN_VIRTUAL_PASSWORD_ADICIONAL": "segunda",
            "ALMACEN_VIRTUAL_PASSWORD_TERCERA": "tercera",
            "CEO_PASSWORD": "ceo",
        }
        for password in variables.values():
            with self.subTest(password=password):
                streamlit = self.run_login(variables, password)
                self.assertTrue(streamlit.session_state["almacen_virtual_autorizado"])
                streamlit.rerun.assert_called_once()

    def test_ceo_puede_ser_la_unica_clave_configurada(self):
        streamlit = self.run_login({"CEO_PASSWORD": "ceo"}, "ceo")
        self.assertTrue(streamlit.session_state["almacen_virtual_autorizado"])

    def test_clave_incorrecta_y_configuracion_vacia_no_autorizan(self):
        for variables, password in (({"CEO_PASSWORD": "ceo"}, "incorrecta"), ({}, "ceo")):
            with self.subTest(variables=variables):
                streamlit = self.run_login(variables, password)
                self.assertNotIn("almacen_virtual_autorizado", streamlit.session_state)
                streamlit.error.assert_called_once()
                streamlit.rerun.assert_not_called()


if __name__ == "__main__":
    unittest.main()
