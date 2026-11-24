import os
import sys

from streamlit.web import cli

from utils.limpieza_fotos import iniciar_limpieza_automatica


if __name__ == "__main__":
    iniciar_limpieza_automatica()
    app = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.py")
    sys.argv = ["streamlit", "run", app, *sys.argv[1:]]
    sys.exit(cli.main())
