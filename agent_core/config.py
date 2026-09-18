"""
agent_core/config.py

Configuración centralizada del proyecto. La base a la que se conecta
el agente se define en DATABASE_URL (cualquier connection string de
SQLAlchemy: sqlite, postgresql, mysql, etc.). Si no se configura nada,
usa la base SQLite de demo para que el repo siga siendo plug-and-play.
"""

import os

from dotenv import load_dotenv
from sqlalchemy.engine import make_url

load_dotenv()  # carga .env si existe en la raíz del repo; no falla si no existe

DEFAULT_DEMO_DB = "sqlite:///empresa_b2b.db"

# El "or" (en vez de un segundo argumento en os.environ.get) hace que
# un DATABASE_URL vacío en el .env también caiga en el default, no
# solo cuando la variable no está definida.
DATABASE_URL = os.environ.get("DATABASE_URL") or DEFAULT_DEMO_DB

# Nombre del dialecto SQL (sqlite, postgresql, mysql, ...). Se saca
# parseando la URL, no con create_engine(): create_engine() intenta
# importar el driver de la base (psycopg2, pymysql, etc.) al toque, y
# no queremos que eso rompa el import de este módulo si ese driver
# todavía no está instalado.
SQL_DIALECT = make_url(DATABASE_URL).get_backend_name()
