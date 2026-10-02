import importlib
import os
import unittest
from unittest.mock import patch


class TelegramEnvTest(unittest.TestCase):
    def test_enviar_telegram_uses_runtime_environment(self):
        module = importlib.import_module("utils.telegram")
        importlib.reload(module)

        os.environ["TELEGRAM_TOKEN"] = "test-token"
        os.environ["TELEGRAM_CHAT_ID"] = "123456"

        try:
            with patch("requests.post") as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.text = '{"ok": true}'
                result = module.enviar_telegram("Nuevo albarán")

            self.assertTrue(result)
            self.assertEqual(mock_post.call_count, 1)
            self.assertEqual(mock_post.call_args.kwargs["data"]["chat_id"], "123456")
        finally:
            os.environ.pop("TELEGRAM_TOKEN", None)
            os.environ.pop("TELEGRAM_CHAT_ID", None)


if __name__ == "__main__":
    unittest.main()
