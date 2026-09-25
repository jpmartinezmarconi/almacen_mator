import re
from datetime import datetime

from utils.db import get_conn


DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def ahora():
    return datetime.now().strftime(DATE_FORMAT)


def listar_secciones(incluir_inactivas=False):
    conn = get_conn()
    try:
        filtro = "" if incluir_inactivas else " WHERE activa = 1"
        return conn.execute(
            "SELECT id, nombre, descripcion, filas, columnas, alto_m, ancho_m, fondo_m, "
            f"capacidad_palets, activa FROM almacen_secciones{filtro} ORDER BY nombre"
        ).fetchall()
    finally:
        conn.close()


def listar_ubicaciones(seccion_id, incluir_inactivas=False):
    conn = get_conn()
    try:
        filtro = "" if incluir_inactivas else " AND u.activa = 1"
        return conn.execute(
            "SELECT u.id, u.codigo, u.fila, u.columna, u.capacidad_palets, u.alto_m, "
            "u.ancho_m, u.fondo_m, u.activa, "
            "COALESCE(SUM(s.palets), 0) AS palets_ocupados "
            "FROM almacen_ubicaciones u LEFT JOIN almacen_stock s ON s.ubicacion_id = u.id "
            "WHERE u.seccion_id = ?" + filtro + " GROUP BY u.id ORDER BY u.fila, u.columna",
            (seccion_id,),
        ).fetchall()
    finally:
        conn.close()


def obtener_detalle_ubicacion(ubicacion_id):
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT s.id, s.material, s.codigo_material, s.palets, s.unidades_por_palet, "
            "s.unidades_sueltas, s.actualizado FROM almacen_stock s "
            "WHERE s.ubicacion_id = ? ORDER BY s.material",
            (ubicacion_id,),
        ).fetchall()
    finally:
        conn.close()


def guardar_seccion(
    nombre,
    descripcion,
    filas,
    columnas,
    alto_m,
    ancho_m,
    fondo_m,
    capacidad_palets,
    seccion_id=None,
):
    nombre = nombre.strip()
    if not nombre:
        raise ValueError("El nombre de la seccion es obligatorio.")
    if min(filas, columnas, capacidad_palets) < 1:
        raise ValueError("Filas, columnas y capacidad deben ser mayores que cero.")
    if min(alto_m, ancho_m, fondo_m) <= 0:
        raise ValueError("Las dimensiones deben ser mayores que cero.")

    conn = get_conn()
    try:
        prefijo_existente = None
        if seccion_id:
            codigo_existente = conn.execute(
                "SELECT codigo FROM almacen_ubicaciones WHERE seccion_id=? ORDER BY id LIMIT 1",
                (seccion_id,),
            ).fetchone()
            if codigo_existente:
                prefijo_existente = codigo_existente[0].split("-R", 1)[0]
        if seccion_id:
            conn.execute(
                "UPDATE almacen_secciones SET nombre=?, descripcion=?, filas=?, columnas=?, "
                "alto_m=?, ancho_m=?, fondo_m=?, capacidad_palets=?, activa=1 WHERE id=?",
                (nombre, descripcion.strip(), filas, columnas, alto_m, ancho_m, fondo_m, capacidad_palets, seccion_id),
            )
            fuera_de_mapa = conn.execute(
                "SELECT u.id, COALESCE(SUM(s.palets), 0), COALESCE(SUM(s.unidades_sueltas), 0) "
                "FROM almacen_ubicaciones u LEFT JOIN almacen_stock s ON s.ubicacion_id=u.id "
                "WHERE u.seccion_id=? AND (u.fila>? OR u.columna>?) GROUP BY u.id",
                (seccion_id, filas, columnas),
            ).fetchall()
            if any(palets or sueltas for _id, palets, sueltas in fuera_de_mapa):
                raise ValueError("No puedes reducir la seccion mientras sus espacios tengan stock.")
            for ubicacion_id, _palets, _sueltas in fuera_de_mapa:
                conn.execute("UPDATE almacen_ubicaciones SET activa=0 WHERE id=?", (ubicacion_id,))
        else:
            conn.execute(
                "INSERT INTO almacen_secciones "
                "(nombre, descripcion, filas, columnas, alto_m, ancho_m, fondo_m, capacidad_palets) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (nombre, descripcion.strip(), filas, columnas, alto_m, ancho_m, fondo_m, capacidad_palets),
            )
            seccion_id = conn.execute(
                "SELECT id FROM almacen_secciones WHERE nombre = ?", (nombre,)
            ).fetchone()[0]

        prefijo = prefijo_existente or re.sub(r"[^A-Za-z0-9]+", "-", nombre).strip("-").upper() or "SEC"
        for fila in range(1, filas + 1):
            for columna in range(1, columnas + 1):
                codigo = f"{prefijo}-R{fila:02d}-C{columna:02d}"
                existente = conn.execute(
                    "SELECT id FROM almacen_ubicaciones WHERE codigo = ?", (codigo,)
                ).fetchone()
                if existente:
                    conn.execute(
                        "UPDATE almacen_ubicaciones SET seccion_id=?, fila=?, columna=?, "
                        "capacidad_palets=?, alto_m=?, ancho_m=?, fondo_m=?, activa=1 WHERE id=?",
                        (seccion_id, fila, columna, capacidad_palets, alto_m, ancho_m, fondo_m, existente[0]),
                    )
                else:
                    conn.execute(
                        "INSERT INTO almacen_ubicaciones "
                        "(seccion_id, codigo, fila, columna, capacidad_palets, alto_m, ancho_m, fondo_m) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (seccion_id, codigo, fila, columna, capacidad_palets, alto_m, ancho_m, fondo_m),
                    )
        conn.commit()
        return seccion_id
    except Exception:
        conn.close()
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass


def eliminar_seccion(seccion_id):
    conn = get_conn()
    try:
        ocupacion = conn.execute(
            "SELECT COALESCE(SUM(palets), 0) + COALESCE(SUM(unidades_sueltas), 0) FROM almacen_stock s "
            "JOIN almacen_ubicaciones u ON u.id = s.ubicacion_id WHERE u.seccion_id = ?",
            (seccion_id,),
        ).fetchone()[0]
        if ocupacion:
            raise ValueError("No se puede eliminar una seccion con palets almacenados.")
        conn.execute("UPDATE almacen_secciones SET activa=0 WHERE id=?", (seccion_id,))
        conn.execute("UPDATE almacen_ubicaciones SET activa=0 WHERE seccion_id=?", (seccion_id,))
        conn.commit()
    finally:
        conn.close()


def registrar_movimiento(
    tipo,
    ubicacion_id,
    material,
    codigo_material,
    palets,
    unidades_por_palet,
    unidades_sueltas,
    referencia="",
    albaran_id=None,
):
    tipo = tipo.lower().strip()
    material = material.strip()
    codigo_material = codigo_material.strip()
    palets = int(palets)
    unidades_por_palet = int(unidades_por_palet)
    unidades_sueltas = int(unidades_sueltas)
    if tipo not in {"entrada", "salida"}:
        raise ValueError("El movimiento debe ser de entrada o salida.")
    if not material:
        raise ValueError("El material es obligatorio.")
    if palets < 0 or unidades_sueltas < 0 or unidades_por_palet < 1:
        raise ValueError("Las cantidades no pueden ser negativas.")
    if palets == 0 and unidades_sueltas == 0:
        raise ValueError("Indica al menos un palet o una unidad.")

    conn = get_conn()
    try:
        ubicacion = conn.execute(
            "SELECT capacidad_palets FROM almacen_ubicaciones WHERE id=? AND activa=1",
            (ubicacion_id,),
        ).fetchone()
        if not ubicacion:
            raise ValueError("La ubicacion seleccionada no esta activa.")

        stock = conn.execute(
            "SELECT id, palets, unidades_por_palet, unidades_sueltas FROM almacen_stock "
            "WHERE ubicacion_id=? AND material=? AND codigo_material=?",
            (ubicacion_id, material, codigo_material),
        ).fetchone()
        palets_actuales = conn.execute(
            "SELECT COALESCE(SUM(palets), 0) FROM almacen_stock WHERE ubicacion_id=?",
            (ubicacion_id,),
        ).fetchone()[0]

        if tipo == "entrada":
            if palets_actuales + palets > ubicacion[0]:
                raise ValueError(
                    f"La ubicacion solo admite {ubicacion[0]} palets y quedaria con "
                    f"{palets_actuales + palets}."
                )
            if stock:
                nuevo_palets = stock[1] + palets
                nuevo_sueltas = stock[3] + unidades_sueltas
                upp = stock[2]
                conn.execute(
                    "UPDATE almacen_stock SET palets=?, unidades_sueltas=?, actualizado=? WHERE id=?",
                    (nuevo_palets, nuevo_sueltas, ahora(), stock[0]),
                )
            else:
                upp = unidades_por_palet
                conn.execute(
                    "INSERT INTO almacen_stock "
                    "(ubicacion_id, material, codigo_material, palets, unidades_por_palet, unidades_sueltas, actualizado) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (ubicacion_id, material, codigo_material, palets, upp, unidades_sueltas, ahora()),
                )
        else:
            if not stock:
                raise ValueError("No hay ese material en la ubicacion seleccionada.")
            upp = stock[2]
            unidades_disponibles = stock[1] * upp + stock[3]
            unidades_solicitadas = palets * upp + unidades_sueltas
            if unidades_solicitadas > unidades_disponibles:
                raise ValueError(
                    f"Solo hay {unidades_disponibles} unidades disponibles de ese material."
                )
            restantes = unidades_disponibles - unidades_solicitadas
            nuevos_palets, nuevas_sueltas = divmod(restantes, upp)
            if nuevos_palets == 0 and nuevas_sueltas == 0:
                conn.execute("DELETE FROM almacen_stock WHERE id=?", (stock[0],))
            else:
                conn.execute(
                    "UPDATE almacen_stock SET palets=?, unidades_sueltas=?, actualizado=? WHERE id=?",
                    (nuevos_palets, nuevas_sueltas, ahora(), stock[0]),
                )

        conn.execute(
            "INSERT INTO almacen_movimientos "
            "(fecha, tipo, ubicacion_id, material, codigo_material, palets, unidades_por_palet, unidades_sueltas, referencia, albaran_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (ahora(), tipo, ubicacion_id, material, codigo_material, palets, unidades_por_palet, unidades_sueltas, referencia.strip(), albaran_id),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def obtener_movimientos(limite=100):
    conn = get_conn()
    try:
        return conn.execute(
            "SELECT m.fecha, m.tipo, u.codigo, m.material, m.palets, "
            "m.unidades_por_palet, m.unidades_sueltas, m.referencia "
            "FROM almacen_movimientos m JOIN almacen_ubicaciones u ON u.id=m.ubicacion_id "
            "ORDER BY m.id DESC LIMIT ?",
            (limite,),
        ).fetchall()
    finally:
        conn.close()


def resumen_almacen():
    conn = get_conn()
    try:
        fila = conn.execute(
            "SELECT COALESCE(SUM(u.capacidad_palets), 0), COALESCE(SUM(s.palets), 0) "
            "FROM almacen_ubicaciones u LEFT JOIN almacen_stock s ON s.ubicacion_id=u.id "
            "WHERE u.activa=1"
        ).fetchone()
        return int(fila[0]), int(fila[1])
    finally:
        conn.close()


def demanda_albaranes():
    conn = get_conn()
    try:
        filas = conn.execute(
            "SELECT id, nombre, empresa, materiales, estado, fecha FROM albaranes "
            "WHERE estado IN ('entrada', 'procesando') ORDER BY id DESC"
        ).fetchall()
    finally:
        conn.close()

    resultado = []
    patron = re.compile(r"^(.*?)\s*-\s*(\d+)\s+unidades?\s*$", re.IGNORECASE)
    for albaran_id, nombre, empresa, materiales, estado, fecha in filas:
        for linea in (materiales or "").splitlines():
            coincidencia = patron.match(linea.strip())
            if coincidencia:
                material, unidades = coincidencia.groups()
            else:
                material, unidades = linea.strip(), "0"
            if material:
                resultado.append(
                    {
                        "albaran_id": albaran_id,
                        "pedido": nombre,
                        "empresa": empresa,
                        "material": material.strip(),
                        "unidades": int(unidades),
                        "estado": estado,
                        "fecha": fecha,
                    }
                )
    return resultado
