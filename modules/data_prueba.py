import sys
import os
import psycopg2
from psycopg2.extras import execute_batch
import json
import random
from datetime import datetime, timedelta
from decimal import Decimal
import re
from collections import defaultdict
from pathlib import Path
import io
import csv

class SmartDataGenerator:

    # ── Datos estáticos ──────────────────────────────────────────────────────
    _NOMBRES      = ['Juan', 'María', 'Carlos', 'Ana', 'Luis', 'Carmen', 'Pedro', 'Rosa',
                     'Jorge', 'Isabel', 'Miguel', 'Elena', 'Antonio', 'Laura', 'José']
    _APELLIDOS    = ['García', 'Rodríguez', 'Martínez', 'López', 'González', 'Hernández',
                     'Pérez', 'Sánchez', 'Ramírez', 'Torres', 'Flores', 'Rivera', 'Gómez']
    _CIUDADES     = ['Lima', 'Arequipa', 'Cusco', 'Trujillo', 'Chiclayo', 'Piura',
                     'Iquitos', 'Huancayo', 'Tacna', 'Puno', 'Ayacucho']
    _PAISES       = ['Perú', 'Argentina', 'Chile', 'Colombia', 'Brasil', 'Ecuador',
                     'México', 'España', 'Estados Unidos']
    _USUARIOS     = ['admin', 'sistema', 'operador', 'supervisor', 'usuario1',
                     'analista', 'gestor', 'coordinador']
    _ESTADOS      = ['ACTIVO', 'INACTIVO', 'PENDIENTE', 'APROBADO', 'RECHAZADO',
                     'EN_PROCESO', 'COMPLETADO', 'CANCELADO']
    _DIR_TIPOS    = ['Av.', 'Jr.', 'Calle', 'Psje.']
    _DIR_CALLES   = ['Los Olivos', 'Las Flores', 'San Martín', 'Bolognesi', 'Grau']
    _EMP_PREF     = ['Corporación', 'Empresa', 'Grupo', 'Inversiones', 'Compañía']
    _EMP_NOMB     = ['Andina', 'del Sur', 'Pacífico', 'Nacional', 'Global', 'Peruana']
    _EMP_SUF      = ['S.A.', 'S.A.C.', 'E.I.R.L.', 'S.R.L.']
    _DOMINIOS     = ['gmail.com', 'outlook.com', 'hotmail.com', 'yahoo.com', 'empresa.com']
    _URL_DOMINIOS = ['ejemplo.com', 'test.com', 'demo.pe', 'sitio.com']
    _DESCRIPCIONES = [
        'Registro generado automáticamente para pruebas del sistema',
        'Entrada de datos de ejemplo para validación',
        'Información de prueba creada por el generador',
        'Dato sintético para testing de la aplicación',
        'Registro de ejemplo con propósitos de desarrollo',
    ]
    _OBSERVACIONES = [
        'Sin observaciones', 'Pendiente de revisión', 'Verificado correctamente',
        'Requiere seguimiento', 'En proceso de validación', 'Aprobado sin inconvenientes',
    ]
    _PALABRAS = [
        'lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur', 'adipiscing', 'elit',
        'sed', 'eiusmod', 'tempor', 'incididunt', 'labore', 'dolore', 'magna', 'aliqua',
    ]

    # Patrones de contexto pre-ordenados por prioridad (mayor primero)
    _CTX = [
        (r'(nombre_completo|full_name|nombre_apellido)',                        'generar_nombre_completo'),
        (r'(^nombre$|^name$|_nombre$|_name$|nombre_|name_)',                   'generar_nombre_persona'),
        (r'(^apellido|^surname|^last_name|apellido_|surname_|paterno|materno)', 'generar_apellido'),
        (r'(^dni$|^documento$|num_doc|numero_documento|_dni$|_documento$)',     'generar_dni'),
        (r'(^ruc$|numero_ruc|_ruc$)',                                           'generar_ruc'),
        (r'(pasaporte|passport)',                                                'generar_pasaporte'),
        (r'(email|correo|mail)',                                                 'generar_email'),
        (r'(telefono|celular|phone|movil|fono)',                                 'generar_telefono'),
        (r'(direccion|address|domicilio)',                                       'generar_direccion'),
        (r'(ciudad|city)',                                                       'generar_ciudad'),
        (r'(^pais$|^country$|_pais$|_country$)',                                'generar_pais'),
        (r'(codigo_postal|cp|zip|postal)',                                       'generar_codigo_postal'),
        (r'(latitud|latitude|lat$)',                                             'generar_latitud'),
        (r'(longitud|longitude|lng$|lon$)',                                      'generar_longitud'),
        (r'(empresa|company|organizacion|razon_social)',                         'generar_empresa'),
        (r'(^url$|_url$|link|enlace)',                                           'generar_url'),
        (r'(^ip$|_ip$|ip_address|direccion_ip)',                                 'generar_ip'),
        (r'(abreviatura|abrev|sigla|acronimo|acronym|codigo_corto|short_code)',  'generar_abreviatura'),
        (r'(^activo$|^active$|^enabled$|_activo$|n_activo|es_activo|b_activo)', 'generar_boolean_activo'),
        (r'(^vigente$|^vigencia$|_vigente$|n_vigente|es_vigente|b_vigente)',    'generar_boolean_activo'),
        (r'(fecha_creacion|created_at|date_create|f_creacion)',                 'generar_fecha_creacion'),
        (r'(fecha_modificacion|modified_at|updated_at|date_update)',            'generar_fecha_modificacion'),
        (r'(monto|amount|precio|price|costo|cost|valor|importe)',               'generar_monto'),
        (r'(porcentaje|percent|tasa|rate)',                                      'generar_porcentaje'),
        (r'(^estado$|^status$|_estado$|_status$)',                              'generar_estado'),
        (r'(usuario_creacion|created_by|user_create|creado_por)',               'generar_usuario'),
        (r'(usuario_modificacion|modified_by|user_update|modificado_por)',      'generar_usuario'),
        (r'(^codigo$|^code$|_codigo$|_code$|^cod_)',                            'generar_codigo'),
        (r'(descripcion|description|detalle|detail)',                           'generar_descripcion'),
        (r'(observacion|observation|nota|comment|comentario)',                  'generar_observacion'),
    ]

    # ── Inicialización ───────────────────────────────────────────────────────
    def __init__(self, host, puerto, bd, usuario, password, esquema, config_file=None):
        self.host     = host
        self.puerto   = puerto
        self.bd       = bd
        self.usuario  = usuario
        self.password = password
        self.esquema  = esquema
        self.conn     = None
        self.cursor   = None
        self.metadata = {
            'tablas': [], 'columnas': {}, 'pks': {}, 'fks': {},
            'checks': {}, 'uniques': {}, 'sequences': {}, 'indices': {},
            'orden_carga': [], 'grafos_dependencias': {}
        }
        self.data_cache      = {}
        self.generated_values = {}
        self.stats = {
            'total_registros': 0, 'por_tabla': {},
            'tiempo_inicio': None, 'tiempo_fin': None, 'errores': []
        }
        base_dir = Path(__file__).resolve().parent
        if config_file is None:
            config_file = base_dir.parent / "resources" / "config_data_prueba.json"
        self.config = self.cargar_config(config_file)
        if self.config.get('seeds', {}).get('random_seed'):
            random.seed(self.config['seeds']['random_seed'])
        self.faker = None
        self._init_faker()

    def _init_faker(self):
        try:
            from faker import Faker
            locale = self.config.get('faker', {}).get('locale', 'es_ES')
            self.faker = Faker(locale)
            print(f"[OK] Faker inicializado con locale: {locale}")
        except ImportError:
            print("[WARN] Faker no esta instalado. Usando generadores basicos.")
            print("  Para mejores resultados, instala: pip install faker")
            self.faker = None

    def _faker_or(self, attr, fallback):
        """Usa faker si está disponible, si no elige de la lista fallback."""
        if self.faker:
            return getattr(self.faker, attr)()
        return random.choice(fallback)

    # ── Inferencia de contexto ───────────────────────────────────────────────
    def inferir_contexto_columna(self, nombre_columna):
        nombre_lower = nombre_columna.lower()
        for regex, generator in self._CTX:
            if re.search(regex, nombre_lower, re.IGNORECASE):
                return generator
        return None

    def _tipo_columna(self, columna_info):
        return (columna_info.get('udt_name') or columna_info.get('tipo_dato') or '').lower()

    # ── Generadores de datos ─────────────────────────────────────────────────
    def generar_nombre_persona(self, columna_info):
        return self._faker_or('first_name', self._NOMBRES)

    def generar_apellido(self, columna_info):
        return self._faker_or('last_name', self._APELLIDOS)

    def generar_nombre_completo(self, columna_info):
        if self.faker:
            return self.faker.name()
        return f"{self.generar_nombre_persona(columna_info)} {self.generar_apellido(columna_info)}"

    def generar_dni(self, columna_info):
        return str(random.randint(10000000, 99999999))

    def generar_ruc(self, columna_info):
        tipo = random.choice(['10', '15', '20'])
        base = str(random.randint(10000000, 99999999))
        return tipo + base + str(random.randint(0, 9))

    def generar_pasaporte(self, columna_info):
        return f"{random.choice(['P', 'A', 'E'])}{random.randint(10000000, 99999999)}"

    def generar_email(self, columna_info):
        if self._tipo_columna(columna_info) in ('int2', 'smallint', 'int4', 'integer', 'int8', 'bigint'):
            return random.randint(0, 1)
        if self.faker:
            return self.faker.email()
        nombre = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=8))
        return f"{nombre}@{random.choice(self._DOMINIOS)}"

    def generar_telefono(self, columna_info):
        if random.choice([True, False]):
            return f"9{random.randint(10000000, 99999999)}"
        return f"01{random.randint(1000000, 9999999)}"

    def generar_direccion(self, columna_info):
        if self.faker:
            return self.faker.address().replace('\n', ', ')
        return f"{random.choice(self._DIR_TIPOS)} {random.choice(self._DIR_CALLES)} {random.randint(100, 999)}"

    def generar_ciudad(self, columna_info):
        return random.choice(self._CIUDADES)

    def generar_pais(self, columna_info):
        return self._faker_or('country', self._PAISES)

    def generar_codigo_postal(self, columna_info):
        return f"LIMA{random.randint(1, 99):02d}"

    def generar_latitud(self, columna_info):
        return round(random.uniform(-18.35, 0), 6)

    def generar_longitud(self, columna_info):
        return round(random.uniform(-81.33, -68.65), 6)

    def generar_empresa(self, columna_info):
        if self.faker:
            return self.faker.company()
        return f"{random.choice(self._EMP_PREF)} {random.choice(self._EMP_NOMB)} {random.choice(self._EMP_SUF)}"

    def generar_estado(self, columna_info):
        if self._tipo_columna(columna_info) in ('int2', 'smallint', 'int4', 'integer', 'int8', 'bigint'):
            return random.randint(0, 5)
        return random.choice(self._ESTADOS)

    def generar_boolean_activo(self, columna_info):
        prob = random.random() < 0.8
        tipo = self._tipo_columna(columna_info)
        if tipo in ('int2', 'smallint', 'int4', 'integer', 'int8', 'bigint', 'numeric', 'decimal'):
            return 1 if prob else 0
        if tipo in ('char', 'bpchar', 'varchar', 'text'):
            return '1' if prob else '0'
        return prob

    def generar_usuario(self, columna_info):
        return random.choice(self._USUARIOS)

    def generar_fecha_creacion(self, columna_info):
        return datetime.now() - timedelta(days=random.randint(1, 365))

    def generar_fecha_modificacion(self, columna_info):
        return datetime.now() - timedelta(days=random.randint(0, 180))

    def generar_monto(self, columna_info):
        scale = columna_info.get('scale', 2)
        rango = random.choice([(10, 100), (100, 1000), (1000, 10000), (10000, 100000)])
        return Decimal(str(round(random.uniform(*rango), scale)))

    def generar_porcentaje(self, columna_info):
        return Decimal(str(round(random.uniform(0, 100), 2)))

    def generar_url(self, columna_info):
        if self.faker:
            return self.faker.url()
        return f"https://www.{random.choice(self._URL_DOMINIOS)}/pagina/{random.randint(1, 100)}"

    def generar_ip(self, columna_info):
        if self.faker:
            return self.faker.ipv4()
        return f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}"

    def generar_codigo(self, columna_info):
        max_len = columna_info.get('max_length') or 10
        length  = min(random.randint(6, 12), max_len)
        letras  = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        numeros = '0123456789'
        if length >= 8:
            return f"{''.join(random.choices(letras, k=3))}-{''.join(random.choices(numeros, k=min(4, length-4)))}"
        return ''.join(random.choices(letras + numeros, k=length))

    def generar_descripcion(self, columna_info):
        if self.faker:
            return self.faker.text(max_nb_chars=min(columna_info.get('max_length', 200), 200))
        return random.choice(self._DESCRIPCIONES)

    def generar_observacion(self, columna_info):
        return self._faker_or('sentence', self._OBSERVACIONES)

    def generar_abreviatura(self, columna_info):
        max_len = columna_info.get('max_length', 10)
        if max_len <= 2:
            length = 2
        elif max_len <= 3:
            length = 3
        elif max_len <= 5:
            length = random.randint(2, min(4, max_len))
        else:
            length = random.randint(2, 5)
        return ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=length))

    # ── Configuración ────────────────────────────────────────────────────────
    def cargar_config(self, config_file):
        config_default = {
            'cantidad_base': 100,
            'cantidad_por_tabla': {},
            'multiplicadores_fk': {'habilitado': True, 'factor': 1.0},
            'generacion_nulls': {
                'habilitado': True, 'probabilidad': 0.2,
                'excluir_pks': True, 'excluir_fks': False
            },
            'limpieza_previa': {'preguntar': True, 'automatico': False},
            'rangos_personalizados': {
                'integer':  {'min': 1, 'max': 2147483647},
                'bigint':   {'min': 1, 'max': 9223372036854775807},
                'smallint': {'min': 1, 'max': 32767},
                'numeric':  {'max_valor': 999999}
            },
            'rangos_fechas': {
                'date':      {'dias_atras': 1825, 'dias_adelante': 0},
                'timestamp': {'dias_atras': 730,  'dias_adelante': 0}
            },
            'texto':       {'max_length_text': 500, 'palabras_personalizadas': []},
            'faker':       {'habilitado': True, 'locale': 'es_ES'},
            'optimizacion':{'usar_copy': True, 'batch_size': 1000},
            'seeds':       {'random_seed': None}
        }
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_archivo = json.load(f)
                    if 'config_generacion' in config_archivo:
                        config_archivo = config_archivo['config_generacion']
                    self._merge_config(config_default, config_archivo)
                    print(f"[OK] Configuracion cargada: {config_file}")
            except Exception as e:
                print(f"[WARN] Error cargando config, usando defaults: {e}")
        return config_default

    def _merge_config(self, base, updates):
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    # ── Conexión ─────────────────────────────────────────────────────────────
    def conectar(self):
        try:
            self.conn = psycopg2.connect(
                host=self.host, port=self.puerto, database=self.bd,
                user=self.usuario, password=self.password
            )
            self.cursor = self.conn.cursor()
            print(f"[OK] Conectado a PostgreSQL: {self.bd}")
            return True
        except Exception as e:
            print(f"[ERROR] Error al conectar: {e}")
            return False

    def desconectar(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    # ── Análisis de base de datos ────────────────────────────────────────────
    def analizar_base_datos(self):
        print(f"\n{'='*70}")
        print(f"ANALISIS DE ESTRUCTURA DE BASE DE DATOS")
        print(f"{'='*70}\n")
        print(f"Esquema: {self.esquema}")
        self.metadata['tablas'] = self.obtener_tablas()
        print(f"[OK] Tablas: {len(self.metadata['tablas'])}")
        for tabla in self.metadata['tablas']:
            self.metadata['columnas'][tabla] = self.obtener_columnas(tabla)
        print(f"[OK] Columnas analizadas")
        self.metadata['pks'] = self.obtener_primary_keys()
        print(f"[OK] Primary Keys: {len(self.metadata['pks'])}")
        self.metadata['fks'] = self.obtener_foreign_keys()
        print(f"[OK] Foreign Keys: {sum(len(v) for v in self.metadata['fks'].values())}")
        self.metadata['checks'] = self.obtener_check_constraints()
        print(f"[OK] CHECK Constraints: {sum(len(v) for v in self.metadata['checks'].values())}")
        self.metadata['uniques'] = self.obtener_unique_constraints()
        print(f"[OK] UNIQUE Constraints: {sum(len(v) for v in self.metadata['uniques'].values())}")
        self.metadata['sequences'] = self.obtener_sequences()
        print(f"[OK] Sequences: {len(self.metadata['sequences'])}")
        self.metadata['indices'] = self.obtener_indices()
        print(f"[OK] Indices: {sum(len(v) for v in self.metadata['indices'].values())}")
        self.metadata['orden_carga'] = self.resolver_orden_carga()
        print(f"[OK] Orden de carga resuelto: {len(self.metadata['orden_carga'])} tablas")
        self._analizar_contexto_semantico()
        print(f"\n{'='*70}")
        print(f"[OK] ANALISIS COMPLETADO")
        print(f"{'='*70}\n")

    def _analizar_contexto_semantico(self):
        print(f"\nAnalisis de Contexto Semantico:")
        contextos = defaultdict(list)
        for tabla, columnas in self.metadata['columnas'].items():
            for columna in columnas:
                gen = self.inferir_contexto_columna(columna['nombre'])
                if gen:
                    contextos[gen].append(f"{tabla}.{columna['nombre']}")
        if contextos:
            print(f"  [OK] Detectados {len(contextos)} tipos de contexto:")
            for gen, cols in sorted(contextos.items()):
                print(f"    - {gen}: {len(cols)} columna(s)")
        else:
            print(f"  [INFO] No se detectaron contextos especiales (se usaran generadores por tipo)")

    # ── Consultas de metadatos ───────────────────────────────────────────────
    def obtener_tablas(self):
        self.cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = %s AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """, (self.esquema,))
        return [row[0] for row in self.cursor.fetchall()]

    def obtener_columnas(self, tabla):
        self.cursor.execute("""
            SELECT column_name, data_type, udt_name, character_maximum_length,
                   numeric_precision, numeric_scale, is_nullable, column_default, ordinal_position
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """, (self.esquema, tabla))
        return [
            {'nombre': r[0], 'tipo_dato': r[1], 'udt_name': r[2], 'max_length': r[3],
             'precision': r[4], 'scale': r[5], 'nullable': r[6] == 'YES',
             'default': r[7], 'posicion': r[8]}
            for r in self.cursor.fetchall()
        ]

    def _query_to_groups(self, query, row_to_kv):
        """Ejecuta query y agrupa resultados en un dict de listas."""
        self.cursor.execute(query, (self.esquema,))
        groups = defaultdict(list)
        for row in self.cursor.fetchall():
            k, v = row_to_kv(row)
            groups[k].append(v)
        return dict(groups)

    def obtener_primary_keys(self):
        return self._query_to_groups("""
            SELECT tc.table_name, kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.table_schema = %s AND tc.constraint_type = 'PRIMARY KEY'
            ORDER BY tc.table_name, kcu.ordinal_position
        """, lambda row: (row[0], row[1]))

    def obtener_foreign_keys(self):
        return self._query_to_groups("""
            SELECT tc.table_name, kcu.column_name, ccu.table_name, ccu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.table_schema = %s AND tc.constraint_type = 'FOREIGN KEY'
            ORDER BY tc.table_name
        """, lambda row: (row[0], {'columna': row[1], 'tabla_ref': row[2], 'columna_ref': row[3]}))

    def obtener_check_constraints(self):
        return self._query_to_groups("""
            SELECT tc.table_name, cc.check_clause
            FROM information_schema.table_constraints tc
            JOIN information_schema.check_constraints cc
                ON tc.constraint_name = cc.constraint_name
            WHERE tc.table_schema = %s AND tc.constraint_type = 'CHECK'
        """, lambda row: (row[0], row[1]))

    def obtener_unique_constraints(self):
        return self._query_to_groups("""
            SELECT tc.table_name, kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.table_schema = %s AND tc.constraint_type = 'UNIQUE'
            ORDER BY tc.table_name
        """, lambda row: (row[0], row[1]))

    def obtener_sequences(self):
        self.cursor.execute("""
            SELECT sequence_name, data_type, start_value, minimum_value, maximum_value, increment
            FROM information_schema.sequences
            WHERE sequence_schema = %s
        """, (self.esquema,))
        return {
            r[0]: {'tipo': r[1], 'inicio': r[2], 'minimo': r[3], 'maximo': r[4], 'incremento': r[5]}
            for r in self.cursor.fetchall()
        }

    def obtener_indices(self):
        return self._query_to_groups("""
            SELECT tablename, indexname, indexdef FROM pg_indexes
            WHERE schemaname = %s
            ORDER BY tablename, indexname
        """, lambda row: (row[0], {'nombre': row[1], 'definicion': row[2]}))

    # ── Orden de carga (topological sort) ────────────────────────────────────
    def resolver_orden_carga(self):
        dependencias = defaultdict(set)
        sin_dependencias = set(self.metadata['tablas'])
        for tabla, fks in self.metadata['fks'].items():
            for fk in fks:
                tabla_ref = fk['tabla_ref']
                if tabla_ref != tabla:
                    dependencias[tabla].add(tabla_ref)
                    sin_dependencias.discard(tabla)
        orden      = []
        procesadas = set()
        en_proceso = set()

        def visitar_tabla(tabla):
            if tabla in procesadas:
                return True
            if tabla in en_proceso:
                print(f"  [WARN] Ciclo detectado en: {tabla}")
                return False
            en_proceso.add(tabla)
            for dep in dependencias.get(tabla, []):
                visitar_tabla(dep)
            en_proceso.discard(tabla)
            if tabla not in procesadas:
                orden.append(tabla)
                procesadas.add(tabla)
            return True

        for tabla in sorted(sin_dependencias):
            visitar_tabla(tabla)
        for tabla in sorted(self.metadata['tablas']):
            visitar_tabla(tabla)
        return orden

    # ── Generación de valores ────────────────────────────────────────────────
    def generar_valor_columna(self, tabla, columna_info, registro_actual=None):
        nombre_col = columna_info['nombre']
        tipo       = columna_info['udt_name'] or columna_info['tipo_dato']
        col_key    = f"{tabla}.{nombre_col}"
        columnas_personalizadas = self.config.get('columnas_personalizadas', {})
        if col_key in columnas_personalizadas:
            try:
                valor = self._generar_valor_personalizado(col_key, columnas_personalizadas[col_key], columna_info)
                if tabla in self.metadata['uniques'] and nombre_col in self.metadata['uniques'][tabla]:
                    gen_lambda = lambda ci: self._generar_valor_personalizado(col_key, columnas_personalizadas[col_key], ci)
                    valor = self._garantizar_unicidad(tabla, nombre_col, valor, gen_lambda, columna_info)
                return valor
            except Exception as e:
                print(f"  [WARN] Error en configuración personalizada para {col_key}: {e}")
        if tabla in self.metadata['fks']:
            for fk in self.metadata['fks'][tabla]:
                if fk['columna'] == nombre_col:
                    return self.obtener_valor_fk(fk['tabla_ref'], fk['columna_ref'])
        if tabla in self.metadata['pks'] and nombre_col in self.metadata['pks'][tabla]:
            if columna_info['default'] and 'nextval' in str(columna_info['default']):
                return None
        if self._debe_generar_null(tabla, nombre_col, columna_info):
            return None
        generador_nombre = self.inferir_contexto_columna(nombre_col)
        if generador_nombre:
            try:
                generador = getattr(self, generador_nombre)
                valor = generador(columna_info)
                if tabla in self.metadata['uniques'] and nombre_col in self.metadata['uniques'][tabla]:
                    valor = self._garantizar_unicidad(tabla, nombre_col, valor, generador, columna_info)
                return valor
            except Exception as e:
                print(f"  [WARN] Error en generador {generador_nombre}: {e}")
        return self.generar_por_tipo(tipo, columna_info)

    def _generar_valor_personalizado(self, col_key, config_personalizada, columna_info):
        tipo   = config_personalizada['tipo']
        config = config_personalizada['config']
        if tipo in ('int2', 'smallint', 'int4', 'integer', 'int8', 'bigint'):
            return random.randint(config['min'], config['max'])
        elif tipo in ('numeric', 'decimal'):
            valor = random.uniform(config['min'], config['max'])
            return round(Decimal(str(valor)), config.get('decimales', 2))
        elif tipo in ('varchar', 'character varying', 'bpchar', 'char', 'character', 'text'):
            longitud = config['longitud']
            if config.get('usar_faker', False) and self.faker:
                return self.faker.text(max_nb_chars=longitud)[:longitud]
            return self.generar_texto_basico(longitud)
        elif tipo in ('date', 'timestamp', 'timestamptz', 'timestamp with time zone'):
            try:
                fecha_inicio = datetime.strptime(config['fecha_inicio'], '%Y-%m-%d')
                fecha_fin    = datetime.strptime(config['fecha_fin'],    '%Y-%m-%d')
                fecha = fecha_inicio + timedelta(days=random.randint(0, (fecha_fin - fecha_inicio).days))
                if 'timestamp' in tipo:
                    fecha = fecha.replace(hour=random.randint(0, 23),
                                          minute=random.randint(0, 59),
                                          second=random.randint(0, 59))
                return fecha
            except Exception as e:
                print(f"  [WARN] Error al parsear fechas en {col_key}: {e}. Usando fallback.")
                return self.generar_fecha()
        elif tipo == 'bool':
            return random.random() < config.get('prob_true', 0.5)
        else:
            raise ValueError(f"Tipo '{tipo}' no soportado en configuración personalizada")

    def _debe_generar_null(self, tabla, nombre_col, columna_info):
        if not columna_info['nullable']:
            return False
        if not self.config['generacion_nulls']['habilitado']:
            return False
        if (tabla in self.metadata['pks'] and nombre_col in self.metadata['pks'][tabla]
                and self.config['generacion_nulls']['excluir_pks']):
            return False
        if (self.config['generacion_nulls']['excluir_fks']
                and tabla in self.metadata['fks']
                and any(fk['columna'] == nombre_col for fk in self.metadata['fks'][tabla])):
            return False
        return random.random() < self.config['generacion_nulls']['probabilidad']

    def _garantizar_unicidad(self, tabla, columna, valor, generador, columna_info):
        cache_key = f"{tabla}.{columna}"
        usados    = self.generated_values.setdefault(cache_key, set())
        intentos  = 0
        while valor in usados and intentos < 1000:
            valor = generador(columna_info)
            intentos += 1
        if intentos >= 1000:
            import uuid
            if isinstance(valor, str):
                valor = f"{valor}_{uuid.uuid4().hex[:6]}"
        usados.add(valor)
        return valor

    def generar_por_tipo(self, tipo, columna_info):
        tipo = tipo.lower()
        if tipo in ('varchar', 'character varying', 'bpchar', 'char', 'character'):
            max_len = columna_info['max_length'] or self.config.get('texto', {}).get('max_length_text', 50)
            return self.generar_texto_basico(max_len)
        elif tipo == 'text':
            max_len_cfg = self.config.get('texto', {}).get('max_length_text', 200)
            return self.generar_texto_basico(min(random.randint(50, 200), max_len_cfg))
        elif tipo in ('int4', 'integer'):
            cfg = self.config['rangos_personalizados']['integer']
            return random.randint(cfg['min'], min(cfg['max'], 2147483647))
        elif tipo in ('int8', 'bigint'):
            cfg = self.config['rangos_personalizados']['bigint']
            return random.randint(cfg['min'], min(cfg['max'], 9223372036854775807))
        elif tipo in ('int2', 'smallint'):
            cfg = self.config['rangos_personalizados']['smallint']
            return random.randint(cfg['min'], min(cfg['max'], 32767))
        elif tipo in ('numeric', 'decimal'):
            precision = columna_info['precision'] or 10
            scale     = columna_info['scale'] or 2
            max_val   = 10 ** (precision - scale) - 1
            return Decimal(str(round(random.uniform(0, max_val), scale)))
        elif tipo in ('float4', 'float8', 'real', 'double precision'):
            return round(random.uniform(0, 10000), 2)
        elif tipo == 'date':
            cfg = self.config['rangos_fechas']['date']
            return (datetime.now() - timedelta(days=random.randint(0, cfg['dias_atras']))).date()
        elif tipo in ('timestamp', 'timestamptz', 'timestamp without time zone', 'timestamp with time zone'):
            cfg = self.config['rangos_fechas']['timestamp']
            return datetime.now() - timedelta(days=random.randint(0, cfg['dias_atras']),
                                               hours=random.randint(0, 23))
        elif tipo in ('time', 'time without time zone'):
            return f"{random.randint(0,23):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}"
        elif tipo in ('bool', 'boolean'):
            return random.choice([True, False])
        elif tipo == 'uuid':
            import uuid
            return str(uuid.uuid4())
        elif tipo in ('json', 'jsonb'):
            return json.dumps({'id': random.randint(1, 1000),
                               'valor': self.generar_texto_basico(20),
                               'activo': random.choice([True, False])})
        elif tipo.endswith('[]'):
            return [self.generar_por_tipo(tipo[:-2], columna_info) for _ in range(random.randint(1, 5))]
        else:
            return self.generar_texto_basico(50)

    def generar_texto_basico(self, max_len):
        texto = ''
        while len(texto) < max_len:
            palabra = random.choice(self._PALABRAS)
            if len(texto) + len(palabra) + 1 <= max_len:
                texto += palabra + ' '
            else:
                break
        return texto.strip()[:max_len]

    # ── FK y unicidad ────────────────────────────────────────────────────────
    def obtener_valor_fk(self, tabla_ref, columna_ref):
        cache_key = f"{tabla_ref}.{columna_ref}"
        if cache_key in self.data_cache and self.data_cache[cache_key]:
            return random.choice(self.data_cache[cache_key])
        tabla_completa = f"{self.esquema}.{tabla_ref}"
        query = f'SELECT "{columna_ref}" FROM {tabla_completa} WHERE "{columna_ref}" IS NOT NULL LIMIT 1000'
        try:
            self.cursor.execute(query)
            valores = [row[0] for row in self.cursor.fetchall()]
            if valores:
                self.data_cache[cache_key] = valores
                return random.choice(valores)
            return None
        except Exception as e:
            print(f"  [WARN] Error obteniendo FK {tabla_ref}.{columna_ref}: {e}")
            return None

    # ── Generación e inserción ───────────────────────────────────────────────
    def generar_registros_tabla(self, tabla, cantidad):
        registros           = []
        columnas            = self.metadata['columnas'][tabla]
        registros_saltados  = 0
        columnas_procesadas = 0
        columnas_con_default = 0
        for _ in range(cantidad):
            registro      = {}
            registro_valido = True
            for columna in columnas:
                nombre_col = columna['nombre']
                if columna['default'] and 'nextval' in str(columna['default']):
                    columnas_con_default += 1
                    continue
                columnas_procesadas += 1
                valor = self.generar_valor_columna(tabla, columna, registro)
                if valor is None and not columna['nullable']:
                    registro_valido = False
                    registros_saltados += 1
                    break
                registro[nombre_col] = valor
            if registro_valido and registro:
                registros.append(registro)
        if len(registros) == 0:
            print(f"  [WARN] 0 registros generados para {tabla}")
            print(f"  - Columnas totales: {len(columnas)}")
            print(f"  - Columnas con DEFAULT/sequence: {columnas_con_default}")
            print(f"  - Columnas procesadas: {columnas_procesadas}")
            print(f"  - Registros saltados por validacion: {registros_saltados}")
            if columnas_procesadas > 0 and registros_saltados == cantidad:
                print(f"  [WARN] Todas las iteraciones fueron saltadas - revisar FKs o columnas requeridas")
        elif registros_saltados > 0:
            print(f"  [WARN] {registros_saltados} registros saltados por columnas requeridas sin valor")
        return registros

    def insertar_registros(self, tabla, registros):
        if not registros:
            return 0
        if self.config.get('optimizacion', {}).get('usar_copy', True):
            return self._insertar_con_copy(tabla, registros)
        return self._insertar_con_batch(tabla, registros)

    def _insertar_con_copy(self, tabla, registros):
        if not registros:
            return 0
        try:
            columnas       = list(registros[0].keys())
            tabla_completa = f"{self.esquema}.{tabla}"
            output = io.StringIO()
            writer = csv.writer(output, delimiter='\t', quotechar='"',
                                quoting=csv.QUOTE_MINIMAL, lineterminator='\n')
            for registro in registros:
                fila = []
                for col in columnas:
                    valor = registro.get(col)
                    if valor is None:
                        fila.append('\\N')
                    elif isinstance(valor, datetime):
                        fila.append(valor.isoformat())
                    elif isinstance(valor, bool):
                        fila.append('t' if valor else 'f')
                    elif isinstance(valor, (list, dict)):
                        fila.append(json.dumps(valor))
                    else:
                        fila.append(str(valor))
                writer.writerow(fila)
            output.seek(0)
            columnas_str = ', '.join([f'"{col}"' for col in columnas])
            self.cursor.copy_expert(
                f"COPY {tabla_completa} ({columnas_str}) FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t', NULL '\\N', QUOTE '\"')",
                output
            )
            self.conn.commit()
            self._actualizar_cache_insercion(tabla, registros, columnas)
            return len(registros)
        except Exception as e:
            self.conn.rollback()
            print(f"  [ERROR] Error con COPY en {tabla}: {e}")
            print(f"  [INFO] Intentando con execute_batch...")
            return self._insertar_con_batch(tabla, registros)

    def _insertar_con_batch(self, tabla, registros):
        if not registros:
            return 0
        try:
            columnas       = list(registros[0].keys())
            tabla_completa = f"{self.esquema}.{tabla}"
            columnas_str   = ', '.join([f'"{col}"' for col in columnas])
            placeholders   = ', '.join(['%s'] * len(columnas))
            query          = f'INSERT INTO {tabla_completa} ({columnas_str}) VALUES ({placeholders})'
            datos          = [tuple(registro.get(col) for col in columnas) for registro in registros]
            batch_size     = self.config.get('optimizacion', {}).get('batch_size', 1000)
            execute_batch(self.cursor, query, datos, page_size=batch_size)
            self.conn.commit()
            self._actualizar_cache_insercion(tabla, registros, columnas)
            return len(registros)
        except Exception as e:
            self.conn.rollback()
            print(f"  [ERROR] Error insertando en {tabla}: {e}")
            self.stats['errores'].append(f"{tabla}: {str(e)}")
            return 0

    def _actualizar_cache_insercion(self, tabla, registros, columnas):
        for pk_col in self.metadata['pks'].get(tabla, []):
            if pk_col in columnas:
                cache_key = f"{tabla}.{pk_col}"
                valores   = [r[pk_col] for r in registros if r.get(pk_col) is not None]
                self.data_cache.setdefault(cache_key, []).extend(valores)

    # ── Proceso principal ────────────────────────────────────────────────────
    def generar_data_completa(self, cantidad_base=None):
        if cantidad_base is None:
            cantidad_base = self.config.get('cantidad_base', 100)
        self.stats['tiempo_inicio'] = datetime.now()
        print(f"\n{'='*70}")
        print(f"GENERACION DE DATA DE PRUEBA")
        print(f"{'='*70}\n")
        print(f"Cantidad base: {cantidad_base} registros")
        print(f"Tablas a procesar: {len(self.metadata['orden_carga'])}")
        usar_copy = self.config.get('optimizacion', {}).get('usar_copy')
        print(f"Metodo de insercion: {'COPY' if usar_copy else 'INSERT BATCH'}\n")
        total_insertados = 0
        for i, tabla in enumerate(self.metadata['orden_carga'], 1):
            print(f"[{i}/{len(self.metadata['orden_carga'])}] {tabla}")
            cantidad = self.config.get('cantidad_por_tabla', {}).get(tabla, cantidad_base)
            if (self.config['multiplicadores_fk']['habilitado']
                    and tabla in self.metadata['fks'] and self.metadata['fks'][tabla]):
                factor   = self.config['multiplicadores_fk']['factor']
                cantidad = int(cantidad_base * len(self.metadata['fks'][tabla]) * factor)
            print(f"  -> Generando {cantidad} registros...")
            registros  = self.generar_registros_tabla(tabla, cantidad)
            print(f"  -> Insertando...")
            insertados = self.insertar_registros(tabla, registros)
            if insertados > 0:
                print(f"  [OK] {insertados} registros insertados\n")
                total_insertados += insertados
                self.stats['por_tabla'][tabla] = insertados
            else:
                print(f"  [WARN] 0 registros insertados\n")
                self.stats['por_tabla'][tabla] = 0
        self.stats['tiempo_fin']      = datetime.now()
        self.stats['total_registros'] = total_insertados
        self._mostrar_reporte_final()

    def _mostrar_reporte_final(self):
        print(f"{'='*70}")
        print(f"[OK] GENERACION COMPLETADA")
        print(f"{'='*70}\n")
        print(f"Estadisticas:")
        print(f"  - Total registros insertados: {self.stats['total_registros']:,}")
        print(f"  - Tablas procesadas: {len(self.stats['por_tabla'])}")
        if self.stats['tiempo_inicio'] and self.stats['tiempo_fin']:
            duracion = (self.stats['tiempo_fin'] - self.stats['tiempo_inicio']).total_seconds()
            print(f"  - Tiempo total: {duracion:.2f} segundos")
            if duracion > 0:
                print(f"  - Tasa de insercion: {self.stats['total_registros'] / duracion:.0f} registros/segundo")
        if self.stats['errores']:
            print(f"\n[WARN] Errores encontrados: {len(self.stats['errores'])}")
            for error in self.stats['errores'][:5]:
                print(f"  - {error}")
        print(f"\n{'='*70}\n")

    def limpiar_tablas(self):
        print(f"\nLimpiando tablas existentes...")
        for tabla in reversed(self.metadata['orden_carga']):
            try:
                self.cursor.execute(f'TRUNCATE TABLE {self.esquema}.{tabla} CASCADE')
                self.conn.commit()
                print(f"  [OK] {tabla}")
            except Exception as e:
                print(f"  [ERROR] Error en {tabla}: {e}")
                self.conn.rollback()


def main():
    if sys.platform == 'win32':
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except:
            pass
    if len(sys.argv) < 7:
        print("Error: Faltan parámetros")
        print("Uso: python data_prueba.py <host> <puerto> <bd> <usuario> <password> <esquema> [cantidad]")
        sys.exit(1)
    host     = sys.argv[1]
    puerto   = sys.argv[2]
    bd       = sys.argv[3]
    usuario  = sys.argv[4]
    password = sys.argv[5]
    esquema  = sys.argv[6]
    cantidad = int(sys.argv[7]) if len(sys.argv) > 7 else None
    print(f"\n{'='*70}")
    print(f"SEMBRADO INTELIGENTE DE DATOS - PostgreSQL")
    print(f"{'='*70}\n")
    print(f"Sistema de generacion semantica de datos de prueba")
    print(f"con inferencia de contexto de negocio\n")
    generator = SmartDataGenerator(host, puerto, bd, usuario, password, esquema)
    if not generator.conectar():
        sys.exit(1)
    try:
        generator.analizar_base_datos()
        if generator.config['limpieza_previa']['automatico']:
            generator.limpiar_tablas()
        elif generator.config['limpieza_previa']['preguntar']:
            try:
                respuesta = input("\n¿Limpiar tablas antes de insertar? (s/n): ")
                if respuesta.lower() == 's':
                    generator.limpiar_tablas()
            except EOFError:
                print("\n[INFO] Modo no interactivo detectado. Continuando sin limpieza previa.")
                print("[INFO] Para limpiar tablas automaticamente, configura 'limpieza_previa.automatico': true")
        generator.generar_data_completa(cantidad_base=cantidad)
    except Exception as e:
        print(f"\n[ERROR] Error durante la ejecucion: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        generator.desconectar()

if __name__ == "__main__":
    main()
