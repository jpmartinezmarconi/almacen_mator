import os
from datetime import date

import streamlit as st

from utils.branding import mostrar_logo
from utils.db import get_conn
from utils.reparaciones import save_upload

mostrar_logo()
st.title("Reparaciones")
st.caption("Registra equipos, adjunta evidencias y controla su estado.")

with st.form("nueva_reparacion"):
    fecha_entrada = st.date_input("Fecha de entrada", value=date.today())
    empresa = st.text_input("Empresa que lo envia")
    reparacion = st.text_area("Reparacion que se necesita hacer")
    piezas_pendientes = st.text_area("Piezas pendientes", placeholder="Indica las piezas que faltan")

    st.subheader("Presupuesto")
    presupuesto_password = st.text_input("Contraseña para aceptar el presupuesto", type="password")
    presupuesto_monto = st.number_input("Monto del presupuesto", min_value=0.0, step=0.01, format="%.2f")
    presupuesto_archivo = st.file_uploader(
        "Presupuesto en Excel o Word",
        type=["xlsx", "xls", "docx", "doc"],
    )
    fotos = st.file_uploader(
        "Fotos de la reparacion",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
    )
    enviar = st.form_submit_button("Guardar reparacion")

if enviar:
    if not empresa.strip() or not reparacion.strip():
        st.error("Empresa y reparacion son obligatorios.")
    elif presupuesto_archivo is None and presupuesto_monto <= 0:
        st.error("Introduce un monto o adjunta un presupuesto.")
    elif presupuesto_password != "dotr@s":
        st.error("La contraseña del presupuesto es incorrecta.")
    else:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO reparaciones
            (fecha_entrada, empresa, reparacion, piezas_pendientes,
             presupuesto_monto, presupuesto_archivo, estado, fotos,
             fecha_finalizacion, presupuesto_estado)
            VALUES (?, ?, ?, ?, ?, ?, 'en reparacion', '', NULL, 'aceptado')""",
            (fecha_entrada.isoformat(), empresa.strip(), reparacion.strip(),
             piezas_pendientes.strip(), presupuesto_monto or None, ""),
        )
        repair_id = cursor.lastrowid
        budget_path = save_upload(presupuesto_archivo, repair_id, "presupuesto")
        photo_paths = [save_upload(photo, repair_id, "fotos") for photo in fotos]
        cursor.execute(
            "UPDATE reparaciones SET presupuesto_archivo=?, fotos=? WHERE id=?",
            (budget_path, "\n".join(photo_paths), repair_id),
        )
        conn.commit()
        conn.close()
        st.success(f"Reparacion #{repair_id} guardada y presupuesto aceptado.")
        st.rerun()

conn = get_conn()
records = conn.execute(
    """SELECT id, fecha_entrada, empresa, reparacion, piezas_pendientes,
       presupuesto_monto, presupuesto_archivo, presupuesto_estado, estado,
       fotos, fecha_finalizacion
       FROM reparaciones WHERE estado != 'finalizado'
       ORDER BY fecha_entrada DESC, id DESC"""
).fetchall()

st.header("Reparaciones en curso")
if not records:
    st.info("No hay reparaciones en curso.")
else:
    for record in records:
        (repair_id, fecha, empresa, trabajo, piezas, monto, budget_path,
         budget_status, status, photo_paths, finished_at) = record
        with st.expander(f"#{repair_id} - {empresa} [{status}]"):
            st.write(f"Fecha de entrada: {fecha}")
            st.write(f"Reparacion: {trabajo}")
            st.write(f"Piezas pendientes: {piezas or 'Ninguna indicada'}")
            st.write(f"Presupuesto: {monto if monto is not None else 'Adjunto'} ({budget_status})")
            if budget_path:
                full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), budget_path)
                if os.path.isfile(full_path):
                    with open(full_path, "rb") as budget_file:
                        st.download_button("Descargar presupuesto", budget_file.read(), os.path.basename(full_path), key=f"budget_{repair_id}")
            for photo_path in (photo_paths or "").splitlines():
                full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), photo_path)
                if os.path.isfile(full_path):
                    st.image(full_path, width=240)
            if st.button(f"Marcar como finalizado #{repair_id}", key=f"finish_repair_{repair_id}"):
                conn.execute(
                    "UPDATE reparaciones SET estado='finalizado', fecha_finalizacion=? WHERE id=?",
                    (date.today().isoformat(), repair_id),
                )
                conn.commit()
                st.success("Reparacion finalizada.")
                st.rerun()

conn.close()
