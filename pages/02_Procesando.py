import os

import streamlit as st
from utils.branding import mostrar_logo
from utils.db import get_conn

mostrar_logo()
st.title("Procesando Albaranes")

password = st.text_input("Contraseña", type="password")

if password != "ju@n":
    st.error("Contraseña incorrecta")
    st.stop()

conn = get_conn()
cur = conn.cursor()
MAX_ALBARANES_PROCESANDO = 20

cur.execute("SELECT * FROM albaranes WHERE estado='entrada'")
pendientes = cur.fetchall()
cur.execute("SELECT COUNT(*) FROM albaranes WHERE estado='procesando'")
albaranes_en_proceso = cur.fetchone()[0]

st.subheader("Albaranes pendientes")
st.caption(f"Albaranes en procesando: {albaranes_en_proceso}/{MAX_ALBARANES_PROCESANDO}")

if albaranes_en_proceso >= MAX_ALBARANES_PROCESANDO:
    st.warning("Se ha alcanzado el máximo de 20 albaranes en procesando. Finaliza alguno antes de añadir otro.")

for albaran in pendientes:
    id_, nombre, empresa, solicitado_por, materiales, comentario, envio_recogida, estado, _msg_final, fecha, foto_preparacion, numero_serie = albaran

    with st.expander(f"Albarán #{id_} - {nombre}"):
        st.write(f"Empresa: {empresa}")
        st.write(f"Solicitado por: {solicitado_por}")
        st.write(f"Materiales:\n{materiales}")
        st.write(f"Comentario: {comentario}")
        st.write(f"Entrega: {envio_recogida}")

        st.subheader("Observaciones internas")
        nuevas_obs = st.text_area("Añadir observaciones", value=obs, key=f"observaciones_{id_}")

        st.subheader("Lectura de código de barras")
        codigo = st.text_input("Escanea el código aquí (lector Zebra)", key=f"codigo_{id_}")
        st.write(f"Código leído: {codigo or numero_serie or 'Pendiente'}")

        imagen = st.camera_input("O usa la cámara de la Zebra", key=f"imagen_{id_}")

        if st.button(f"Marcar como procesado #{id_}", key=f"procesar_{id_}"):
            if albaranes_en_proceso >= MAX_ALBARANES_PROCESANDO:
                st.error("No puedes tener más de 20 albaranes en procesando a la vez.")
                continue
            if imagen is None:
                st.error("Debes sacar una foto de la preparación antes de marcar el albarán como procesado.")
                continue

            ruta_foto = os.path.join("data", f"albaran_{id_}_preparacion.jpg")
            ruta_foto_completa = os.path.join(os.path.dirname(os.path.dirname(__file__)), ruta_foto)
            with open(ruta_foto_completa, "wb") as archivo_foto:
                archivo_foto.write(imagen.getvalue())

            cur.execute("""
                UPDATE albaranes SET estado='procesando', observaciones=?, foto_preparacion=?, numero_serie=?
                WHERE id=?
            """, (nuevas_obs, ruta_foto, codigo.strip(), id_))
            conn.commit()
            st.success("Albarán actualizado")
