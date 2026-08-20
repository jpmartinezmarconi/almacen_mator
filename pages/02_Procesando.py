import streamlit as st
from utils.db import get_conn

st.title("Procesando Albaranes")

password = st.text_input("Contraseña", type="password")

if password != "ju@n":
    st.error("Contraseña incorrecta")
    st.stop()

conn = get_conn()
cur = conn.cursor()

cur.execute("SELECT * FROM albaranes WHERE estado='entrada'")
pendientes = cur.fetchall()

st.subheader("Albaranes pendientes")

for albaran in pendientes:
    id_, nombre, empresa, solicitado_por, materiales, comentario, envio_recogida, estado, obs, msg_final, fecha = albaran

    with st.expander(f"Albarán #{id_} - {nombre}"):
        st.write(f"Empresa: {empresa}")
        st.write(f"Solicitado por: {solicitado_por}")
        st.write(f"Materiales:\n{materiales}")
        st.write(f"Comentario: {comentario}")
        st.write(f"Entrega: {envio_recogida}")

        st.subheader("Observaciones internas")
        nuevas_obs = st.text_area("Añadir observaciones", value=obs)

        st.subheader("Mensaje para pantalla Finalizados")
        mensaje_final = st.text_area("Mensaje final", value=msg_final)

        st.subheader("Lectura de código de barras")
        codigo = st.text_input("Escanea el código aquí (lector Zebra)")
        st.write(f"Código leído: {codigo}")

        imagen = st.camera_input("O usa la cámara de la Zebra")

        if st.button(f"Marcar como procesado #{id_}"):
            cur.execute("""
                UPDATE albaranes SET estado='procesando', observaciones=?, mensaje_final=?
                WHERE id=?
            """, (nuevas_obs, mensaje_final, id_))
            conn.commit()
            st.success("Albarán actualizado")
