import streamlit as st
from datetime import date

from utils.branding import mostrar_logo
from utils.db import get_conn
from utils.reparaciones import repair_excel, repair_zip

mostrar_logo()
st.title("Averias finalizadas")

conn = get_conn()
empresa_filtro = st.text_input("Filtrar por empresa")
fecha_inicio, fecha_fin = st.date_input(
    "Rango de entrada",
    value=(date(2000, 1, 1), date.today()),
)

query = """SELECT id, fecha_entrada, empresa, reparacion, piezas_pendientes,
    presupuesto_monto, presupuesto_archivo, presupuesto_estado, estado,
    fotos, fecha_finalizacion FROM reparaciones WHERE estado='finalizado'"""
params = []
if empresa_filtro.strip():
    query += " AND empresa LIKE ?"
    params.append(f"%{empresa_filtro.strip()}%")
if fecha_inicio and fecha_fin:
    query += " AND fecha_entrada BETWEEN ? AND ?"
    params.extend([fecha_inicio.isoformat(), fecha_fin.isoformat()])
query += " ORDER BY fecha_finalizacion DESC, id DESC"
records = conn.execute(query, params).fetchall()
conn.close()

st.caption(f"Averias finalizadas encontradas: {len(records)}")
if not records:
    st.info("No hay averias finalizadas con estos filtros.")
    st.stop()

for record in records:
    repair_id, fecha, empresa, trabajo, piezas, monto, budget_path, budget_status, status, photos, finished = record
    with st.expander(f"#{repair_id} - {empresa} ({finished})"):
        st.write(f"Entrada: {fecha}")
        st.write(f"Reparacion: {trabajo}")
        st.write(f"Piezas pendientes: {piezas or 'Ninguna'}")
        st.write(f"Presupuesto: {monto if monto is not None else 'Adjunto'} ({budget_status})")
        st.write(f"Finalizada: {finished}")
        st.download_button(
            "Descargar esta averia",
            repair_excel([record]),
            file_name=f"averia_{repair_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"download_repair_{repair_id}",
        )

ids = [record[0] for record in records]
selected_ids = st.multiselect(
    "Selecciona una o varias averias",
    ids,
    format_func=lambda repair_id: next(
        f"#{row[0]} - {row[2]}" for row in records if row[0] == repair_id
    ),
)
selected_records = [record for record in records if record[0] in selected_ids]
if selected_records:
    st.download_button(
        f"Descargar {len(selected_records)} averias y adjuntos",
        repair_zip(selected_records),
        file_name="averias_seleccionadas.zip",
        mime="application/zip",
        key="download_selected_repairs",
    )

st.download_button(
    "Descargar todas las averias y adjuntos",
    repair_zip(records),
    file_name="averias_finalizadas.zip",
    mime="application/zip",
    key="download_all_repairs",
)