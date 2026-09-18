"""
agent_core/schema.py

Capa de esquema: inspecciona la base de datos real (cualquiera que
sea) y arma un bloque de texto con la información que el modelo
necesita para escribir SQL correcto: tablas, columnas, tipos, claves
foráneas y valores posibles de las columnas categóricas, detectadas
automáticamente por cardinalidad en vez de estar escritas a mano.
"""

from sqlalchemy import create_engine, inspect, text

from agent_core.config import DATABASE_URL

# Una columna de texto se considera "categórica" si tiene pocos
# valores distintos en relación al total de filas. En ese caso vale
# la pena mostrarle al modelo los valores reales en vez de dejar que
# los adivine.
MAX_VALORES_DISTINTOS = 30
MAX_PROPORCION_DISTINTOS = 0.1

TIPOS_TEXTO = {"VARCHAR", "CHAR", "TEXT", "STRING", "NVARCHAR", "CLOB"}


def _es_columna_de_texto(tipo) -> bool:
    return any(t in str(tipo).upper() for t in TIPOS_TEXTO)


def _contar_filas(engine, tabla) -> int:
    with engine.connect() as con:
        return con.execute(text(f"SELECT COUNT(*) FROM {tabla}")).scalar()


def _cardinalidad(engine, tabla, columna) -> int:
    with engine.connect() as con:
        return con.execute(text(f"SELECT COUNT(DISTINCT {columna}) FROM {tabla}")).scalar()


def _valores_distintos(engine, tabla, columna):
    with engine.connect() as con:
        rows = con.execute(text(f"SELECT DISTINCT {columna} FROM {tabla}")).fetchall()
    return sorted(str(r[0]) for r in rows if r[0] is not None)


def build_schema_context(engine=None, glosario: dict | None = None) -> str:
    """
    Arma el bloque de texto con el esquema, listo para inyectar en el
    prompt.

    `glosario` es opcional: un dict con claves `tabla` -> "descripción"
    y `(tabla, columna)` -> "descripción" para sumar contexto de
    negocio cuando el usuario lo tiene a mano. Sin glosario, el
    esquema se arma igual, solo con lo que la base puede decir de
    sí misma.
    """
    engine = engine or create_engine(DATABASE_URL)
    glosario = glosario or {}
    inspector = inspect(engine)

    bloques = []
    for tabla in inspector.get_table_names():
        columnas = inspector.get_columns(tabla)
        fks = {
            fk["constrained_columns"][0]: f'{fk["referred_table"]}.{fk["referred_columns"][0]}'
            for fk in inspector.get_foreign_keys(tabla)
        }
        total_filas = _contar_filas(engine, tabla)

        descripcion_tabla = glosario.get(tabla, "")
        encabezado = f"Tabla: {tabla}"
        if descripcion_tabla:
            encabezado += f" — {descripcion_tabla}"
        lineas = [encabezado]

        for col in columnas:
            nombre, tipo = col["name"], col["type"]
            extra = glosario.get((tabla, nombre), "")

            if nombre in fks:
                extra = f"FK → {fks[nombre]}. {extra}".strip()

            if total_filas > 0 and _es_columna_de_texto(tipo):
                cardinalidad = _cardinalidad(engine, tabla, nombre)
                es_categorica = (
                    cardinalidad <= MAX_VALORES_DISTINTOS
                    and cardinalidad / total_filas <= MAX_PROPORCION_DISTINTOS
                )
                if es_categorica:
                    valores = _valores_distintos(engine, tabla, nombre)
                    extra = f"{extra} Valores posibles: {', '.join(valores)}.".strip()

            linea = f"  - {nombre} ({tipo})"
            if extra:
                linea += f" — {extra}"
            lineas.append(linea)

        bloques.append("\n".join(lineas))

    return "\n\n".join(bloques)


if __name__ == "__main__":
    print(build_schema_context())
