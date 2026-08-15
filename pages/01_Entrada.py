import streamlit as st
from utils.db import get_conn
from utils.excel import generar_excel
from utils.telegram import enviar_telegram
import datetime

st.title("Albarán de Entrada")

nombre = st.text_input("Nombre")
empresa = st.text_input("Empresa")
solicitado_por = st.text_input("Solicitado por")

st.subheader("Materiales pedidos")
materiales = []

num_lineas = st.number_input("Número de líneas", min_value=1, value=1)

for i in range(num_lineas):
    mat = st.text_input(f"Material {i+1}")
    uni = st.number_input(f"Unidades {i+1}", min_value=1, value=1)
    materiales.append(f"{mat} - {uni} unidades")

comentario = st.text_area("Comentario opcional")

envio_recogida = st.radio("Tipo de entrega", ["Enviado por nosotros", "Vienen a buscar"])

if st.button("Enviar albarán"):
    conn = get_conn()
    cur = conn.cursor()

    datos = {
        "nombre": nombre,
        "empresa": empresa,
        "solicitado_por": solicitado_por,
        "materiales": "\n".join(materiales),
        "comentario": comentario,
        "envio_recogida": envio_recogida,
        "estado": "entrada",
        "observaciones": "",
        "mensaje_final": "",
        "fecha": str(datetime.date.today())
    }

    cur.execute("""
        INSERT INTO albaranes (nombre, empresa, solicitado_por, materiales, comentario,
        envio_recogida, estado, observaciones, mensaje_final, fecha)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, tuple(datos.values()))

    conn.commit()
    id_albaran = cur.lastrowid

    ruta_excel = generar_excel(datos, id_albaran)

    enviar_telegram(f"Nuevo albarán recibido: {id_albaran}")

    st.success("Albarán enviado correctamente")
    st.info(f"Excel generado en: {ruta_excel}")
