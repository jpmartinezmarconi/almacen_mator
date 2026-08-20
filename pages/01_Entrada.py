import streamlit as st
from utils.db import get_conn
from utils.excel import generar_excel
from utils.telegram import enviar_telegram
import datetime

st.title("Albarán de Entrada")

MATERIALES = [
    "Cable", "Conector", "Disyuntor", "Enchufe", "Fusible",
    "Interruptor", "Lámpara", "Magnetotérmico", "Regleta", "Tubo",
]

nombre = st.text_input("Nombre")
empresa = st.text_input("Empresa")
solicitado_por = st.text_input("Solicitado por")

st.subheader("Materiales pedidos")
materiales = []

num_lineas = st.number_input("Número de líneas", min_value=1, value=1)

for i in range(num_lineas):
    busqueda_material = st.text_input(
        f"Buscar material {i+1}",
        key=f"busqueda_material_{i}",
        placeholder="Escribe una o varias letras",
    )
    coincidencias = [
        material
        for material in MATERIALES
        if busqueda_material.strip().lower() in material.lower()
    ]
    opciones = coincidencias + ["Otro material (escribir manualmente)"]
    material_seleccionado = st.selectbox(
        f"Sugerencias para material {i+1}",
        opciones,
        key=f"seleccion_material_{i}",
    )
    if material_seleccionado == "Otro material (escribir manualmente)":
        mat = st.text_input(
            f"Material manual {i+1}",
            value=busqueda_material,
            key=f"material_manual_{i}",
        )
    else:
        mat = material_seleccionado
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
