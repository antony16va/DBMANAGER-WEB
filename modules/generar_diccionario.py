import sys
import psycopg2
from pathlib import Path

# Constantes de configuración RTF
ESQUEMAS_HEADERS = ["ESQUEMA", "DESCRIPCION"]
ESQUEMAS_WIDTHS = [3000, 4500]

TBSPACE_HEADERS = ["TABLESPACE", "DESCRIPCION"]
TBSPACE_WIDTHS = [3000, 4500]

EXTENSION_HEADERS = ["EXTENSIONES", "DESCRIPCION"]
EXTENSION_WIDTHS = [3000, 4500]

ENTIDADES_HEADERS = ["N", "Nombre de la Tabla", "Descripcion"]
ENTIDADES_WIDTHS = [450, 3000, 4500]

ATRIBUTOS_HEADERS = ["N", "Campo", "Tipo de Dato", "Nulos", "PK", "FK", "Descripcion", "Valores permitidos"]
ATRIBUTOS_WIDTHS = [450, 2100, 1300, 750, 470, 470, 2100, 2300]

PROC_HEADERS = ["N", "Procedimiento", "Descripcion"]
PROC_WIDTHS = [450, 2400, 6500]

FUNC_HEADERS = ["N", "Funcion", "Descripcion"]
FUNC_WIDTHS = [450, 2400, 6500]

VISTAS_HEADERS = ["N", "Vista", "Descripcion"]
VISTAS_WIDTHS = [450, 3000, 5500]

TRIGGERS_HEADERS = ["N", "Triggers", "Descripcion"]
TRIGGERS_WIDTHS = [450, 3000, 5500]

F_TRIGGERS_HEADERS = ["N", "Funciones Triggers", "Descripcion"]
F_TRIGGERS_WIDTHS = [450, 3000, 5500]

TYPES_HEADERS = ["N", "Types", "Descripcion"]
TYPES_WIDTHS = [450, 3000, 5500]

DBLINKS_HEADERS = ["N", "Dblink / Foreign Server", "Descripcion"]
DBLINKS_WIDTHS = [450, 3000, 5500]

T_FORANEA_HEADERS = ["N", "Campo", "Tipo de Dato", "Nulos", "PK", "FK", "Descripcion", "Valores permitidos"]
T_FORANEA_WIDTHS = [450, 2100, 1300, 750, 470, 470, 2100, 2300]



def escape_rtf(text):
    """Escapa caracteres especiales para formato RTF"""
    if text is None:
        return ""
    
    text = str(text)
    sb = []
    
    for char in text:
        code = ord(char)
        if char == '\\':
            sb.append('\\\\')
        elif char == '{':
            sb.append('\\{')
        elif char == '}':
            sb.append('\\}')
        elif char == '\n':
            sb.append('\\line ')
        elif char == '\r':
            continue
        elif 32 <= code <= 126:
            sb.append(char)
        else:
            sb.append(f"\\u{code}?")
    
    return ''.join(sb)

def create_table_row(cells, widths, is_header=False):
    """Crea una fila de tabla en formato RTF"""
    row = []
    row.append("\\trowd\\trgaph108\\trleft0")
    row.append("\\trbrdrt\\brdrs\\brdrw10")
    row.append("\\trbrdrl\\brdrs\\brdrw10")
    row.append("\\trbrdrb\\brdrs\\brdrw10")
    row.append("\\trbrdrr\\brdrs\\brdrw10")
    
    pos = 0
    for width in widths:
        pos += width
        row.append("\\clbrdrt\\brdrs\\brdrw10")
        row.append("\\clbrdrl\\brdrs\\brdrw10")
        row.append("\\clbrdrb\\brdrs\\brdrw10")
        row.append("\\clbrdrr\\brdrs\\brdrw10")
        if is_header:
            row.append("\\clcbpat3")
        row.append(f"\\cellx{pos}")
    
    row.append("\n")
    
    for cell in cells:
        if is_header:
            row.append("\\qc\\b\\cf2 ")
        else:
            row.append("\\ql ")
        row.append(escape_rtf(cell or ""))
        if is_header:
            row.append("\\b0\\cf1")
        row.append("\\cell ")
    
    row.append("\\row\n")
    return ''.join(row)

def obtener_esquemas_con_comentarios(cursor):
    """Obtiene esquemas con sus comentarios"""
    sql = """
    SELECT 
        n.nspname AS esquema,
        obj_description(n.oid, 'pg_namespace') AS comentario
    FROM pg_namespace n
    WHERE n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
      AND n.nspname NOT LIKE 'pg_temp_%'
      AND n.nspname NOT LIKE 'pg_toast_temp_%'
    ORDER BY n.nspname;
    """
    try:
        cursor.execute(sql)
        return {row[0]: row[1] or '' for row in cursor.fetchall()}
    except Exception as e:
        print(f"Error al obtener esquemas: {e}")
        return {}

def obtener_tablespaces_con_comentarios(cursor):
    """Obtiene tablespaces con sus comentarios"""
    sql = """
    SELECT 
        spcname AS tablespace,
        obj_description(oid, 'pg_tablespace') AS comentario
    FROM pg_tablespace
    ORDER BY spcname;
    """
    try:
        cursor.execute(sql)
        return {row[0]: row[1] or '' for row in cursor.fetchall()}
    except Exception as e:
        print(f"Error al obtener tablespaces: {e}")
        return {}

def obtener_extensiones_con_comentarios(cursor, schema):
    """Obtiene extensiones con sus comentarios"""
    sql = """
    SELECT 
        e.extname AS extension,
        obj_description(e.oid, 'pg_extension') AS comentario
    FROM pg_extension e
    JOIN pg_namespace n ON n.oid = e.extnamespace
    WHERE n.nspname = %s
    ORDER BY e.extname;
    """
    try:
        cursor.execute(sql, (schema,))
        return {row[0]: row[1] or '' for row in cursor.fetchall()}
    except Exception as e:
        print(f"Error al obtener extensiones: {e}")
        return {}

def obtener_tablas_con_comentarios(cursor, schema):
    """Obtiene tablas con sus comentarios"""
    sql = """
    SELECT 
        c.relname AS tabla,
        obj_description(c.oid) AS comentario
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relkind = 'r'
      AND n.nspname = %s
    ORDER BY tabla;
    """
    try:
        cursor.execute(sql, (schema,))
        return {row[0]: row[1] or '' for row in cursor.fetchall()}
    except Exception as e:
        print(f"Error al obtener tablas: {e}")
        return {}

def obtener_nombres_tablas(cursor, schema):
    """Obtiene lista de nombres de tablas"""
    sql = """
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = %s
      AND table_type = 'BASE TABLE'
    ORDER BY table_name
    """
    try:
        cursor.execute(sql, (schema,))
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error al obtener nombres de tablas: {e}")
        return []

def obtener_campos_tabla(cursor, schema, table_name):
    """Obtiene información detallada de campos de una tabla"""
    sql = """
    SELECT
        lower(c.column_name) AS nombre_columna,
        CASE
            WHEN c.udt_name = 'date' THEN 'date'
            WHEN c.udt_name = 'timestamp' THEN 'timestamp'
            WHEN c.udt_name = 'int8' THEN 'bigint'
            WHEN c.udt_name = 'int2' THEN 'smallint'
            WHEN c.udt_name = 'text' THEN 'text'
            WHEN c.udt_name = 'numeric' THEN 'numeric'
            WHEN c.udt_name = 'jsonb' THEN 'jsonb'
            WHEN c.udt_name IN ('bpchar', 'varchar') THEN 'varchar(' || COALESCE(c.character_maximum_length, 255)::text || ')'
            ELSE
                CASE
                    WHEN c.udt_name = 'int4' THEN 'integer'
                    WHEN c.character_maximum_length IS NOT NULL THEN c.udt_name || ' (' || c.character_maximum_length || ')'
                    ELSE c.udt_name
                END
        END AS tipo,
        CASE WHEN c.is_nullable = 'YES' THEN 'SI' ELSE 'NO' END AS permite_nulos,
        COALESCE(pk_info.is_pk, '') AS pk,
        COALESCE(fk_info.is_fk, '') AS fk,
        COALESCE(pgd.description, '') AS descripcion_columna,
        CASE
            WHEN c.data_type = 'text' THEN 'Cadena tipo text'
            WHEN c.data_type = 'numeric' THEN 'Numero decimal'
            WHEN c.data_type = 'jsonb' THEN 'Representacion binaria de los datos JSON'
            WHEN c.data_type IN ('integer','smallint','bigint') THEN 'Numero entero positivo'
            ELSE
                CASE
                    WHEN c.data_type LIKE 'timestamp%%' OR c.data_type = 'date' THEN 'dd/mm/aaaa hh:mm:ss'
                    WHEN c.character_maximum_length IS NOT NULL THEN 'Cadena de hasta ' || c.character_maximum_length || ' caracteres'
                    ELSE 'Valor especifico del tipo de dato'
                END
        END AS valores_permitidos
    FROM information_schema.columns c
    LEFT JOIN pg_catalog.pg_description pgd ON (
        pgd.objoid = (
            SELECT c_table.oid
            FROM pg_catalog.pg_class c_table
            WHERE c_table.relname = c.table_name
              AND c_table.relnamespace = (
                  SELECT n.oid
                  FROM pg_catalog.pg_namespace n
                  WHERE n.nspname = c.table_schema
              )
        )
        AND pgd.objsubid = c.ordinal_position
    )
    LEFT JOIN (
        SELECT
            kcu.table_schema,
            kcu.table_name,
            kcu.column_name,
            'SI' AS is_pk
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema    = kcu.table_schema
         AND tc.table_name      = kcu.table_name
        WHERE tc.constraint_type = 'PRIMARY KEY'
    ) AS pk_info
      ON c.table_schema = pk_info.table_schema
     AND c.table_name   = pk_info.table_name
     AND c.column_name  = pk_info.column_name
    LEFT JOIN (
        SELECT
            kcu.table_schema,
            kcu.table_name,
            kcu.column_name,
            'SI' AS is_fk
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_name = kcu.constraint_name
         AND tc.table_schema    = kcu.table_schema
         AND tc.table_name      = kcu.table_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
    ) AS fk_info
      ON c.table_schema = fk_info.table_schema
     AND c.table_name   = fk_info.table_name
     AND c.column_name  = fk_info.column_name
    WHERE c.table_schema = %s
      AND c.table_name = %s
    ORDER BY c.ordinal_position;
    """
    try:
        cursor.execute(sql, (schema, table_name))
        rows = cursor.fetchall()
        
        if not rows:
            return []
        
        # Obtener nombres de columnas del cursor
        columns = [desc[0] for desc in cursor.description]
        
        # Convertir cada fila en diccionario
        results = []
        for row in rows:
            if len(row) != len(columns):
                print(f"Warning en {table_name}: row tiene {len(row)} valores pero esperaba {len(columns)} columnas")
                continue
            results.append(dict(zip(columns, row)))
        
        return results
        
    except Exception as e:
        print(f"Error al obtener campos de {table_name}: {e}")
        import traceback
        traceback.print_exc()
        return []

def obtener_procedimientos_con_comentarios(cursor, schema):
    """Obtiene procedimientos con sus comentarios"""
    sql = """
    SELECT 
        p.proname AS procedimiento,
        obj_description(p.oid, 'pg_proc') AS comentario
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = %s
      AND p.prokind = 'p'
    ORDER BY procedimiento;
    """
    try:
        cursor.execute(sql, (schema,))
        return {row[0]: row[1] or '' for row in cursor.fetchall()}
    except Exception as e:
        print(f"Error al obtener procedimientos: {e}")
        return {}

def obtener_funciones_con_comentarios(cursor, schema):
    """Obtiene funciones con sus comentarios"""
    sql = """
    SELECT 
        p.proname AS funcion,
        obj_description(p.oid, 'pg_proc') AS comentario
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = %s
      AND p.prokind = 'f'
    ORDER BY funcion;
    """
    try:
        cursor.execute(sql, (schema,))
        return {row[0]: row[1] or '' for row in cursor.fetchall()}
    except Exception as e:
        print(f"Error al obtener funciones: {e}")
        return {}

def obtener_vistas_con_comentarios(cursor, schema):
    """Obtiene vistas con sus comentarios"""
    sql = """
    SELECT 
        c.relname AS vista,
        obj_description(c.oid) AS comentario
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE c.relkind = 'v'
      AND n.nspname = %s
    ORDER BY vista;
    """
    try:
        cursor.execute(sql, (schema,))
        return {row[0]: row[1] or '' for row in cursor.fetchall()}
    except Exception as e:
        print(f"Error al obtener vistas: {e}")
        return {}

def generar_diccionario_rtf(host, port, database, user, password, schema, output_file):
    """Genera el diccionario de datos en formato RTF"""
    
    # Crear directorio de salida si no existe
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("Iniciando generación de diccionario...")
    print(f"Esquema: {schema}")
    print(f"Archivo de salida: {output_file}")
    
    # Conectar a la base de datos
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        cursor = conn.cursor()
        print("Conexión exitosa a PostgreSQL")
    except Exception as e:
        print(f"Error al conectar a la base de datos: {e}")
        sys.exit(3)
    
    # Obtener datos
    esquemas = obtener_esquemas_con_comentarios(cursor)
    tablespaces = obtener_tablespaces_con_comentarios(cursor)
    extensiones = obtener_extensiones_con_comentarios(cursor, schema)
    tablas = obtener_tablas_con_comentarios(cursor, schema)
    table_names = obtener_nombres_tablas(cursor, schema)
    print(f"Tablas detectadas: {len(table_names)}")
    
    procedimientos = obtener_procedimientos_con_comentarios(cursor, schema)
    funciones = obtener_funciones_con_comentarios(cursor, schema)
    vistas = obtener_vistas_con_comentarios(cursor, schema)
    
    # Generar archivo RTF
    with open(output_file, 'w', encoding='utf-8') as writer:
        # Cabecera RTF
        writer.write("{\\rtf1\\ansi\\deff0 {\\fonttbl {\\f0 Arial;}}\n")
        writer.write("{\\colortbl;\\red0\\green0\\blue0;\\red255\\green255\\blue255;\\red25\\green25\\blue112;}\n")
        writer.write("\\paperw11906\\paperh16838\\margl1063\\margr973\\margt1063\\margb1063\n")
        writer.write("\\f0\\fs20\n")
        
        # Título
        writer.write("\\qc\\b\\fs36 DICCIONARIO DE DATOS\\b0\\fs22\\par\n")
        writer.write("\\par\\par\n")
        
        # 1) Esquemas
        writer.write("\\ql\\b\\fs28 Descripcion de Esquemas\\b0\\fs18\\par\n")
        writer.write("\\par\n")
        if esquemas:
            writer.write(create_table_row(ESQUEMAS_HEADERS, ESQUEMAS_WIDTHS, True))
            for esq_name, desc in esquemas.items():
                writer.write(create_table_row([esq_name, desc or ""], ESQUEMAS_WIDTHS, False))
        else:
            writer.write("\\i No se encontraron esquemas.\\i0\\par\n")
        
        # 2) Tablespaces
        writer.write("\\ql\\b\\fs28 Descripcion de Tablespaces\\b0\\fs18\\par\n")
        writer.write("\\par\n")
        if tablespaces:
            writer.write(create_table_row(TBSPACE_HEADERS, TBSPACE_WIDTHS, True))
            for tbs_name, desc in tablespaces.items():
                writer.write(create_table_row([tbs_name, desc or ""], TBSPACE_WIDTHS, False))
        else:
            writer.write("\\i No se encontraron tablespaces personalizados.\\i0\\par\n")
        
        # 3) Extensiones
        writer.write("\\ql\\b\\fs28 Descripcion de Extensiones\\b0\\fs18\\par\n")
        writer.write("\\par\n")
        if extensiones:
            writer.write(create_table_row(EXTENSION_HEADERS, EXTENSION_WIDTHS, True))
            for ext_name, desc in extensiones.items():
                writer.write(create_table_row([ext_name, desc or ""], EXTENSION_WIDTHS, False))
        else:
            writer.write("\\i No aplica.\\i0\\par\n")
        
        writer.write("\\par\\page\n")
        
        # 4) Tablas (resumen)
        writer.write("\\ql\\b\\fs28 Descripcion de Tablas\\b0\\fs18\\par\n")
        writer.write("\\par\n")
        if tablas:
            writer.write(create_table_row(ENTIDADES_HEADERS, ENTIDADES_WIDTHS, True))
            i = 1
            for t_name, desc in tablas.items():
                writer.write(create_table_row([str(i), t_name, desc or ""], ENTIDADES_WIDTHS, False))
                i += 1
        else:
            writer.write("\\i No se encontraron comentarios de tablas en el esquema.\\i0\\par\n")
        
        writer.write("\\par\\page\n")
        
        # 5) Campos (detalle por tabla)
        writer.write("\\b\\fs28 Descripcion de Atributos\\b0\\fs18\\par\n")
        writer.write("\\par\n")
        
        for t_name in table_names:
            writer.write(f"\\b\\fs24 Tabla: {escape_rtf(t_name)}\\b0\\fs18\\par\n")
            writer.write("\\par\n")
            
            campos = obtener_campos_tabla(cursor, schema, t_name)
            if campos:
                writer.write(create_table_row(ATRIBUTOS_HEADERS, ATRIBUTOS_WIDTHS, True))
                j = 1
                for campo in campos:
                    cells = [
                        str(j),
                        campo.get('nombre_columna', ''),
                        campo.get('tipo', ''),
                        campo.get('permite_nulos', ''),
                        campo.get('pk', ''),
                        campo.get('fk', ''),
                        campo.get('descripcion_columna', ''),
                        campo.get('valores_permitidos', '')
                    ]
                    writer.write(create_table_row(cells, ATRIBUTOS_WIDTHS, False))
                    j += 1
            else:
                writer.write("\\i No se encontraron columnas\\i0\\par\n")
            writer.write("\\par\n")
        
        # 6) Procedimientos
        writer.write("\\page\n")
        writer.write("\\b\\fs28 Descripcion de Procedimientos\\b0\\fs18\\par\n")
        writer.write("\\par\n")
        if procedimientos:
            writer.write(create_table_row(PROC_HEADERS, PROC_WIDTHS, True))
            k = 1
            for p_name, p_desc in procedimientos.items():
                writer.write(create_table_row([str(k), p_name, p_desc or ""], PROC_WIDTHS, False))
                k += 1
        else:
            writer.write("\\i No aplica.\\i0\\par\n")
        writer.write("\\par\n")
        
        # 7) Funciones
        writer.write("\\page\n")
        writer.write("\\b\\fs28 Descripcion de Funciones\\b0\\fs18\\par\n")
        writer.write("\\par\n")
        if funciones:
            writer.write(create_table_row(FUNC_HEADERS, FUNC_WIDTHS, True))
            m = 1
            for f_name, f_desc in funciones.items():
                writer.write(create_table_row([str(m), f_name, f_desc or ""], FUNC_WIDTHS, False))
                m += 1
        else:
            writer.write("\\i No aplica.\\i0\\par\n")
        writer.write("\\par\n")
        
        # 8) Vistas
        writer.write("\\ql\\b\\fs28 Descripcion de Vistas\\b0\\fs18\\par\n")
        writer.write("\\par\n")
        if vistas:
            writer.write(create_table_row(VISTAS_HEADERS, VISTAS_WIDTHS, True))
            j = 1
            for v_name, desc in vistas.items():
                writer.write(create_table_row([str(j), v_name, desc or ""], VISTAS_WIDTHS, False))
                j += 1
        else:
            writer.write("\\i No aplica.\\i0\\par\n")
        writer.write("\\par\\page\n")
        
        # 9) Triggers
        writer.write("\\ql\\b\\fs28 Descripcion de Triggers\\b0\\fs18\\par\n")
        writer.write("\\par\n")
        if vistas:
            writer.write(create_table_row(VISTAS_HEADERS, VISTAS_WIDTHS, True))
            l = 1
            for v_name, desc in vistas.items():
                writer.write(create_table_row([str(j), v_name, desc or ""], TRIGGERS_WIDTHS, False))
                l += 1
        else:
            writer.write("\\i No aplica.\\i0\\par\n")
        writer.write("\\par\\page\n")

        # 10) Funciones Triggers
        writer.write("\\ql\\b\\fs28 Descripcion de Funciones Triggers\\b0\\fs18\\par\n")
        writer.write("\\par\n")
        if vistas:
            writer.write(create_table_row(VISTAS_HEADERS, VISTAS_WIDTHS, True))
            p = 1
            for v_name, desc in vistas.items():
                writer.write(create_table_row([str(j), v_name, desc or ""], TRIGGERS_WIDTHS, False))
                p += 1
        else:
            writer.write("\\i No aplica.\\i0\\par\n")
        writer.write("\\par\\page\n")
       
        # 11) Types
        writer.write("\\ql\\b\\fs28 Descripcion de Types\\b0\\fs18\\par\n")
        writer.write("\\par\n")
        if vistas:
            writer.write(create_table_row(VISTAS_HEADERS, VISTAS_WIDTHS, True))
            q = 1
            for v_name, desc in vistas.items():
                writer.write(create_table_row([str(j), v_name, desc or ""], TYPES_WIDTHS, False))
                q += 1
        else:
            writer.write("\\i No aplica.\\i0\\par\n")
        writer.write("\\par\\page\n")

        # 12) Dblinks / Foreign Servers
        writer.write("\\ql\\b\\fs28 Descripcion de Dblinks / Foreign Servers\\b0\\fs18\\par\n")
        writer.write("\\par\n")
        if vistas:
            writer.write(create_table_row(VISTAS_HEADERS, VISTAS_WIDTHS, True))
            r = 1
            for v_name, desc in vistas.items():
                writer.write(create_table_row([str(j), v_name, desc or ""], DBLINKS_WIDTHS, False))
                r += 1
        else:
            writer.write("\\i No aplica.\\i0\\par\n")
        writer.write("\\par\\page\n")

        # 13) Tablas Foráneas
        writer.write("\\ql\\b\\fs28 Descripcion de Tablas Foráneas\\b0\\fs18\\par\n")
        writer.write("\\par\n")
        
        for t_name in table_names:
            writer.write(f"\\b\\fs24 Tabla: {escape_rtf(t_name)}\\b0\\fs18\\par\n")
            writer.write("\\par\n")

            campos = obtener_campos_tabla(cursor, schema, t_name)
            if campos:
                writer.write(create_table_row(ATRIBUTOS_HEADERS, ATRIBUTOS_WIDTHS, True))
                s = 1
                for campo in campos:
                    cells = [
                        str(j),
                        campo.get('nombre_columna', ''),
                        campo.get('tipo', ''),
                        campo.get('permite_nulos', ''),
                        campo.get('pk', ''),
                        campo.get('fk', ''),
                        campo.get('descripcion_columna', ''),
                        campo.get('valores_permitidos', '')
                    ]
                    writer.write(create_table_row(cells, ATRIBUTOS_WIDTHS, False))
                    s += 1
            else:
                writer.write("\\i No se encontraron columnas\\i0\\par\n")
            writer.write("\\par\n")
           






        # Cierre del documento
        writer.write("}\n")
    
    cursor.close()
    conn.close()
    
    print(f"Archivo RTF generado en: {output_file}")

def main():
    if len(sys.argv) != 8:
        print("Error: Se requieren 7 parametros")
        print("Uso: python generar_diccionario.py <host> <puerto> <bd> <usuario> <password> <esquema> <ruta_salida_rtf>")
        sys.exit(1)
    
    host = sys.argv[1]
    port = sys.argv[2]
    database = sys.argv[3]
    user = sys.argv[4]
    password = sys.argv[5]
    schema = sys.argv[6]
    output_file = sys.argv[7]
    
    generar_diccionario_rtf(host, port, database, user, password, schema, output_file)

if __name__ == "__main__":
    main()