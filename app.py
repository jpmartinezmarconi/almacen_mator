import streamlit as st
from utils.branding import mostrar_logo
from utils.db import init_db

init_db()

st.set_page_config(page_title="Almacén Mator", layout="wide")
mostrar_logo()

st.markdown("""
    <h1 style='text-align: center; color: black; font-family: Arial;'>
        Almacén Mator
    </h1>
""", unsafe_allow_html=True)

st.write("Usa el menú lateral para navegar entre las páginas.")
