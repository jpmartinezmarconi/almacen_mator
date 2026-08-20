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

conn_materiales = get_conn()
filas_materiales = conn_materiales.execute("SELECT materiales FROM albaranes").fetchall()
conn_materiales.close()

catalogo_materiales = sorted({
    linea.rsplit(" - ", 1)[0].strip()
    for (materiales_guardados,) in filas_materiales
    for linea in (materiales_guardados or "").splitlines()
    if linea.strip()
})

num_lineas = st.number_input("Número de líneas", min_value=1, value=1)

for i in range(num_lineas):
    usar_material_manual = st.checkbox("Escribir material nuevo", key=f"usar_material_manual_{i}")
    if usar_material_manual:
        mat = st.text_input(
            f"Material {i+1}",
            key=f"material_manual_{i}",
        )
    else:
        material_seleccionado = st.selectbox(
            f"Material {i+1}",
            catalogo_materiales,
            index=None,
            placeholder="Escribe para buscar un material existente",
            key=f"seleccion_material_{i}",
        )
        mat = material_seleccionado or ""
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

    enviar_telegram("Tienes un nuevo albarán")

    st.success("Albarán enviado correctamente")
    st.info(f"Excel generado en: {ruta_excel}")
