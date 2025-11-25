import json
import re
import subprocess
import sys
import builtins
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from pathlib import Path


class Error:
    def __init__(self, linea: int, tipo_objeto: str, nombre_objeto: str, tipo_error: str, mensaje: str, valor_actual: str, valor_sugerido: str = None):
        self.linea = linea
        self.tipo_objeto = tipo_objeto
        self.nombre_objeto = nombre_objeto
        self.tipo_error = tipo_error
        self.mensaje = mensaje
        self.valor_actual = valor_actual
        self.valor_sugerido = valor_sugerido
    
    def __str__(self):
        return f"Línea {self.linea} [{self.tipo_objeto}] {self.nombre_objeto}: {self.mensaje}"


class ValidadorDDL:
    def __init__(self, reglas_json: str):
        self.reglas_json = reglas_json
        self.reglas = {}
        self.errores = []
        self.warnings = []
        self.ddl_file = None
        self.objetos_validados = set()
        
    def cargar_reglas(self):
        with open(self.reglas_json, 'r', encoding='utf-8') as f:
            self.reglas = json.load(f)
    
    def generar_ddl_desde_bd(self, host: str, puerto: str, usuario: str, base_datos: str, archivo_salida: str, password: str = None):
        comando = [
            'pg_dump',
            '-h', host,
            '-p', str(puerto),
            '-U', usuario,
            '-d', base_datos,
            '-s',
            '--no-owner',
            '--no-privileges',
            '-f', archivo_salida
        ]
        
        import os
        env = os.environ.copy()
        if password:
            env['PGPASSWORD'] = password
        
        try:
            resultado = subprocess.run(
                comando,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            self.ddl_file = archivo_salida
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error al ejecutar pg_dump: {e.stderr}")
            return False
        except FileNotFoundError:
            print("Error: pg_dump no está instalado o no está en el PATH")
            return False
    
    def cargar_ddl_existente(self, archivo_ddl: str):
        self.ddl_file = archivo_ddl
    
    def extraer_tablas(self, contenido: str) -> List[Tuple[int, str, str]]:
        tablas = []
        patron = r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+|[a-zA-Z0-9_]+)\s*\('
        
        for i, linea in enumerate(contenido.split('\n'), 1):
            match = re.search(patron, linea, re.IGNORECASE)
            if match:
                tabla_completa = match.group(1)
                if '.' in tabla_completa:
                    esquema, tabla = tabla_completa.split('.')
                else:
                    esquema = 'public'
                    tabla = tabla_completa
                tablas.append((i, esquema, tabla))
        
        return tablas
    
    def extraer_columnas(self, contenido: str) -> List[Tuple[int, str, str, str, str]]:
        columnas = []
        lineas = contenido.split('\n')
        
        tabla_actual = None
        esquema_actual = None
        dentro_create_table = False
        
        for i, linea in enumerate(lineas, 1):
            if re.search(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+|[a-zA-Z0-9_]+)', linea, re.IGNORECASE):
                match = re.search(r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+|[a-zA-Z0-9_]+)', linea, re.IGNORECASE)
                tabla_completa = match.group(1)
                if '.' in tabla_completa:
                    esquema_actual, tabla_actual = tabla_completa.split('.')
                else:
                    esquema_actual = 'public'
                    tabla_actual = tabla_completa
                dentro_create_table = True
                continue
            
            if dentro_create_table and tabla_actual:
                if re.match(r'^\s*\);', linea):
                    dentro_create_table = False
                    tabla_actual = None
                    continue
                
                patron_columna = r'^\s+([a-zA-Z0-9_]+)\s+(character varying|varchar|integer|smallint|bigint|numeric|decimal|text|timestamp|date|boolean|bytea|char|real|double precision|json|jsonb)'
                match = re.match(patron_columna, linea, re.IGNORECASE)
                
                if match:
                    columna = match.group(1)
                    tipo_dato = match.group(2)
                    columnas.append((i, esquema_actual, tabla_actual, columna, tipo_dato))
        
        return columnas
    
    def extraer_constraints(self, contenido: str) -> List[Tuple[int, str, str, str]]:
        constraints = []
        
        patron_pk = r'CONSTRAINT\s+([a-zA-Z0-9_]+)\s+PRIMARY KEY'
        patron_fk = r'CONSTRAINT\s+([a-zA-Z0-9_]+)\s+FOREIGN KEY'
        patron_uk = r'CONSTRAINT\s+([a-zA-Z0-9_]+)\s+UNIQUE'
        patron_ck = r'CONSTRAINT\s+([a-zA-Z0-9_]+)\s+CHECK'
        patron_alter_pk = r'ALTER TABLE.*ADD CONSTRAINT\s+([a-zA-Z0-9_]+)\s+PRIMARY KEY'
        patron_alter_fk = r'ALTER TABLE.*ADD CONSTRAINT\s+([a-zA-Z0-9_]+)\s+FOREIGN KEY'
        
        for i, linea in enumerate(contenido.split('\n'), 1):
            if match := re.search(patron_pk, linea, re.IGNORECASE):
                constraints.append((i, match.group(1), 'PK', 'PRIMARY KEY'))
            elif match := re.search(patron_fk, linea, re.IGNORECASE):
                constraints.append((i, match.group(1), 'FK', 'FOREIGN KEY'))
            elif match := re.search(patron_uk, linea, re.IGNORECASE):
                constraints.append((i, match.group(1), 'UK', 'UNIQUE'))
            elif match := re.search(patron_ck, linea, re.IGNORECASE):
                constraints.append((i, match.group(1), 'CK', 'CHECK'))
            elif match := re.search(patron_alter_pk, linea, re.IGNORECASE):
                constraints.append((i, match.group(1), 'PK', 'PRIMARY KEY'))
            elif match := re.search(patron_alter_fk, linea, re.IGNORECASE):
                constraints.append((i, match.group(1), 'FK', 'FOREIGN KEY'))
        
        return constraints
    
    def extraer_funciones(self, contenido: str) -> List[Tuple[int, str]]:
        funciones = []
        patron = r'CREATE\s+(?:OR REPLACE\s+)?FUNCTION\s+(?:[a-zA-Z0-9_]+\.)?([a-zA-Z0-9_]+)\s*\('
        
        for i, linea in enumerate(contenido.split('\n'), 1):
            match = re.search(patron, linea, re.IGNORECASE)
            if match:
                funciones.append((i, match.group(1)))
        
        return funciones
    
    def extraer_triggers(self, contenido: str) -> List[Tuple[int, str]]:
        triggers = []
        patron = r'CREATE\s+(?:OR REPLACE\s+)?TRIGGER\s+([a-zA-Z0-9_]+)'
        
        for i, linea in enumerate(contenido.split('\n'), 1):
            match = re.search(patron, linea, re.IGNORECASE)
            if match:
                triggers.append((i, match.group(1)))
        
        return triggers
    
    def extraer_indices(self, contenido: str) -> List[Tuple[int, str]]:
        indices = []
        patron = r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF NOT EXISTS\s+)?([a-zA-Z0-9_]+)'
        
        for i, linea in enumerate(contenido.split('\n'), 1):
            match = re.search(patron, linea, re.IGNORECASE)
            if match:
                indices.append((i, match.group(1)))
        
        return indices
    
    def extraer_sequences(self, contenido: str) -> List[Tuple[int, str]]:
        sequences = []
        patron = r'CREATE SEQUENCE\s+(?:IF NOT EXISTS\s+)?(?:[a-zA-Z0-9_]+\.)?([a-zA-Z0-9_]+)'
        
        for i, linea in enumerate(contenido.split('\n'), 1):
            match = re.search(patron, linea, re.IGNORECASE)
            if match:
                sequences.append((i, match.group(1)))
        
        return sequences
    
    def extraer_views(self, contenido: str) -> List[Tuple[int, str]]:
        views = []
        patron = r'CREATE\s+(?:OR REPLACE\s+)?VIEW\s+(?:[a-zA-Z0-9_]+\.)?([a-zA-Z0-9_]+)'
        
        for i, linea in enumerate(contenido.split('\n'), 1):
            match = re.search(patron, linea, re.IGNORECASE)
            if match:
                views.append((i, match.group(1)))
        
        return views
    
    def validar_nombre_tabla(self, linea: int, esquema: str, tabla: str):
        objeto_key = f"tabla:{esquema}.{tabla}"
        if objeto_key in self.objetos_validados:
            return
        self.objetos_validados.add(objeto_key)
        
        reglas_tabla = self.reglas.get('tabla', {})
        tabla_upper = tabla.upper()
        
        max_length = reglas_tabla.get('max_length', 30)
        if len(tabla) > max_length:
            self.errores.append(Error(
                linea=linea,
                tipo_objeto='TABLA',
                nombre_objeto=f"{esquema}.{tabla}",
                tipo_error='LONGITUD',
                mensaje=f"Nombre de tabla demasiado largo ({len(tabla)} caracteres). Máximo: {max_length}",
                valor_actual=tabla,
                valor_sugerido=tabla[:max_length]
            ))
        
        prefijos_validos = reglas_tabla.get('prefijos_validos', [])
        tiene_prefijo = any(tabla_upper.startswith(p + '_') for p in prefijos_validos)
        
        if not tiene_prefijo:
            sugerencia = f"{prefijos_validos[0]}_{tabla_upper}" if prefijos_validos else tabla_upper
            self.errores.append(Error(
                linea=linea,
                tipo_objeto='TABLA',
                nombre_objeto=f"{esquema}.{tabla}",
                tipo_error='PREFIJO',
                mensaje=f"Tabla sin prefijo estándar. Debe iniciar con: {', '.join(prefijos_validos)}",
                valor_actual=tabla,
                valor_sugerido=sugerencia
            ))
    
    def sugerir_prefijo_columna(self, tipo_dato: str) -> str:
        if not tipo_dato:
            return 'N'
        
        tipo_upper = tipo_dato.upper()
        prefijos = self.reglas.get('columna', {}).get('prefijos_tipo_dato', {})
        
        for tipo_key, prefijo in prefijos.items():
            if tipo_upper.startswith(tipo_key):
                return prefijo
        
        return 'N'
    
    def validar_nombre_columna(self, linea: int, esquema: str, tabla: str, columna: str, tipo_dato: str):
        objeto_key = f"columna:{esquema}.{tabla}.{columna}"
        if objeto_key in self.objetos_validados:
            return
        self.objetos_validados.add(objeto_key)
        
        reglas_columna = self.reglas.get('columna', {})
        columna_upper = columna.upper()
        
        max_length = reglas_columna.get('max_length', 30)
        if len(columna) > max_length:
            self.errores.append(Error(
                linea=linea,
                tipo_objeto='COLUMNA',
                nombre_objeto=f"{tabla}.{columna}",
                tipo_error='LONGITUD',
                mensaje=f"Nombre de columna demasiado largo ({len(columna)} caracteres). Máximo: {max_length}",
                valor_actual=columna,
                valor_sugerido=columna[:max_length]
            ))
        
        prefijo_esperado = self.sugerir_prefijo_columna(tipo_dato)
        if not columna_upper.startswith(prefijo_esperado + '_'):
            partes = columna_upper.split('_', 1)
            sugerencia = f"{prefijo_esperado}_{partes[1] if len(partes) > 1 else columna_upper}"
            prefijo_actual = columna.split('_')[0] if '_' in columna else 'sin prefijo'
            
            self.errores.append(Error(
                linea=linea,
                tipo_objeto='COLUMNA',
                nombre_objeto=f"{tabla}.{columna}",
                tipo_error='PREFIJO',
                mensaje=f"Prefijo incorrecto '{prefijo_actual}'. Para tipo '{tipo_dato}' debe usar '{prefijo_esperado}_'",
                valor_actual=columna,
                valor_sugerido=sugerencia
            ))
    
    def validar_constraint(self, linea: int, nombre: str, tipo: str, descripcion: str):
        objeto_key = f"constraint:{nombre}"
        if objeto_key in self.objetos_validados:
            return
        self.objetos_validados.add(objeto_key)
        
        reglas_constraint = self.reglas.get('constraint', {})
        nombre_upper = nombre.upper()
        
        prefijo_esperado = reglas_constraint.get('prefijo', 'CST_')
        if not nombre_upper.startswith(prefijo_esperado):
            sugerencia = f"{prefijo_esperado}{nombre_upper}"
            self.errores.append(Error(
                linea=linea,
                tipo_objeto='CONSTRAINT',
                nombre_objeto=nombre,
                tipo_error='PREFIJO',
                mensaje=f"Constraint debe iniciar con '{prefijo_esperado}'",
                valor_actual=nombre,
                valor_sugerido=sugerencia
            ))
        
        regex_nombre = reglas_constraint.get('regex_nombre')
        if regex_nombre and not re.match(regex_nombre, nombre_upper):
            formato = reglas_constraint.get('formato', '')
            self.warnings.append(Error(
                linea=linea,
                tipo_objeto='CONSTRAINT',
                nombre_objeto=nombre,
                tipo_error='FORMATO',
                mensaje=f"No cumple formato esperado: {formato}",
                valor_actual=nombre
            ))
    
    def validar_funcion(self, linea: int, nombre: str):
        objeto_key = f"funcion:{nombre}"
        if objeto_key in self.objetos_validados:
            return
        self.objetos_validados.add(objeto_key)
        
        reglas_function = self.reglas.get('function', {})
        nombre_upper = nombre.upper()
        
        prefijo_esperado = reglas_function.get('prefijo', 'FN_')
        if not nombre_upper.startswith(prefijo_esperado):
            sugerencia = f"{prefijo_esperado}{nombre_upper}"
            self.errores.append(Error(
                linea=linea,
                tipo_objeto='FUNCTION',
                nombre_objeto=nombre,
                tipo_error='PREFIJO',
                mensaje=f"Función debe iniciar con '{prefijo_esperado}'",
                valor_actual=nombre,
                valor_sugerido=sugerencia
            ))
    
    def validar_trigger(self, linea: int, nombre: str):
        objeto_key = f"trigger:{nombre}"
        if objeto_key in self.objetos_validados:
            return
        self.objetos_validados.add(objeto_key)
        
        reglas_trigger = self.reglas.get('trigger', {})
        nombre_upper = nombre.upper()
        
        prefijo_esperado = reglas_trigger.get('prefijo', 'TRG_')
        if not nombre_upper.startswith(prefijo_esperado):
            sugerencia = f"{prefijo_esperado}{nombre_upper}"
            self.errores.append(Error(
                linea=linea,
                tipo_objeto='TRIGGER',
                nombre_objeto=nombre,
                tipo_error='PREFIJO',
                mensaje=f"Trigger debe iniciar con '{prefijo_esperado}'",
                valor_actual=nombre,
                valor_sugerido=sugerencia
            ))
        
        tipos_validos = reglas_trigger.get('tipos_validos', [])
        tiene_tipo = any(f"_{tipo}" in nombre_upper for tipo in tipos_validos)
        
        if not tiene_tipo:
            self.warnings.append(Error(
                linea=linea,
                tipo_objeto='TRIGGER',
                nombre_objeto=nombre,
                tipo_error='TIPO',
                mensaje=f"Trigger no especifica tipo. Tipos válidos: {', '.join(tipos_validos)}",
                valor_actual=nombre
            ))
    
    def validar_indice(self, linea: int, nombre: str):
        objeto_key = f"index:{nombre}"
        if objeto_key in self.objetos_validados:
            return
        self.objetos_validados.add(objeto_key)
        
        reglas_index = self.reglas.get('index', {})
        nombre_upper = nombre.upper()
        
        prefijo_esperado = reglas_index.get('prefijo', 'INX_')
        if not nombre_upper.startswith(prefijo_esperado):
            sugerencia = f"{prefijo_esperado}{nombre_upper}"
            self.errores.append(Error(
                linea=linea,
                tipo_objeto='INDEX',
                nombre_objeto=nombre,
                tipo_error='PREFIJO',
                mensaje=f"Índice debe iniciar con '{prefijo_esperado}'",
                valor_actual=nombre,
                valor_sugerido=sugerencia
            ))
    
    def validar_sequence(self, linea: int, nombre: str):
        objeto_key = f"sequence:{nombre}"
        if objeto_key in self.objetos_validados:
            return
        self.objetos_validados.add(objeto_key)
        
        reglas_sequence = self.reglas.get('sequence', {})
        nombre_upper = nombre.upper()
        
        prefijo_esperado = reglas_sequence.get('prefijo', 'SQ_')
        if not nombre_upper.startswith(prefijo_esperado):
            sugerencia = f"{prefijo_esperado}{nombre_upper}"
            self.errores.append(Error(
                linea=linea,
                tipo_objeto='SEQUENCE',
                nombre_objeto=nombre,
                tipo_error='PREFIJO',
                mensaje=f"Secuencia debe iniciar con '{prefijo_esperado}'",
                valor_actual=nombre,
                valor_sugerido=sugerencia
            ))
    
    def validar_view(self, linea: int, nombre: str):
        objeto_key = f"view:{nombre}"
        if objeto_key in self.objetos_validados:
            return
        self.objetos_validados.add(objeto_key)
        
        reglas_view = self.reglas.get('view', {})
        nombre_upper = nombre.upper()
        
        prefijo_esperado = reglas_view.get('prefijo', 'VW_')
        if not nombre_upper.startswith(prefijo_esperado):
            sugerencia = f"{prefijo_esperado}{nombre_upper}"
            self.errores.append(Error(
                linea=linea,
                tipo_objeto='VIEW',
                nombre_objeto=nombre,
                tipo_error='PREFIJO',
                mensaje=f"Vista debe iniciar con '{prefijo_esperado}'",
                valor_actual=nombre,
                valor_sugerido=sugerencia
            ))
    
    def validar(self) -> bool:
        self.cargar_reglas()
        
        if not self.ddl_file:
            raise ValueError("No se ha especificado un archivo DDL")
        
        with open(self.ddl_file, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        tablas = self.extraer_tablas(contenido)
        for linea, esquema, tabla in tablas:
            self.validar_nombre_tabla(linea, esquema, tabla)
        
        columnas = self.extraer_columnas(contenido)
        for linea, esquema, tabla, columna, tipo_dato in columnas:
            self.validar_nombre_columna(linea, esquema, tabla, columna, tipo_dato)
        
        constraints = self.extraer_constraints(contenido)
        for linea, nombre, tipo, descripcion in constraints:
            self.validar_constraint(linea, nombre, tipo, descripcion)
        
        funciones = self.extraer_funciones(contenido)
        for linea, nombre in funciones:
            self.validar_funcion(linea, nombre)
        
        triggers = self.extraer_triggers(contenido)
        for linea, nombre in triggers:
            self.validar_trigger(linea, nombre)
        
        indices = self.extraer_indices(contenido)
        for linea, nombre in indices:
            self.validar_indice(linea, nombre)
        
        sequences = self.extraer_sequences(contenido)
        for linea, nombre in sequences:
            self.validar_sequence(linea, nombre)
        
        views = self.extraer_views(contenido)
        for linea, nombre in views:
            self.validar_view(linea, nombre)
        
        return len(self.errores) == 0
    
    def generar_reporte(self, archivo_salida: str):
        with open(archivo_salida, 'w', encoding='utf-8') as f:
            f.write("=" * 100 + "\n")
            f.write("REPORTE DE VALIDACIÓN DE NOMENCLATURA - DDL PostgreSQL\n")
            f.write("=" * 100 + "\n\n")
            
            f.write(f"Archivo DDL analizado: {self.ddl_file}\n")
            f.write(f"Reglas aplicadas: {self.reglas_json}\n")
            f.write(f"Total de errores críticos: {len(self.errores)}\n")
            f.write(f"Total de advertencias: {len(self.warnings)}\n\n")
            
            if self.errores:
                f.write("=" * 100 + "\n")
                f.write("ERRORES\n")
                f.write("=" * 100 + "\n\n")
                
                errores_por_tipo = defaultdict(list)
                for error in self.errores:
                    errores_por_tipo[error.tipo_objeto].append(error)
                
                for tipo_objeto in sorted(errores_por_tipo.keys()):
                    errores = errores_por_tipo[tipo_objeto]
                    f.write(f"\n### {tipo_objeto} ({len(errores)} errores)\n\n")
                    
                    for idx, error in enumerate(errores, 1):
                        f.write(f"{idx}. Línea {error.linea} | {error.tipo_error}\n")
                        f.write(f"   Objeto: {error.nombre_objeto}\n")
                        f.write(f"   Problema: {error.mensaje}\n")
                        f.write(f"   Valor actual: '{error.valor_actual}'\n")
                        if error.valor_sugerido:
                            f.write(f"    Sugerencia: '{error.valor_sugerido}'\n")
                        f.write("\n")
            
            if self.warnings:
                f.write("=" * 100 + "\n")
                f.write("ADVERTENCIAS (revisar)\n")
                f.write("=" * 100 + "\n\n")
                
                for idx, warning in enumerate(self.warnings, 1):
                    f.write(f"{idx}. Línea {warning.linea} | {warning.tipo_objeto}\n")
                    f.write(f"   Objeto: {warning.nombre_objeto}\n")
                    f.write(f"   Detalle: {warning.mensaje}\n")
                    f.write(f"   Valor: '{warning.valor_actual}'\n")
                    f.write("\n")
            
            if not self.errores and not self.warnings:
                f.write("\n" + "=" * 100 + "\n")
                f.write(" VALIDACIÓN EXITOSA - No se encontraron errores ni advertencias\n")
                f.write("=" * 100 + "\n")



def main():
    import sys

    if len(sys.argv) != 7:
        print("Error: Se requieren 6 parametros")
        print("Uso: python validar_nomenclatura.py <host> <puerto> <bd> <usuario> <password> <ruta_salida_ddl_completo>")
        sys.exit(1)
    
    host = sys.argv[1]
    puerto = sys.argv[2]
    bd = sys.argv[3]
    usuario = sys.argv[4]
    password = sys.argv[5]
    ruta_salida = sys.argv[6]
    
    # Asegurar que las impresiones no fallen en consolas Windows con codificación cp1252
    try:
        # Python 3.7+ permite reconfigure
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        # Fallback: envolver print para manejar UnicodeEncodeError usando reemplazo
        _orig_print = builtins.print

        def _safe_print(*args, **kwargs):
            try:
                _orig_print(*args, **kwargs)
            except UnicodeEncodeError:
                # Construir texto y escribir con reemplazo de caracteres no representables
                file = kwargs.get('file', sys.stdout)
                sep = kwargs.get('sep', ' ')
                end = kwargs.get('end', '\n')
                text = sep.join(str(a) for a in args) + end
                enc = getattr(file, 'encoding', None) or 'utf-8'
                try:
                    # Intentar escribir en buffer si está disponible (stdout/stderr reales)
                    if hasattr(file, 'buffer'):
                        file.buffer.write(text.encode(enc, errors='replace'))
                    else:
                        file.write(text.encode(enc, errors='replace').decode(enc))
                except Exception:
                    # Último recurso: usar original print con safe-encoding via utf-8 replacement
                    _orig_print(text.encode('utf-8', errors='replace').decode('utf-8'))

        builtins.print = _safe_print

    print(f"Iniciando validacion de nomenclatura...")
    print(f"Host: {host}")
    print(f"Puerto: {puerto}")
    print(f"Base de datos: {bd}")
    print(f"Usuario: {usuario}")
    print(f"Archivo de salida: {ruta_salida}")
    
    base_dir = Path(__file__).resolve().parent
    reglas_json = base_dir.parent / 'resources' / 'reglas_nomenclatura.json'
    validador = ValidadorDDL(str(reglas_json))
    
    print(f"\nGenerando DDL desde base de datos...")
    if not validador.generar_ddl_desde_bd(host, puerto, usuario, bd, ruta_salida, password):
        print("\n✗ Error al generar DDL")
        sys.exit(1)
    
    print("DDL generado...")
    
    print("\nValidando nomenclatura...")
    try:
        es_valido = validador.validar()
        
        print(f"\nResultado: {'VALIDO' if es_valido else 'ERRORES ENCONTRADOS'}")
        print(f"Errores: {len(validador.errores)}")
        print(f"Advertencias: {len(validador.warnings)}")
        
        reporte = ruta_salida.replace('.sql', '_nomenclatura.txt')
        validador.generar_reporte(reporte)
        
        print(f"\nDDL completo generado en: {ruta_salida}")
        print(f"Reporte de validacion: {reporte}")
        
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error durante la validacion: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
