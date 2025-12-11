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

    def _buscar_pg_dump(self):
        """Busca pg_dump en ubicaciones comunes de Windows"""
        import os
        import glob
        if os.system('pg_dump --version > nul 2>&1') == 0:
            return 'pg_dump'
        posibles_rutas = [
            r'C:\Program Files\PostgreSQL\*\bin\pg_dump.exe',
            r'C:\Program Files (x86)\PostgreSQL\*\bin\pg_dump.exe',
            r'C:\PostgreSQL\*\bin\pg_dump.exe',
        ]
        for patron in posibles_rutas:
            rutas = glob.glob(patron)
            if rutas:
                rutas.sort(reverse=True)
                return rutas[0]
        return None

    def generar_ddl_desde_bd(self, host: str, puerto: str, usuario: str, base_datos: str, archivo_salida: str, password: str = None):
        pg_dump_path = self._buscar_pg_dump()
        if not pg_dump_path:
            print("Error: pg_dump no está instalado o no está en el PATH")
            print("Instale PostgreSQL o agregue la carpeta 'bin' de PostgreSQL al PATH del sistema")
            print("Ejemplo: C:\\Program Files\\PostgreSQL\\16\\bin")
            return False
        comando = [
            pg_dump_path,
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
        pk_rules = reglas_columna.get('pk', {})
        sufijo_pk = pk_rules.get('sufijo_pk', '_PK')
        if len(columna) > max_length:
            valor_sugerido = None
            if sufijo_pk and columna_upper.endswith(sufijo_pk.upper()):
                sufijo_real = columna[-len(sufijo_pk):]
                longitud_base = max_length - len(sufijo_pk)
                base_recortada = columna[:-len(sufijo_pk)][:max(longitud_base, 0)]
                valor_sugerido = f"{base_recortada}{sufijo_real}"
            else:
                valor_sugerido = columna[:max_length]
            self.errores.append(Error(
                linea=linea,
                tipo_objeto='COLUMNA',
                nombre_objeto=f"{tabla}.{columna}",
                tipo_error='LONGITUD',
                mensaje=f"Nombre de columna demasiado largo ({len(columna)} caracteres). Máximo: {max_length}",
                valor_actual=columna,
                valor_sugerido=valor_sugerido
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
        """Genera reporte en formato HTML profesional"""
        from datetime import datetime
        archivo_html = archivo_salida.replace('.txt', '.html')
        total_errores = len(self.errores)
        total_warnings = len(self.warnings)
        total_problemas = total_errores + total_warnings
        errores_por_tipo = defaultdict(list)
        for error in self.errores:
            errores_por_tipo[error.tipo_objeto].append(error)
        warnings_por_tipo = defaultdict(list)
        for warning in self.warnings:
            warnings_por_tipo[warning.tipo_objeto].append(warning)
        estado = "[OK] EXITOSA" if total_problemas == 0 else "[ERROR] CON ERRORES"
        color_estado = "#27ae60" if total_problemas == 0 else "#e74c3c"
        html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Validación de Nomenclatura</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        .header p {{
            font-size: 1.1em;
            opacity: 0.9;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .summary-card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border-left: 5px solid #3498db;
            transition: transform 0.2s;
        }}
        .summary-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.15);
        }}
        .summary-card.error {{
            border-left-color: #e74c3c;
        }}
        .summary-card.warning {{
            border-left-color: #f39c12;
        }}
        .summary-card.success {{
            border-left-color: #27ae60;
        }}
        .summary-card h3 {{
            color: #7f8c8d;
            font-size: 0.9em;
            text-transform: uppercase;
            margin-bottom: 10px;
        }}
        .summary-card .value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #2c3e50;
        }}
        .status {{
            padding: 30px;
            text-align: center;
            background: {color_estado};
            color: white;
        }}
        .status h2 {{
            font-size: 2em;
            margin-bottom: 10px;
        }}
        .content {{
            padding: 30px;
        }}
        .info-table {{
            width: 100%;
            margin-bottom: 30px;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .info-table th {{
            background: #34495e;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        .info-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #ecf0f1;
        }}
        .info-table tr:last-child td {{
            border-bottom: none;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section-title {{
            font-size: 1.8em;
            color: #2c3e50;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #3498db;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .section-title.error {{
            border-bottom-color: #e74c3c;
        }}
        .section-title.warning {{
            border-bottom-color: #f39c12;
        }}
        .badge {{
            background: #3498db;
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.7em;
            font-weight: bold;
        }}
        .badge.error {{
            background: #e74c3c;
        }}
        .badge.warning {{
            background: #f39c12;
        }}
        .subsection {{
            margin-bottom: 30px;
        }}
        .subsection-title {{
            background: #ecf0f1;
            padding: 15px 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            font-weight: bold;
            color: #34495e;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .error-item, .warning-item {{
            background: white;
            border: 1px solid #e0e0e0;
            border-left: 4px solid #e74c3c;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            transition: all 0.2s;
        }}
        .error-item:hover, .warning-item:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transform: translateX(5px);
        }}
        .warning-item {{
            border-left-color: #f39c12;
        }}
        .error-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        .error-title {{
            font-weight: bold;
            color: #2c3e50;
            font-size: 1.1em;
        }}
        .line-number {{
            background: #34495e;
            color: white;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 0.9em;
            font-family: 'Courier New', monospace;
        }}
        .error-details {{
            margin-top: 12px;
        }}
        .detail-row {{
            display: grid;
            grid-template-columns: 120px 1fr;
            gap: 10px;
            margin-bottom: 8px;
        }}
        .detail-label {{
            color: #7f8c8d;
            font-weight: 600;
        }}
        .detail-value {{
            color: #34495e;
        }}
        .code {{
            background: #f8f9fa;
            padding: 4px 8px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.95em;
            border: 1px solid #e0e0e0;
        }}
        .suggestion {{
            background: #d5f4e6;
            color: #27ae60;
            padding: 4px 8px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.95em;
            border: 1px solid #a9dfbf;
        }}
        .success-message {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            padding: 40px;
            text-align: center;
            border-radius: 10px;
            font-size: 1.3em;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }}
        .footer {{
            background: #2c3e50;
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 0.9em;
        }}
        .chart-container {{
            margin: 30px 0;
            padding: 20px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        .stat-item {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }}
        .stat-label {{
            color: #7f8c8d;
            margin-top: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Reporte de Validación de Nomenclatura</h1>
            <p>Análisis DDL PostgreSQL - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        </div>
        <div class="summary">
            <div class="summary-card {'error' if total_errores > 0 else 'success'}">
                <h3>Errores Críticos</h3>
                <div class="value" style="color: {'#e74c3c' if total_errores > 0 else '#27ae60'};">{total_errores}</div>
            </div>
            <div class="summary-card warning">
                <h3>Advertencias</h3>
                <div class="value" style="color: #f39c12;">{total_warnings}</div>
            </div>
            <div class="summary-card">
                <h3>Total Problemas</h3>
                <div class="value">{total_problemas}</div>
            </div>
        </div>
        <div class="status">
            <h2>{estado}</h2>
            <p>Validación de nomenclatura completada</p>
        </div>
        <div class="content">
            <table class="info-table">
                <tr>
                    <th>Archivo DDL</th>
                    <td>{self.ddl_file}</td>
                </tr>
                <tr>
                    <th>Archivo de Reglas</th>
                    <td>{self.reglas_json}</td>
                </tr>
                <tr>
                    <th>Fecha de Análisis</th>
                    <td>{datetime.now().strftime('%d de %B de %Y, %H:%M:%S')}</td>
                </tr>
            </table>
"""
        if self.errores:
            html += f"""
            <div class="section">
                <h2 class="section-title error">
                    Errores Críticos
                    <span class="badge error">{total_errores}</span>
                </h2>
"""
            for tipo_objeto in sorted(errores_por_tipo.keys()):
                errores = errores_por_tipo[tipo_objeto]
                html += f"""
                <div class="subsection">
                    <div class="subsection-title">
                        <span>{tipo_objeto}</span>
                        <span class="badge error">{len(errores)} error{'es' if len(errores) > 1 else ''}</span>
                    </div>
"""
                for idx, error in enumerate(errores, 1):
                    html += f"""
                    <div class="error-item">
                        <div class="error-header">
                            <div class="error-title">#{idx} - {error.tipo_error}</div>
                            <div class="line-number">Línea {error.linea}</div>
                        </div>
                        <div class="error-details">
                            <div class="detail-row">
                                <div class="detail-label">Objeto:</div>
                                <div class="detail-value"><strong>{error.nombre_objeto}</strong></div>
                            </div>
                            <div class="detail-row">
                                <div class="detail-label">Problema:</div>
                                <div class="detail-value">{error.mensaje}</div>
                            </div>
                            <div class="detail-row">
                                <div class="detail-label">Valor Actual:</div>
                                <div class="detail-value"><span class="code">{error.valor_actual}</span></div>
                            </div>
"""
                    if error.valor_sugerido:
                        html += f"""
                            <div class="detail-row">
                                <div class="detail-label">Sugerencia:</div>
                                <div class="detail-value"><span class="suggestion">{error.valor_sugerido}</span></div>
                            </div>
"""
                    html += """
                        </div>
                    </div>
"""
                html += """
                </div>
"""
            html += """
            </div>
"""
        if self.warnings:
            html += f"""
            <div class="section">
                <h2 class="section-title warning">
                    Advertencias
                    <span class="badge warning">{total_warnings}</span>
                </h2>
"""
            for idx, warning in enumerate(self.warnings, 1):
                html += f"""
                <div class="warning-item">
                    <div class="error-header">
                        <div class="error-title">#{idx} - {warning.tipo_objeto}</div>
                        <div class="line-number">Línea {warning.linea}</div>
                    </div>
                    <div class="error-details">
                        <div class="detail-row">
                            <div class="detail-label">Objeto:</div>
                            <div class="detail-value"><strong>{warning.nombre_objeto}</strong></div>
                        </div>
                        <div class="detail-row">
                            <div class="detail-label">Detalle:</div>
                            <div class="detail-value">{warning.mensaje}</div>
                        </div>
                        <div class="detail-row">
                            <div class="detail-label">Valor:</div>
                            <div class="detail-value"><span class="code">{warning.valor_actual}</span></div>
                        </div>
                    </div>
                </div>
"""
            html += """
            </div>
"""
        if not self.errores and not self.warnings:
            html += """
            <div class="success-message">
                <h2>¡Validación Exitosa!</h2>
                <p>No se encontraron errores ni advertencias en el análisis de nomenclatura.</p>
                <p>Todos los objetos cumplen con las reglas establecidas.</p>
            </div>
"""
        if errores_por_tipo or warnings_por_tipo:
            html += """
            <div class="chart-container">
                <h3 style="margin-bottom: 15px; color: #2c3e50;">Estadísticas por Tipo de Objeto</h3>
                <div class="stats-grid">
"""
            todos_tipos = set(list(errores_por_tipo.keys()) + list(warnings_por_tipo.keys()))
            for tipo in sorted(todos_tipos):
                num_errores = len(errores_por_tipo.get(tipo, []))
                num_warnings = len(warnings_por_tipo.get(tipo, []))
                total = num_errores + num_warnings
                html += f"""
                    <div class="stat-item">
                        <div class="stat-number">{total}</div>
                        <div class="stat-label">{tipo}</div>
                        <div style="font-size: 0.85em; color: #95a5a6; margin-top: 5px;">
                            {num_errores} errores, {num_warnings} advertencias
                        </div>
                    </div>
"""
            html += """
                </div>
            </div>
"""
        html += f"""
        </div>
        <div class="footer">
            <p>📄 Reporte generado automáticamente por DB Manager</p>
            <p style="margin-top: 10px; opacity: 0.8;">Arquitectura de Base de Datos - {datetime.now().year}</p>
        </div>
    </div>
</body>
</html>
"""
        with open(archivo_html, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"[OK] Reporte HTML generado: {archivo_html}")

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
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        _orig_print = builtins.print

        def _safe_print(*args, **kwargs):
            try:
                _orig_print(*args, **kwargs)
            except UnicodeEncodeError:
                file = kwargs.get('file', sys.stdout)
                sep = kwargs.get('sep', ' ')
                end = kwargs.get('end', '\n')
                text = sep.join(str(a) for a in args) + end
                enc = getattr(file, 'encoding', None) or 'utf-8'
                try:
                    if hasattr(file, 'buffer'):
                        file.buffer.write(text.encode(enc, errors='replace'))
                    else:
                        file.write(text.encode(enc, errors='replace').decode(enc))
                except Exception:
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
        print("\n[ERROR] Error al generar DDL")
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
        print(f"\n[ERROR] Error durante la validacion: {e}")
        sys.exit(1)
if __name__ == "__main__":
    main()
