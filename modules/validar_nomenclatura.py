import json
import os
import re
import subprocess
import sys
import builtins
import tempfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path

class Error:

    def __init__(self, linea, tipo_objeto, nombre_objeto, tipo_error, mensaje,
                 valor_actual, valor_sugerido=None):
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

    _RE_TABLA = re.compile(
        r'CREATE TABLE\s+(?:IF NOT EXISTS\s+)?([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)?)\s*\(',
        re.IGNORECASE,
    )
    _RE_COLUMNA = re.compile(
        r'^\s+([a-zA-Z0-9_]+)\s+'
        r'(character varying|varchar|integer|smallint|bigint|numeric|decimal|text|'
        r'timestamp|date|boolean|bytea|char|real|double precision|json|jsonb)',
        re.IGNORECASE,
    )

    def __init__(self, reglas_json):
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
        import glob
        if os.system('pg_dump --version > nul 2>&1') == 0:
            return 'pg_dump'
        candidatos = [
            r'C:\Program Files\PostgreSQL\*\bin\pg_dump.exe',
            r'C:\Program Files (x86)\PostgreSQL\*\bin\pg_dump.exe',
            r'C:\PostgreSQL\*\bin\pg_dump.exe',
        ]
        for patron in candidatos:
            rutas = sorted(glob.glob(patron), reverse=True)
            if rutas:
                return rutas[0]
        return None

    def generar_ddl_desde_bd(self, host, puerto, usuario, base_datos,
                              archivo_salida, password=None):
        pg = self._buscar_pg_dump()
        if not pg:
            print("Error: pg_dump no encontrado. Instale PostgreSQL o agréguelo al PATH.")
            return False
        env = {**os.environ, 'PGPASSWORD': password} if password else os.environ.copy()
        try:
            subprocess.run(
                [pg, '-h', host, '-p', str(puerto), '-U', usuario,
                 '-d', base_datos, '-s', '--no-owner', '--no-privileges',
                 '-f', archivo_salida],
                env=env, capture_output=True, text=True, check=True,
            )
            self.ddl_file = archivo_salida
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error al ejecutar pg_dump: {e.stderr}")
        except FileNotFoundError:
            print("Error: pg_dump no encontrado.")
        return False

    def cargar_ddl_existente(self, archivo_ddl):
        self.ddl_file = archivo_ddl

    @staticmethod
    def _split_nombre(nombre_completo):
        """'esquema.tabla' → ('esquema','tabla'), 'tabla' → ('public','tabla')."""
        return tuple(nombre_completo.split('.', 1)) if '.' in nombre_completo \
               else ('public', nombre_completo)

    @staticmethod
    def _extraer_simple(contenido, patron):
        """Retorna [(num_linea, nombre)] para un patrón con un grupo capturado."""
        rx = re.compile(patron, re.IGNORECASE)
        return [
            (i, m.group(1))
            for i, linea in enumerate(contenido.split('\n'), 1)
            if (m := rx.search(linea))
        ]

    def extraer_tablas(self, contenido):
        return [
            (i, *self._split_nombre(m.group(1)))
            for i, linea in enumerate(contenido.split('\n'), 1)
            if (m := self._RE_TABLA.search(linea))
        ]

    def extraer_columnas(self, contenido):
        columnas, esquema, tabla, dentro = [], None, None, False
        for i, linea in enumerate(contenido.split('\n'), 1):
            if m := self._RE_TABLA.search(linea):
                esquema, tabla = self._split_nombre(m.group(1))
                dentro = True
            elif dentro and re.match(r'^\s*\);', linea):
                dentro = False
                esquema = tabla = None
            elif dentro:
                if m := self._RE_COLUMNA.match(linea):
                    columnas.append((i, esquema, tabla, m.group(1), m.group(2)))
        return columnas

    def extraer_constraints(self, contenido):
        patrones = [
            (r'CONSTRAINT\s+([a-zA-Z0-9_]+)\s+PRIMARY KEY',                  'PK', 'PRIMARY KEY'),
            (r'CONSTRAINT\s+([a-zA-Z0-9_]+)\s+FOREIGN KEY',                  'FK', 'FOREIGN KEY'),
            (r'CONSTRAINT\s+([a-zA-Z0-9_]+)\s+UNIQUE',                       'UK', 'UNIQUE'),
            (r'CONSTRAINT\s+([a-zA-Z0-9_]+)\s+CHECK',                        'CK', 'CHECK'),
            (r'ALTER TABLE.*ADD CONSTRAINT\s+([a-zA-Z0-9_]+)\s+PRIMARY KEY', 'PK', 'PRIMARY KEY'),
            (r'ALTER TABLE.*ADD CONSTRAINT\s+([a-zA-Z0-9_]+)\s+FOREIGN KEY', 'FK', 'FOREIGN KEY'),
        ]
        constraints = []
        for i, linea in enumerate(contenido.split('\n'), 1):
            for patron, tipo, desc in patrones:
                if m := re.search(patron, linea, re.IGNORECASE):
                    constraints.append((i, m.group(1), tipo, desc))
                    break
        return constraints

    def extraer_funciones(self, contenido):
        return self._extraer_simple(contenido,
            r'CREATE\s+(?:OR REPLACE\s+)?FUNCTION\s+(?:[a-zA-Z0-9_]+\.)?([a-zA-Z0-9_]+)\s*\(')

    def extraer_triggers(self, contenido):
        return self._extraer_simple(contenido,
            r'CREATE\s+(?:OR REPLACE\s+)?TRIGGER\s+([a-zA-Z0-9_]+)')

    def extraer_indices(self, contenido):
        return self._extraer_simple(contenido,
            r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF NOT EXISTS\s+)?([a-zA-Z0-9_]+)')

    def extraer_sequences(self, contenido):
        return self._extraer_simple(contenido,
            r'CREATE SEQUENCE\s+(?:IF NOT EXISTS\s+)?(?:[a-zA-Z0-9_]+\.)?([a-zA-Z0-9_]+)')

    def extraer_views(self, contenido):
        return self._extraer_simple(contenido,
            r'CREATE\s+(?:OR REPLACE\s+)?VIEW\s+(?:[a-zA-Z0-9_]+\.)?([a-zA-Z0-9_]+)')

    def _ya_validado(self, clave):
        if clave in self.objetos_validados:
            return True
        self.objetos_validados.add(clave)
        return False

    def _add_error_prefijo(self, linea, tipo_str, nombre_obj, nombre, prefijo):
        self.errores.append(Error(
            linea=linea, tipo_objeto=tipo_str, nombre_objeto=nombre_obj,
            tipo_error='PREFIJO',
            mensaje=f"{tipo_str} debe iniciar con '{prefijo}'",
            valor_actual=nombre,
            valor_sugerido=f"{prefijo}{nombre.upper()}",
        ))

    def _validar_prefijo_simple(self, linea, nombre, tipo_str, regla_key, prefijo_default):
        """Valida prefijo para objetos simples. Retorna False si ya estaba validado."""
        if self._ya_validado(f"{regla_key}:{nombre}"):
            return False
        prefijo = self.reglas.get(regla_key, {}).get('prefijo', prefijo_default)
        if not nombre.upper().startswith(prefijo):
            self._add_error_prefijo(linea, tipo_str, nombre, nombre, prefijo)
        return True

    def validar_nombre_tabla(self, linea, esquema, tabla):
        if self._ya_validado(f"tabla:{esquema}.{tabla}"):
            return
        reglas = self.reglas.get('tabla', {})
        tabla_up = tabla.upper()
        nombre_obj = f"{esquema}.{tabla}"
        max_len = reglas.get('max_length', 30)
        if len(tabla) > max_len:
            self.errores.append(Error(
                linea=linea, tipo_objeto='TABLA', nombre_objeto=nombre_obj,
                tipo_error='LONGITUD',
                mensaje=f"Nombre demasiado largo ({len(tabla)} chars). Máximo: {max_len}",
                valor_actual=tabla, valor_sugerido=tabla[:max_len],
            ))
        prefijos = reglas.get('prefijos_validos', [])
        if not any(tabla_up.startswith(p + '_') for p in prefijos):
            sugerencia = f"{prefijos[0]}_{tabla_up}" if prefijos else tabla_up
            self.errores.append(Error(
                linea=linea, tipo_objeto='TABLA', nombre_objeto=nombre_obj,
                tipo_error='PREFIJO',
                mensaje=f"Sin prefijo estándar. Usar: {', '.join(prefijos)}",
                valor_actual=tabla, valor_sugerido=sugerencia,
            ))

    def sugerir_prefijo_columna(self, tipo_dato):
        if not tipo_dato:
            return 'N'
        prefijos = self.reglas.get('columna', {}).get('prefijos_tipo_dato', {})
        tipo_up = tipo_dato.upper()
        return next((p for t, p in prefijos.items() if tipo_up.startswith(t)), 'N')

    def validar_nombre_columna(self, linea, esquema, tabla, columna, tipo_dato):
        if self._ya_validado(f"columna:{esquema}.{tabla}.{columna}"):
            return
        reglas = self.reglas.get('columna', {})
        col_up = columna.upper()
        nombre_obj = f"{tabla}.{columna}"
        max_len = reglas.get('max_length', 30)
        sufijo_pk = reglas.get('pk', {}).get('sufijo_pk', '_PK')
        if len(columna) > max_len:
            if sufijo_pk and col_up.endswith(sufijo_pk.upper()):
                base = columna[:-len(sufijo_pk)][:max(max_len - len(sufijo_pk), 0)]
                sugerido = f"{base}{columna[-len(sufijo_pk):]}"
            else:
                sugerido = columna[:max_len]
            self.errores.append(Error(
                linea=linea, tipo_objeto='COLUMNA', nombre_objeto=nombre_obj,
                tipo_error='LONGITUD',
                mensaje=f"Nombre demasiado largo ({len(columna)} chars). Máximo: {max_len}",
                valor_actual=columna, valor_sugerido=sugerido,
            ))
        prefijo_esp = self.sugerir_prefijo_columna(tipo_dato)
        if not col_up.startswith(prefijo_esp + '_'):
            partes = col_up.split('_', 1)
            sugerencia = f"{prefijo_esp}_{partes[1] if len(partes) > 1 else col_up}"
            pref_actual = columna.split('_')[0] if '_' in columna else 'sin prefijo'
            self.errores.append(Error(
                linea=linea, tipo_objeto='COLUMNA', nombre_objeto=nombre_obj,
                tipo_error='PREFIJO',
                mensaje=f"Prefijo '{pref_actual}' incorrecto. Para '{tipo_dato}' usar '{prefijo_esp}_'",
                valor_actual=columna, valor_sugerido=sugerencia,
            ))

    def validar_constraint(self, linea, nombre):
        if self._ya_validado(f"constraint:{nombre}"):
            return
        reglas = self.reglas.get('constraint', {})
        nombre_up = nombre.upper()
        prefijo = reglas.get('prefijo', 'CST_')
        if not nombre_up.startswith(prefijo):
            self._add_error_prefijo(linea, 'CONSTRAINT', nombre, nombre, prefijo)
        regex = reglas.get('regex_nombre')
        if regex and not re.match(regex, nombre_up):
            self.warnings.append(Error(
                linea=linea, tipo_objeto='CONSTRAINT', nombre_objeto=nombre,
                tipo_error='FORMATO',
                mensaje=f"No cumple formato: {reglas.get('formato', '')}",
                valor_actual=nombre,
            ))

    def validar_funcion(self, linea, nombre):
        self._validar_prefijo_simple(linea, nombre, 'FUNCTION', 'function', 'FN_')

    def validar_indice(self, linea, nombre):
        self._validar_prefijo_simple(linea, nombre, 'INDEX', 'index', 'INX_')

    def validar_sequence(self, linea, nombre):
        self._validar_prefijo_simple(linea, nombre, 'SEQUENCE', 'sequence', 'SQ_')

    def validar_view(self, linea, nombre):
        self._validar_prefijo_simple(linea, nombre, 'VIEW', 'view', 'VW_')

    def validar_trigger(self, linea, nombre):
        if not self._validar_prefijo_simple(linea, nombre, 'TRIGGER', 'trigger', 'TRG_'):
            return
        reglas = self.reglas.get('trigger', {})
        tipos = reglas.get('tipos_validos', [])
        if tipos and not any(f"_{t}" in nombre.upper() for t in tipos):
            self.warnings.append(Error(
                linea=linea, tipo_objeto='TRIGGER', nombre_objeto=nombre,
                tipo_error='TIPO',
                mensaje=f"Sin tipo válido. Usar: {', '.join(tipos)}",
                valor_actual=nombre,
            ))

    def validar(self):
        self.cargar_reglas()
        if not self.ddl_file:
            raise ValueError("No se ha especificado un archivo DDL")
        contenido = Path(self.ddl_file).read_text(encoding='utf-8')
        for linea, esquema, tabla in self.extraer_tablas(contenido):
            self.validar_nombre_tabla(linea, esquema, tabla)
        for linea, esquema, tabla, col, tipo in self.extraer_columnas(contenido):
            self.validar_nombre_columna(linea, esquema, tabla, col, tipo)
        for linea, nombre, *_ in self.extraer_constraints(contenido):
            self.validar_constraint(linea, nombre)
        for linea, nombre in self.extraer_funciones(contenido):
            self.validar_funcion(linea, nombre)
        for linea, nombre in self.extraer_triggers(contenido):
            self.validar_trigger(linea, nombre)
        for linea, nombre in self.extraer_indices(contenido):
            self.validar_indice(linea, nombre)
        for linea, nombre in self.extraer_sequences(contenido):
            self.validar_sequence(linea, nombre)
        for linea, nombre in self.extraer_views(contenido):
            self.validar_view(linea, nombre)
        return len(self.errores) == 0

    _CSS = (
        "body{font-family:sans-serif;padding:20px;max-width:960px;margin:0 auto;background:#ecf0f1;color:#2c3e50}"
        "table{border-collapse:collapse;width:100%;margin-bottom:16px}"
        "th,td{border:1px solid #bdc3c7;padding:5px 10px;text-align:left;font-size:.9em}"
        "th{background:#3498db;color:#fff;font-weight:bold}"
        "h1{font-size:1.3em;margin-bottom:8px;color:#3498db}"
        "h2{font-size:1.05em;margin:20px 0 8px;border-bottom:2px solid #3498db;padding-bottom:3px;color:#2c3e50}"
        "h3{font-size:.9em;color:#7f8c8d;margin:12px 0 5px}"
        ".err{border-left:3px solid #e74c3c;background:#f7fafc;padding:7px 12px;margin-bottom:7px}"
        ".wrn{border-left:3px solid #f39c12;background:#f7fafc;padding:7px 12px;margin-bottom:7px}"
        "code{background:#dde3e8;padding:1px 4px;font-family:monospace}"
        ".sug{color:#27ae60;font-family:monospace}"
    )

    @staticmethod
    def _render_item(item, idx, tipo='error'):
        cls   = 'err' if tipo == 'error' else 'wrn'
        label = item.tipo_error if tipo == 'error' else item.tipo_objeto
        sug   = f'<br>Sugerencia: <span class="sug">{item.valor_sugerido}</span>' \
                if item.valor_sugerido else ''
        return (
            f'<div class="{cls}"><strong>#{idx} — {label}</strong><br>'
            f'Objeto: <strong>{item.nombre_objeto}</strong><br>'
            f'Problema: {item.mensaje}<br>'
            f'Actual: <code>{item.valor_actual}</code>{sug}</div>'
        )

    def generar_reporte(self, archivo_html):
        n_err  = len(self.errores)
        n_warn = len(self.warnings)
        errores_por_tipo  = defaultdict(list)
        warnings_por_tipo = defaultdict(list)
        for e in self.errores:
            errores_por_tipo[e.tipo_objeto].append(e)
        for w in self.warnings:
            warnings_por_tipo[w.tipo_objeto].append(w)
        ahora = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        partes = [
            f'<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">'
            f'<title>Reporte de Nomenclatura</title><style>{self._CSS}</style></head><body>',
            f'<h1>Validación de Nomenclatura</h1>',
            f'<p><strong>Fecha:</strong> {ahora} &nbsp;|&nbsp; '
            f'<strong>Errores:</strong> {n_err} &nbsp;|&nbsp; '
            f'<strong>Advertencias:</strong> {n_warn}</p>',
            f'<table><tr><th>Archivo DDL</th><td>{self.ddl_file}</td></tr>'
            f'<tr><th>Reglas</th><td>{self.reglas_json}</td></tr></table>',
        ]

        if self.errores:
            partes.append(f'<h2>Errores ({n_err})</h2>')
            for tipo in sorted(errores_por_tipo):
                items = errores_por_tipo[tipo]
                partes.append(f'<h3>{tipo} ({len(items)})</h3>')
                partes.extend(self._render_item(e, i, 'error') for i, e in enumerate(items, 1))

        if self.warnings:
            partes.append(f'<h2>Advertencias ({n_warn})</h2>')
            partes.extend(self._render_item(w, i, 'warning') for i, w in enumerate(self.warnings, 1))

        if not self.errores and not self.warnings:
            partes.append('<p><strong>Validación exitosa.</strong> No se encontraron problemas.</p>')

        if errores_por_tipo or warnings_por_tipo:
            todos = sorted(set(list(errores_por_tipo) + list(warnings_por_tipo)))
            filas = ''.join(
                f'<tr><td>{t}</td>'
                f'<td>{len(errores_por_tipo.get(t, []))}</td>'
                f'<td>{len(warnings_por_tipo.get(t, []))}</td></tr>'
                for t in todos
            )
            partes.append(
                f'<h2>Resumen</h2>'
                f'<table><tr><th>Tipo</th><th>Errores</th><th>Advertencias</th></tr>{filas}</table>'
            )

        with open(archivo_html, 'w', encoding='utf-8') as f:
            f.write('\n'.join(partes))
        print(f"[OK] Reporte HTML generado: {archivo_html}")


def main():
    if len(sys.argv) != 7:
        print("Uso: python validar_nomenclatura.py <host> <puerto> <bd> <usuario> <password> <ruta_salida_html>")
        sys.exit(1)
    host, puerto, bd, usuario, password, ruta_salida_html = sys.argv[1:7]

    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        _orig = builtins.print

        def _safe(*args, **kwargs):
            try:
                _orig(*args, **kwargs)
            except UnicodeEncodeError:
                f = kwargs.get('file', sys.stdout)
                text = kwargs.get('sep', ' ').join(str(a) for a in args) + kwargs.get('end', '\n')
                enc = getattr(f, 'encoding', None) or 'utf-8'
                try:
                    if hasattr(f, 'buffer'):
                        f.buffer.write(text.encode(enc, errors='replace'))
                    else:
                        f.write(text.encode(enc, errors='replace').decode(enc))
                except Exception:
                    _orig(text.encode('utf-8', errors='replace').decode('utf-8'))

        builtins.print = _safe

    print(f"Iniciando validación de nomenclatura...")
    print(f"Host: {host} | Puerto: {puerto} | BD: {bd} | Usuario: {usuario}")
    print(f"Reporte: {ruta_salida_html}")

    reglas_json = Path(__file__).resolve().parent.parent / 'resources' / 'reglas_nomenclatura.json'
    validador = ValidadorDDL(str(reglas_json))

    tmp_ddl = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.sql', delete=False) as tmp:
            tmp_ddl = tmp.name

        print("\nExtrayendo DDL desde base de datos...")
        if not validador.generar_ddl_desde_bd(host, puerto, usuario, bd, tmp_ddl, password):
            print("[ERROR] No se pudo extraer el DDL")
            sys.exit(1)

        print("DDL obtenido. Validando nomenclatura...")
        valido = validador.validar()
        print(f"\nResultado: {'VÁLIDO' if valido else 'ERRORES ENCONTRADOS'}")
        print(f"Errores: {len(validador.errores)} | Advertencias: {len(validador.warnings)}")
        validador.generar_reporte(ruta_salida_html)
        print(f"Reporte: {ruta_salida_html}")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] Error durante la validación: {e}")
        sys.exit(1)
    finally:
        if tmp_ddl and os.path.exists(tmp_ddl):
            os.remove(tmp_ddl)


if __name__ == "__main__":
    main()
