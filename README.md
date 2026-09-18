# Agente Analítico Text-to-SQL

> Este README todavía es parcial: por ahora documenta las decisiones de
> seguridad del proyecto. La instalación, configuración y uso se agregan
> en el último paso, cuando esté lista la interfaz en Streamlit.

## Seguridad: cómo se previene SQL injection y escritura accidental

El agente nunca ejecuta SQL "a ciegas". Hay tres capas independientes,
pensadas para que si una falla, las otras dos sigan protegiendo la base:

### 1. Validación del texto de la consulta (`agent_core/executor.py`)

Antes de tocar la base, cada consulta generada por el modelo pasa por
`validar_consulta()`, que rechaza cualquier cosa que no sea un único
`SELECT`:

- Tiene que empezar con `SELECT`.
- No puede tener más de una sentencia (se busca un `;` antes del final,
  que sería la forma típica de un ataque de SQL injection encadenado).
- No puede contener palabras como `insert`, `update`, `delete`, `drop`,
  `alter`, `create`, `truncate`, `attach` o `pragma`, sin importar dónde
  aparezcan en la consulta.

Esta capa es independiente del motor de base de datos: funciona igual
para SQLite, Postgres o MySQL.

### 2. Conexión real de solo lectura (depende del motor)

- **SQLite** (el modo demo, por defecto): la conexión se abre con
  `sqlite3.connect("file:archivo.db?mode=ro", uri=True)`. Esto hace que
  la base rechace cualquier escritura a nivel de driver, incluso si la
  validación del punto 1 fallara. Se puede comprobar corriendo un
  `DELETE` directo contra esa conexión: SQLite lo rechaza con
  `attempt to write a readonly database`.
- **Postgres / MySQL / otros motores**: no existe un equivalente al
  `mode=ro` de SQLite a nivel de connection string. Para tener una
  protección real acá, **hace falta crear un usuario de base de datos
  con permisos de solo `SELECT`** y usar sus credenciales en
  `DATABASE_URL`. Por ejemplo, en Postgres:

  ```sql
  CREATE USER agente_readonly WITH PASSWORD 'una_contraseña_segura';
  GRANT CONNECT ON DATABASE tu_base TO agente_readonly;
  GRANT USAGE ON SCHEMA public TO agente_readonly;
  GRANT SELECT ON ALL TABLES IN SCHEMA public TO agente_readonly;
  -- para que las tablas que se creen después también queden de solo lectura:
  ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO agente_readonly;
  ```

  En MySQL el equivalente es `GRANT SELECT ON tu_base.* TO 'agente_readonly'@'%';`.

  Esto es responsabilidad de quien despliega el agente, no algo que el
  código pueda garantizar por sí solo — por eso queda documentado acá
  en vez de asumido en silencio.

### 3. Límite de filas por consulta (`agent_core/executor.py`)

Si la consulta generada no trae su propio `LIMIT`, el ejecutor le agrega
uno (200 filas por defecto) antes de correrla. No es una medida de
seguridad contra ataques, sino contra un problema real de otro tipo:
una pregunta como "mostrame todos los pagos" puede generar un `SELECT *`
sin `LIMIT` que devuelva miles de filas, infle el prompt de la capa de
interpretación de negocio y encarezca la llamada al modelo sin agregar
valor. El prompt (`prompts/generar_sql.txt`) también le pide al modelo
que agregue un `LIMIT` razonable por su cuenta, pero esta capa en código
no depende de que el modelo obedezca esa instrucción.

## Por qué el esquema no está hardcodeado

`agent_core/schema.py` inspecciona la base real con SQLAlchemy en vez
de asumir una estructura fija de tablas. Esto es lo que permite que el
mismo agente funcione contra cualquier base de datos: basta con cambiar
`DATABASE_URL`. Las columnas categóricas (con pocos valores distintos
en relación al total de filas) se detectan automáticamente para
mostrarle al modelo los valores reales que existen, en vez de dejar que
los adivine.
