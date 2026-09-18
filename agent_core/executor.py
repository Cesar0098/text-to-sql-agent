"""
agent_core/executor.py

Ejecuta una consulta SQL contra la base configurada en DATABASE_URL,
en modo de solo lectura. Hay dos capas de seguridad:

  1. Validación del texto de la consulta (bloquea DML/DDL y sentencias
     múltiples antes de tocar la base) — funciona sin importar el motor.
  2. Para SQLite, la conexión se abre en modo "ro" real, así que aunque
     la validación fallara, la base rechaza cualquier escritura igual.
     Para Postgres/MySQL/etc. no existe un equivalente a nivel de
     connection string: esa segunda capa depende de que el usuario de
     base de datos configurado en DATABASE_URL tenga permisos de solo
     SELECT (ver README — es responsabilidad de quien despliega el
     agente, no algo que el código pueda garantizar por sí solo).
"""

import re
import sqlite3

import pandas as pd
from sqlalchemy import create_engine

from agent_core.config import DATABASE_URL

PALABRAS_PROHIBIDAS = [
    "insert", "update", "delete", "drop", "alter", "create",
    "truncate", "replace", "attach", "pragma", "vacuum",
]

# Tope de filas si la consulta generada no trae su propio LIMIT. Evita
# que una pregunta tipo "mostrame todos los pagos" devuelva miles de
# filas que después inflan el prompt de interpretación.
MAX_FILAS_DEFAULT = 200


class ConsultaNoPermitida(Exception):
    """Se lanza cuando la consulta generada no es un SELECT seguro."""


def validar_consulta(sql: str) -> None:
    sql_limpio = sql.strip().lower()

    if not sql_limpio.startswith("select"):
        raise ConsultaNoPermitida("Solo se permiten consultas SELECT.")

    if ";" in sql_limpio[:-1]:
        raise ConsultaNoPermitida("No se permite más de una sentencia por consulta.")

    for palabra in PALABRAS_PROHIBIDAS:
        if re.search(rf"\b{palabra}\b", sql_limpio):
            raise ConsultaNoPermitida(
                f"La palabra '{palabra}' no está permitida en una consulta de solo lectura."
            )


def _asegurar_limite(sql: str, limite: int) -> str:
    """Si la consulta no trae un LIMIT propio, le agrega uno antes de ejecutarla.

    Es una red de seguridad extra sobre la regla que ya le dimos al
    modelo en el prompt: no confiamos en que el modelo la respete
    siempre, así que la garantizamos acá en código.
    """
    sql_limpio = sql.strip().rstrip(";").strip()
    if re.search(r"\blimit\b", sql_limpio, flags=re.IGNORECASE):
        return sql_limpio + ";"
    return f"{sql_limpio} LIMIT {limite};"


def _es_sqlite(database_url: str) -> bool:
    return database_url.startswith("sqlite")


def _conectar_sqlite_readonly(database_url: str):
    ruta = database_url.replace("sqlite:///", "")
    uri = f"file:{ruta}?mode=ro"
    return sqlite3.connect(uri, uri=True)


def ejecutar_consulta(
    sql: str, database_url: str = DATABASE_URL, limite_filas: int = MAX_FILAS_DEFAULT
) -> pd.DataFrame:
    """Valida y ejecuta el SQL, devolviendo el resultado como DataFrame."""
    validar_consulta(sql)
    sql = _asegurar_limite(sql, limite_filas)

    if _es_sqlite(database_url):
        con = _conectar_sqlite_readonly(database_url)
        try:
            return pd.read_sql_query(sql, con)
        finally:
            con.close()

    engine = create_engine(database_url)
    with engine.connect() as con:
        return pd.read_sql_query(sql, con)


if __name__ == "__main__":
    df = ejecutar_consulta(
        "SELECT tamano_empresa, COUNT(*) AS cantidad FROM clientes GROUP BY tamano_empresa;"
    )
    print("--- Consulta normal ---")
    print(df)

    for sql_malicioso in [
        "DELETE FROM clientes;",
        "SELECT 1; DROP TABLE clientes;",
    ]:
        try:
            ejecutar_consulta(sql_malicioso)
            print(f"¡ATENCIÓN! No se bloqueó: {sql_malicioso}")
        except ConsultaNoPermitida as e:
            print(f"Bloqueada por validación: {e}")
