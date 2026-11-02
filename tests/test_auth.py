import os
import unittest
from unittest.mock import patch

from utils.auth import get_password


class PasswordConfigurationTest(unittest.TestCase):
    def test_get_password_returns_configured_environment_value(self):
        with patch.dict(os.environ, {"ALMACEN_VIRTUAL_PASSWORD": "configured-value"}):
            self.assertEqual(get_password("ALMACEN_VIRTUAL_PASSWORD"), "configured-value")

    def test_get_password_returns_none_when_unconfigured(self):
        with patch.dict(os.environ):
            os.environ.pop("ALMACEN_VIRTUAL_PASSWORD", None)
            self.assertIsNone(get_password("ALMACEN_VIRTUAL_PASSWORD"))


if __name__ == "__main__":
    unittest.main()
