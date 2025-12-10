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
    """
    Generador Inteligente de Data de Prueba para PostgreSQL.

    Características:
    - Ingeniería inversa completa del esquema de BD (tablas, columnas, tipos, relaciones)
    - Inferencia de contexto de negocio basada en nombres de columnas
    - Generación de datos semánticamente realistas
    - Resolución automática de dependencias y orden de carga
    - Carga masiva optimizada con COPY
    """

    def __init__(self, host, puerto, bd, usuario, password, esquema, config_file=None):
        self.host = host
        self.puerto = puerto
        self.bd = bd
        self.usuario = usuario
        self.password = password
        self.esquema = esquema
        self.conn = None
        self.cursor = None

        # Metadata de la base de datos
        self.metadata = {
            'tablas': [],
            'columnas': {},
            'pks': {},
            'fks': {},
            'checks': {},
            'uniques': {},
            'sequences': {},
            'indices': {},
            'orden_carga': [],
            'grafos_dependencias': {}
        }

        # Cache de valores generados
        self.data_cache = {}
        self.generated_values = {}  # Para valores UNIQUE

        # Estadísticas de generación
        self.stats = {
            'total_registros': 0,
            'por_tabla': {},
            'tiempo_inicio': None,
            'tiempo_fin': None,
            'errores': []
        }

        # Cargar configuración
        base_dir = Path(__file__).resolve().parent
        if config_file is None:
            config_file = base_dir.parent / "resources" / "config_data_prueba.json"
        self.config = self.cargar_config(config_file)

        # Aplicar seed para reproducibilidad
        if self.config.get('seeds', {}).get('random_seed'):
            random.seed(self.config['seeds']['random_seed'])

        # Inicializar generador Faker
        self.faker = None
        self._init_faker()

        # Sistema de inferencia de contexto
        self.context_patterns = self._build_context_patterns()

    def _init_faker(self):
        """Inicializa el generador Faker con manejo de errores"""
        try:
            from faker import Faker
            locale = self.config.get('faker', {}).get('locale', 'es_ES')
            self.faker = Faker(locale)
            print(f"[OK] Faker inicializado con locale: {locale}")
        except ImportError:
            print("[WARN] Faker no esta instalado. Usando generadores basicos.")
            print("  Para mejores resultados, instala: pip install faker")
            self.faker = None

    def _build_context_patterns(self):
        """
        Construye patrones de contexto de negocio basados en nombres de columnas.
        Este es el corazón del sistema de inferencia semántica.
        """
        patterns = {
            # Identificadores personales
            'nombre': {
                'regex': r'(^nombre$|^name$|_nombre$|_name$|nombre_|name_)',
                'generator': 'generar_nombre_persona',
                'priority': 10
            },
            'apellido': {
                'regex': r'(^apellido|^surname|^last_name|apellido_|surname_|paterno|materno)',
                'generator': 'generar_apellido',
                'priority': 10
            },
            'nombre_completo': {
                'regex': r'(nombre_completo|full_name|nombre_apellido)',
                'generator': 'generar_nombre_completo',
                'priority': 15
            },

            # Documentos de identidad
            'dni': {
                'regex': r'(^dni$|^documento$|num_doc|numero_documento|_dni$|_documento$)',
                'generator': 'generar_dni',
                'priority': 10
            },
            'ruc': {
                'regex': r'(^ruc$|numero_ruc|_ruc$)',
                'generator': 'generar_ruc',
                'priority': 10
            },
            'pasaporte': {
                'regex': r'(pasaporte|passport)',
                'generator': 'generar_pasaporte',
                'priority': 10
            },

            # Contacto
            'email': {
                'regex': r'(email|correo|mail)',
                'generator': 'generar_email',
                'priority': 10
            },
            'telefono': {
                'regex': r'(telefono|celular|phone|movil|fono)',
                'generator': 'generar_telefono',
                'priority': 10
            },

            # Ubicación geográfica
            'direccion': {
                'regex': r'(direccion|address|domicilio)',
                'generator': 'generar_direccion',
                'priority': 10
            },
            'ciudad': {
                'regex': r'(ciudad|city)',
                'generator': 'generar_ciudad',
                'priority': 10
            },
            'pais': {
                'regex': r'(^pais$|^country$|_pais$|_country$)',
                'generator': 'generar_pais',
                'priority': 10
            },
            'codigo_postal': {
                'regex': r'(codigo_postal|cp|zip|postal)',
                'generator': 'generar_codigo_postal',
                'priority': 10
            },
            'latitud': {
                'regex': r'(latitud|latitude|lat$)',
                'generator': 'generar_latitud',
                'priority': 10
            },
            'longitud': {
                'regex': r'(longitud|longitude|lng$|lon$)',
                'generator': 'generar_longitud',
                'priority': 10
            },

            # Información empresarial
            'empresa': {
                'regex': r'(empresa|company|organizacion|razon_social)',
                'generator': 'generar_empresa',
                'priority': 10
            },

            # Campos de estado y control
            'estado': {
                'regex': r'(^estado$|^status$|_estado$|_status$)',
                'generator': 'generar_estado',
                'priority': 8
            },
            'activo': {
                'regex': r'(^activo$|^active$|^enabled$|_activo$|es_activo)',
                'generator': 'generar_boolean_activo',
                'priority': 9
            },

            # Campos de auditoría
            'usuario_creacion': {
                'regex': r'(usuario_creacion|created_by|user_create|creado_por)',
                'generator': 'generar_usuario',
                'priority': 8
            },
            'usuario_modificacion': {
                'regex': r'(usuario_modificacion|modified_by|user_update|modificado_por)',
                'generator': 'generar_usuario',
                'priority': 8
            },
            'fecha_creacion': {
                'regex': r'(fecha_creacion|created_at|date_create|f_creacion)',
                'generator': 'generar_fecha_creacion',
                'priority': 9
            },
            'fecha_modificacion': {
                'regex': r'(fecha_modificacion|modified_at|updated_at|date_update)',
                'generator': 'generar_fecha_modificacion',
                'priority': 9
            },

            # Campos financieros
            'monto': {
                'regex': r'(monto|amount|precio|price|costo|cost|valor|importe)',
                'generator': 'generar_monto',
                'priority': 9
            },
            'porcentaje': {
                'regex': r'(porcentaje|percent|tasa|rate)',
                'generator': 'generar_porcentaje',
                'priority': 9
            },

            # URLs y recursos web
            'url': {
                'regex': r'(^url$|_url$|link|enlace)',
                'generator': 'generar_url',
                'priority': 10
            },
            'ip': {
                'regex': r'(^ip$|_ip$|ip_address|direccion_ip)',
                'generator': 'generar_ip',
                'priority': 10
            },

            # Códigos
            'codigo': {
                'regex': r'(^codigo$|^code$|_codigo$|_code$|^cod_)',
                'generator': 'generar_codigo',
                'priority': 7
            },

            # Descripción
            'descripcion': {
                'regex': r'(descripcion|description|detalle|detail)',
                'generator': 'generar_descripcion',
                'priority': 6
            },
            'observacion': {
                'regex': r'(observacion|observation|nota|comment|comentario)',
                'generator': 'generar_observacion',
                'priority': 6
            },

            # Abreviaturas
            'abreviatura': {
                'regex': r'(abreviatura|abrev|sigla|acronimo|acronym|codigo_corto|short_code)',
                'generator': 'generar_abreviatura',
                'priority': 10
            }
        }

        return patterns

    def inferir_contexto_columna(self, nombre_columna):
        """
        Infiere el contexto de negocio de una columna basándose en su nombre.
        Retorna el generador apropiado o None.
        """
        nombre_lower = nombre_columna.lower()

        # Ordenar patrones por prioridad (mayor primero)
        sorted_patterns = sorted(
            self.context_patterns.items(),
            key=lambda x: x[1]['priority'],
            reverse=True
        )

        for pattern_name, pattern_info in sorted_patterns:
            if re.search(pattern_info['regex'], nombre_lower, re.IGNORECASE):
                return pattern_info['generator']

        return None

    # =============================================================================
    # GENERADORES SEMÁNTICOS ESPECIALIZADOS
    # =============================================================================

    def _tipo_columna(self, columna_info):
        """Obtiene el tipo de dato base en minúsculas"""
        return (columna_info.get('udt_name') or columna_info.get('tipo_dato') or '').lower()

    def generar_nombre_persona(self, columna_info):
        """Genera un nombre de persona realista"""
        if self.faker:
            return self.faker.first_name()
        nombres = ['Juan', 'María', 'Carlos', 'Ana', 'Luis', 'Carmen', 'Pedro', 'Rosa',
                   'Jorge', 'Isabel', 'Miguel', 'Elena', 'Antonio', 'Laura', 'José']
        return random.choice(nombres)

    def generar_apellido(self, columna_info):
        """Genera un apellido realista"""
        if self.faker:
            return self.faker.last_name()
        apellidos = ['García', 'Rodríguez', 'Martínez', 'López', 'González', 'Hernández',
                     'Pérez', 'Sánchez', 'Ramírez', 'Torres', 'Flores', 'Rivera', 'Gómez']
        return random.choice(apellidos)

    def generar_nombre_completo(self, columna_info):
        """Genera un nombre completo realista"""
        if self.faker:
            return self.faker.name()
        nombre = self.generar_nombre_persona(columna_info)
        apellido = self.generar_apellido(columna_info)
        return f"{nombre} {apellido}"

    def generar_dni(self, columna_info):
        """Genera un DNI peruano válido (8 dígitos)"""
        return str(random.randint(10000000, 99999999))

    def generar_ruc(self, columna_info):
        """Genera un RUC peruano válido (11 dígitos)"""
        tipo = random.choice(['10', '15', '20'])  # 10: persona natural, 20: empresa
        base = str(random.randint(10000000, 99999999))
        ruc = tipo + base
        # Agregar dígito verificador (simplificado)
        return ruc + str(random.randint(0, 9))

    def generar_pasaporte(self, columna_info):
        """Genera un número de pasaporte"""
        return f"{random.choice(['P', 'A', 'E'])}{random.randint(10000000, 99999999)}"

    def generar_email(self, columna_info):
        """Genera un email realista"""
        # Si la columna es numérica (p.ej. flags de envío), devolver 0/1
        tipo = self._tipo_columna(columna_info)
        if tipo in ('int2', 'smallint', 'int4', 'integer', 'int8', 'bigint'):
            return random.randint(0, 1)

        if self.faker:
            return self.faker.email()

        dominios = ['gmail.com', 'outlook.com', 'hotmail.com', 'yahoo.com', 'empresa.com']
        nombre = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=8))
        return f"{nombre}@{random.choice(dominios)}"

    def generar_telefono(self, columna_info):
        """Genera un teléfono peruano realista"""
        # Celular peruano: 9XX XXX XXX
        if random.choice([True, False]):
            return f"9{random.randint(10000000, 99999999)}"
        # Teléfono fijo Lima: 01 XXX XXXX
        else:
            return f"01{random.randint(1000000, 9999999)}"

    def generar_direccion(self, columna_info):
        """Genera una dirección realista"""
        if self.faker:
            return self.faker.address().replace('\n', ', ')

        tipos = ['Av.', 'Jr.', 'Calle', 'Psje.']
        nombres = ['Los Olivos', 'Las Flores', 'San Martín', 'Bolognesi', 'Grau']
        return f"{random.choice(tipos)} {random.choice(nombres)} {random.randint(100, 999)}"

    def generar_ciudad(self, columna_info):
        """Genera una ciudad peruana"""
        ciudades = ['Lima', 'Arequipa', 'Cusco', 'Trujillo', 'Chiclayo', 'Piura',
                    'Iquitos', 'Huancayo', 'Tacna', 'Puno', 'Ayacucho']
        return random.choice(ciudades)

    def generar_pais(self, columna_info):
        """Genera un país"""
        if self.faker:
            return self.faker.country()
        paises = ['Perú', 'Argentina', 'Chile', 'Colombia', 'Brasil', 'Ecuador',
                  'México', 'España', 'Estados Unidos']
        return random.choice(paises)

    def generar_codigo_postal(self, columna_info):
        """Genera un código postal peruano"""
        return f"LIMA{random.randint(1, 99):02d}"

    def generar_latitud(self, columna_info):
        """Genera una latitud (Perú: -18.35 a 0)"""
        return round(random.uniform(-18.35, 0), 6)

    def generar_longitud(self, columna_info):
        """Genera una longitud (Perú: -81.33 a -68.65)"""
        return round(random.uniform(-81.33, -68.65), 6)

    def generar_empresa(self, columna_info):
        """Genera un nombre de empresa"""
        if self.faker:
            return self.faker.company()

        prefijos = ['Corporación', 'Empresa', 'Grupo', 'Inversiones', 'Compañía']
        nombres = ['Andina', 'del Sur', 'Pacífico', 'Nacional', 'Global', 'Peruana']
        sufijos = ['S.A.', 'S.A.C.', 'E.I.R.L.', 'S.R.L.']

        return f"{random.choice(prefijos)} {random.choice(nombres)} {random.choice(sufijos)}"

    def generar_estado(self, columna_info):
        """Genera un estado típico"""
        tipo = self._tipo_columna(columna_info)

        if tipo in ('int2', 'smallint', 'int4', 'integer', 'int8', 'bigint'):
            # Si la columna es numérica, devolver un código
            return random.randint(0, 5)

        estados = ['ACTIVO', 'INACTIVO', 'PENDIENTE', 'APROBADO', 'RECHAZADO',
                   'EN_PROCESO', 'COMPLETADO', 'CANCELADO']
        return random.choice(estados)

    def generar_boolean_activo(self, columna_info):
        """Genera un booleano con tendencia a True (80%)"""
        prob = random.random() < 0.8
        tipo = self._tipo_columna(columna_info)

        if tipo in ('int2', 'smallint', 'int4', 'integer', 'int8', 'bigint', 'numeric', 'decimal'):
            return 1 if prob else 0
        if tipo in ('char', 'bpchar', 'varchar', 'text'):
            return '1' if prob else '0'

        return prob

    def generar_usuario(self, columna_info):
        """Genera un nombre de usuario del sistema"""
        usuarios = ['admin', 'sistema', 'operador', 'supervisor', 'usuario1',
                    'analista', 'gestor', 'coordinador']
        return random.choice(usuarios)

    def generar_fecha_creacion(self, columna_info):
        """Genera una fecha de creación (pasado reciente)"""
        dias_atras = random.randint(1, 365)
        return datetime.now() - timedelta(days=dias_atras)

    def generar_fecha_modificacion(self, columna_info):
        """Genera una fecha de modificación (más reciente que creación)"""
        dias_atras = random.randint(0, 180)
        return datetime.now() - timedelta(days=dias_atras)

    def generar_monto(self, columna_info):
        """Genera un monto monetario realista"""
        precision = columna_info.get('precision', 10)
        scale = columna_info.get('scale', 2)

        # Generar montos realistas en rangos comunes
        rangos = [
            (10, 100),      # Montos pequeños
            (100, 1000),    # Montos medianos
            (1000, 10000),  # Montos grandes
            (10000, 100000) # Montos muy grandes
        ]

        rango = random.choice(rangos)
        valor = round(random.uniform(*rango), scale)
        return Decimal(str(valor))

    def generar_porcentaje(self, columna_info):
        """Genera un porcentaje (0-100)"""
        valor = round(random.uniform(0, 100), 2)
        return Decimal(str(valor))

    def generar_url(self, columna_info):
        """Genera una URL realista"""
        if self.faker:
            return self.faker.url()

        dominios = ['ejemplo.com', 'test.com', 'demo.pe', 'sitio.com']
        return f"https://www.{random.choice(dominios)}/pagina/{random.randint(1, 100)}"

    def generar_ip(self, columna_info):
        """Genera una dirección IP"""
        if self.faker:
            return self.faker.ipv4()
        return f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 255)}"

    def generar_codigo(self, columna_info):
        """Genera un código alfanumérico"""
        max_len = columna_info.get('max_length') or 10
        length = min(random.randint(6, 12), max_len)

        letras = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        numeros = '0123456789'

        # Formato: XXX-NNNN
        if length >= 8:
            parte1 = ''.join(random.choices(letras, k=3))
            parte2 = ''.join(random.choices(numeros, k=min(4, length-4)))
            return f"{parte1}-{parte2}"
        else:
            return ''.join(random.choices(letras + numeros, k=length))

    def generar_descripcion(self, columna_info):
        """Genera una descripción realista"""
        if self.faker:
            return self.faker.text(max_nb_chars=min(columna_info.get('max_length', 200), 200))

        descripciones = [
            'Registro generado automáticamente para pruebas del sistema',
            'Entrada de datos de ejemplo para validación',
            'Información de prueba creada por el generador',
            'Dato sintético para testing de la aplicación',
            'Registro de ejemplo con propósitos de desarrollo'
        ]
        return random.choice(descripciones)

    def generar_observacion(self, columna_info):
        """Genera una observación o comentario"""
        if self.faker:
            return self.faker.sentence()

        observaciones = [
            'Sin observaciones',
            'Pendiente de revisión',
            'Verificado correctamente',
            'Requiere seguimiento',
            'En proceso de validación',
            'Aprobado sin inconvenientes'
        ]
        return random.choice(observaciones)

    def generar_abreviatura(self, columna_info):
        """Genera una abreviatura o sigla corta"""
        max_len = columna_info.get('max_length', 10)

        # Determinar longitud de la abreviatura (2-5 caracteres típicamente)
        if max_len <= 2:
            length = 2
        elif max_len <= 3:
            length = 3
        elif max_len <= 5:
            length = random.randint(2, min(4, max_len))
        else:
            length = random.randint(2, 5)

        # Generar abreviatura en mayúsculas
        letras = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        abrev = ''.join(random.choices(letras, k=length))

        return abrev

    # =============================================================================
    # GESTIÓN DE CONFIGURACIÓN
    # =============================================================================

    def cargar_config(self, config_file):
        """Carga configuración desde archivo JSON o usa defaults"""
        config_default = {
            'cantidad_base': 100,
            'cantidad_por_tabla': {},
            'multiplicadores_fk': {
                'habilitado': True,
                'factor': 1.0
            },
            'generacion_nulls': {
                'habilitado': True,
                'probabilidad': 0.2,
                'excluir_pks': True,
                'excluir_fks': False
            },
            'limpieza_previa': {
                'preguntar': True,
                'automatico': False
            },
            'rangos_personalizados': {
                'integer': {'min': 1, 'max': 2147483647},
                'bigint': {'min': 1, 'max': 9223372036854775807},
                'smallint': {'min': 1, 'max': 32767},
                'numeric': {'max_valor': 999999}
            },
            'rangos_fechas': {
                'date': {'dias_atras': 1825, 'dias_adelante': 0},
                'timestamp': {'dias_atras': 730, 'dias_adelante': 0}
            },
            'texto': {
                'max_length_text': 500,
                'palabras_personalizadas': []
            },
            'faker': {
                'habilitado': True,
                'locale': 'es_ES'
            },
            'optimizacion': {
                'usar_copy': True,
                'batch_size': 1000
            },
            'seeds': {
                'random_seed': None
            }
        }

        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_archivo = json.load(f)
                    if 'config_generacion' in config_archivo:
                        config_archivo = config_archivo['config_generacion']

                    # Merge profundo
                    self._merge_config(config_default, config_archivo)
                    print(f"[OK] Configuracion cargada: {config_file}")
            except Exception as e:
                print(f"[WARN] Error cargando config, usando defaults: {e}")

        return config_default

    def _merge_config(self, base, updates):
        """Merge recursivo de configuración"""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    # =============================================================================
    # CONEXIÓN A BASE DE DATOS
    # =============================================================================

    def conectar(self):
        """Establece conexión a la base de datos"""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.puerto,
                database=self.bd,
                user=self.usuario,
                password=self.password
            )
            self.cursor = self.conn.cursor()
            print(f"[OK] Conectado a PostgreSQL: {self.bd}")
            return True
        except Exception as e:
            print(f"[ERROR] Error al conectar: {e}")
            return False

    def desconectar(self):
        """Cierra la conexión a la base de datos"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()

    # =============================================================================
    # ANÁLISIS DE METADATA (INGENIERÍA INVERSA)
    # =============================================================================

    def analizar_base_datos(self):
        """Realiza ingeniería inversa completa del esquema de BD"""
        print(f"\n{'='*70}")
        print(f"ANALISIS DE ESTRUCTURA DE BASE DE DATOS")
        print(f"{'='*70}\n")
        print(f"Esquema: {self.esquema}")

        # 1. Obtener tablas
        self.metadata['tablas'] = self.obtener_tablas()
        print(f"[OK] Tablas: {len(self.metadata['tablas'])}")

        # 2. Obtener columnas
        for tabla in self.metadata['tablas']:
            self.metadata['columnas'][tabla] = self.obtener_columnas(tabla)
        print(f"[OK] Columnas analizadas")

        # 3. Primary Keys
        self.metadata['pks'] = self.obtener_primary_keys()
        print(f"[OK] Primary Keys: {len(self.metadata['pks'])}")

        # 4. Foreign Keys
        self.metadata['fks'] = self.obtener_foreign_keys()
        total_fks = sum(len(fks) for fks in self.metadata['fks'].values())
        print(f"[OK] Foreign Keys: {total_fks}")

        # 5. CHECK Constraints
        self.metadata['checks'] = self.obtener_check_constraints()
        print(f"[OK] CHECK Constraints: {sum(len(c) for c in self.metadata['checks'].values())}")

        # 6. UNIQUE Constraints
        self.metadata['uniques'] = self.obtener_unique_constraints()
        print(f"[OK] UNIQUE Constraints: {sum(len(u) for u in self.metadata['uniques'].values())}")

        # 7. Sequences
        self.metadata['sequences'] = self.obtener_sequences()
        print(f"[OK] Sequences: {len(self.metadata['sequences'])}")

        # 8. Indices
        self.metadata['indices'] = self.obtener_indices()
        print(f"[OK] Indices: {sum(len(i) for i in self.metadata['indices'].values())}")

        # 9. Resolver orden de carga
        self.metadata['orden_carga'] = self.resolver_orden_carga()
        print(f"[OK] Orden de carga resuelto: {len(self.metadata['orden_carga'])} tablas")

        # 10. Analisis de contexto semantico
        self._analizar_contexto_semantico()

        print(f"\n{'='*70}")
        print(f"[OK] ANALISIS COMPLETADO")
        print(f"{'='*70}\n")

    def _analizar_contexto_semantico(self):
        """Analiza y muestra el contexto semántico inferido de las columnas"""
        print(f"\nAnalisis de Contexto Semantico:")

        contextos_encontrados = defaultdict(list)

        for tabla, columnas in self.metadata['columnas'].items():
            for columna in columnas:
                generador = self.inferir_contexto_columna(columna['nombre'])
                if generador:
                    contextos_encontrados[generador].append(f"{tabla}.{columna['nombre']}")

        if contextos_encontrados:
            print(f"  [OK] Detectados {len(contextos_encontrados)} tipos de contexto:")
            for generador, columnas in sorted(contextos_encontrados.items()):
                print(f"    - {generador}: {len(columnas)} columna(s)")
        else:
            print(f"  [INFO] No se detectaron contextos especiales (se usaran generadores por tipo)")

    def obtener_tablas(self):
        """Obtiene lista de tablas del esquema"""
        query = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = %s
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
        """
        self.cursor.execute(query, (self.esquema,))
        return [row[0] for row in self.cursor.fetchall()]

    def obtener_columnas(self, tabla):
        """Obtiene información detallada de columnas"""
        query = """
        SELECT
            c.column_name,
            c.data_type,
            c.udt_name,
            c.character_maximum_length,
            c.numeric_precision,
            c.numeric_scale,
            c.is_nullable,
            c.column_default,
            c.ordinal_position
        FROM information_schema.columns c
        WHERE c.table_schema = %s
        AND c.table_name = %s
        ORDER BY c.ordinal_position
        """
        self.cursor.execute(query, (self.esquema, tabla))

        columnas = []
        for row in self.cursor.fetchall():
            columnas.append({
                'nombre': row[0],
                'tipo_dato': row[1],
                'udt_name': row[2],
                'max_length': row[3],
                'precision': row[4],
                'scale': row[5],
                'nullable': row[6] == 'YES',
                'default': row[7],
                'posicion': row[8]
            })

        return columnas

    def obtener_primary_keys(self):
        """Obtiene primary keys de todas las tablas"""
        query = """
        SELECT
            tc.table_name,
            kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema = %s
        AND tc.constraint_type = 'PRIMARY KEY'
        ORDER BY tc.table_name, kcu.ordinal_position
        """
        self.cursor.execute(query, (self.esquema,))

        pks = defaultdict(list)
        for row in self.cursor.fetchall():
            pks[row[0]].append(row[1])

        return dict(pks)

    def obtener_foreign_keys(self):
        """Obtiene foreign keys de todas las tablas"""
        query = """
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS tabla_referenciada,
            ccu.column_name AS columna_referenciada
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        JOIN information_schema.constraint_column_usage ccu
            ON ccu.constraint_name = tc.constraint_name
            AND ccu.table_schema = tc.table_schema
        WHERE tc.table_schema = %s
        AND tc.constraint_type = 'FOREIGN KEY'
        ORDER BY tc.table_name
        """
        self.cursor.execute(query, (self.esquema,))

        fks = defaultdict(list)
        for row in self.cursor.fetchall():
            fks[row[0]].append({
                'columna': row[1],
                'tabla_ref': row[2],
                'columna_ref': row[3]
            })

        return dict(fks)

    def obtener_check_constraints(self):
        """Obtiene CHECK constraints"""
        query = """
        SELECT
            tc.table_name,
            cc.check_clause
        FROM information_schema.table_constraints tc
        JOIN information_schema.check_constraints cc
            ON tc.constraint_name = cc.constraint_name
        WHERE tc.table_schema = %s
        AND tc.constraint_type = 'CHECK'
        """
        self.cursor.execute(query, (self.esquema,))

        checks = defaultdict(list)
        for row in self.cursor.fetchall():
            checks[row[0]].append(row[1])

        return dict(checks)

    def obtener_unique_constraints(self):
        """Obtiene UNIQUE constraints"""
        query = """
        SELECT
            tc.table_name,
            kcu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
            ON tc.constraint_name = kcu.constraint_name
            AND tc.table_schema = kcu.table_schema
        WHERE tc.table_schema = %s
        AND tc.constraint_type = 'UNIQUE'
        ORDER BY tc.table_name
        """
        self.cursor.execute(query, (self.esquema,))

        uniques = defaultdict(list)
        for row in self.cursor.fetchall():
            uniques[row[0]].append(row[1])

        return dict(uniques)

    def obtener_sequences(self):
        """Obtiene sequences disponibles"""
        query = """
        SELECT
            sequence_name,
            data_type,
            start_value,
            minimum_value,
            maximum_value,
            increment
        FROM information_schema.sequences
        WHERE sequence_schema = %s
        """
        self.cursor.execute(query, (self.esquema,))

        sequences = {}
        for row in self.cursor.fetchall():
            sequences[row[0]] = {
                'tipo': row[1],
                'inicio': row[2],
                'minimo': row[3],
                'maximo': row[4],
                'incremento': row[5]
            }

        return sequences

    def obtener_indices(self):
        """Obtiene índices de las tablas"""
        query = """
        SELECT
            tablename,
            indexname,
            indexdef
        FROM pg_indexes
        WHERE schemaname = %s
        ORDER BY tablename, indexname
        """
        self.cursor.execute(query, (self.esquema,))

        indices = defaultdict(list)
        for row in self.cursor.fetchall():
            indices[row[0]].append({
                'nombre': row[1],
                'definicion': row[2]
            })

        return dict(indices)

    def resolver_orden_carga(self):
        """
        Resuelve el orden de carga respetando dependencias FK.
        Maneja ciclos y auto-referencias.
        """
        # Construir grafo de dependencias
        dependencias = defaultdict(set)
        sin_dependencias = set(self.metadata['tablas'])

        for tabla, fks in self.metadata['fks'].items():
            if fks:
                for fk in fks:
                    tabla_ref = fk['tabla_ref']
                    if tabla_ref != tabla:  # Evitar auto-referencias
                        dependencias[tabla].add(tabla_ref)
                        sin_dependencias.discard(tabla)

        # Ordenamiento topológico con Kahn's algorithm
        orden = []
        procesadas = set()
        en_proceso = set()

        def visitar_tabla(tabla):
            if tabla in procesadas:
                return True

            if tabla in en_proceso:
                # Ciclo detectado
                print(f"  [WARN] Ciclo detectado en: {tabla}")
                return False

            en_proceso.add(tabla)

            # Visitar dependencias
            if tabla in dependencias:
                for dep in dependencias[tabla]:
                    visitar_tabla(dep)

            en_proceso.discard(tabla)

            if tabla not in procesadas:
                orden.append(tabla)
                procesadas.add(tabla)

            return True

        # Primero tablas sin dependencias
        for tabla in sorted(sin_dependencias):
            visitar_tabla(tabla)

        # Luego las que tienen dependencias
        for tabla in sorted(self.metadata['tablas']):
            visitar_tabla(tabla)

        return orden

    # =============================================================================
    # GENERACIÓN DE DATOS
    # =============================================================================

    def generar_valor_columna(self, tabla, columna_info, registro_actual=None):
        """
        Genera un valor para una columna usando inferencia semántica.
        Este es el método central que orquesta la generación inteligente.
        """
        nombre_col = columna_info['nombre']
        tipo = columna_info['udt_name'] or columna_info['tipo_dato']

        # 1. Si es FK, obtener valor de tabla referenciada
        if tabla in self.metadata['fks']:
            for fk in self.metadata['fks'][tabla]:
                if fk['columna'] == nombre_col:
                    return self.obtener_valor_fk(fk['tabla_ref'], fk['columna_ref'])

        # 2. Si es PK con sequence, dejar que BD lo maneje
        if tabla in self.metadata['pks'] and nombre_col in self.metadata['pks'][tabla]:
            if columna_info['default'] and 'nextval' in str(columna_info['default']):
                return None

        # 3. Manejo de NULL según configuración
        if self._debe_generar_null(tabla, nombre_col, columna_info):
            return None

        # 4. INFERENCIA SEMÁNTICA: Buscar generador específico por contexto
        generador_nombre = self.inferir_contexto_columna(nombre_col)
        if generador_nombre:
            try:
                generador = getattr(self, generador_nombre)
                valor = generador(columna_info)

                # Garantizar unicidad si es UNIQUE
                if tabla in self.metadata['uniques'] and nombre_col in self.metadata['uniques'][tabla]:
                    valor = self._garantizar_unicidad(tabla, nombre_col, valor, generador, columna_info)

                return valor
            except Exception as e:
                print(f"  [WARN] Error en generador {generador_nombre}: {e}")
                # Fall back a generacion por tipo

        # 5. Fall back: Generación por tipo de dato
        return self.generar_por_tipo(tipo, columna_info)

    def _debe_generar_null(self, tabla, nombre_col, columna_info):
        """Determina si debe generar NULL para esta columna"""
        if not columna_info['nullable']:
            return False

        if not self.config['generacion_nulls']['habilitado']:
            return False

        # Verificar exclusiones
        es_pk = tabla in self.metadata['pks'] and nombre_col in self.metadata['pks'][tabla]
        if es_pk and self.config['generacion_nulls']['excluir_pks']:
            return False

        es_fk = False
        if tabla in self.metadata['fks']:
            es_fk = any(fk['columna'] == nombre_col for fk in self.metadata['fks'][tabla])
        if es_fk and self.config['generacion_nulls']['excluir_fks']:
            return False

        # Aplicar probabilidad
        return random.random() < self.config['generacion_nulls']['probabilidad']

    def _garantizar_unicidad(self, tabla, columna, valor, generador, columna_info):
        """Garantiza que el valor sea único para constraints UNIQUE"""
        cache_key = f"{tabla}.{columna}"

        if cache_key not in self.generated_values:
            self.generated_values[cache_key] = set()

        intentos = 0
        max_intentos = 1000

        while valor in self.generated_values[cache_key] and intentos < max_intentos:
            valor = generador(columna_info)
            intentos += 1

        if intentos >= max_intentos:
            # Agregar sufijo único
            import uuid
            if isinstance(valor, str):
                valor = f"{valor}_{uuid.uuid4().hex[:6]}"

        self.generated_values[cache_key].add(valor)
        return valor

    def generar_por_tipo(self, tipo, columna_info):
        """Genera valor según tipo de dato (fallback)"""
        tipo = tipo.lower()

        # VARCHAR / CHAR / TEXT
        if tipo in ('varchar', 'character varying', 'bpchar', 'char', 'character'):
            max_len = columna_info['max_length'] or self.config.get('texto', {}).get('max_length_text', 50)
            return self.generar_texto_basico(max_len)

        elif tipo == 'text':
            max_len_cfg = self.config.get('texto', {}).get('max_length_text', 200)
            return self.generar_texto_basico(min(random.randint(50, 200), max_len_cfg))

        # INTEGER
        elif tipo in ('int4', 'integer'):
            cfg = self.config['rangos_personalizados']['integer']
            return random.randint(cfg['min'], min(cfg['max'], 2147483647))

        # BIGINT
        elif tipo in ('int8', 'bigint'):
            cfg = self.config['rangos_personalizados']['bigint']
            return random.randint(cfg['min'], min(cfg['max'], 9223372036854775807))

        # SMALLINT
        elif tipo in ('int2', 'smallint'):
            cfg = self.config['rangos_personalizados']['smallint']
            return random.randint(cfg['min'], min(cfg['max'], 32767))

        # NUMERIC / DECIMAL
        elif tipo in ('numeric', 'decimal'):
            precision = columna_info['precision'] or 10
            scale = columna_info['scale'] or 2
            max_val = 10 ** (precision - scale) - 1
            valor = round(random.uniform(0, max_val), scale)
            return Decimal(str(valor))

        # FLOAT / REAL / DOUBLE
        elif tipo in ('float4', 'float8', 'real', 'double precision'):
            return round(random.uniform(0, 10000), 2)

        # DATE
        elif tipo == 'date':
            cfg = self.config['rangos_fechas']['date']
            dias_atras = random.randint(0, cfg['dias_atras'])
            return (datetime.now() - timedelta(days=dias_atras)).date()

        # TIMESTAMP
        elif tipo in ('timestamp', 'timestamptz', 'timestamp without time zone', 'timestamp with time zone'):
            cfg = self.config['rangos_fechas']['timestamp']
            dias_atras = random.randint(0, cfg['dias_atras'])
            return datetime.now() - timedelta(days=dias_atras, hours=random.randint(0, 23))

        # TIME
        elif tipo in ('time', 'time without time zone'):
            return f"{random.randint(0, 23):02d}:{random.randint(0, 59):02d}:{random.randint(0, 59):02d}"

        # BOOLEAN
        elif tipo in ('bool', 'boolean'):
            return random.choice([True, False])

        # UUID
        elif tipo == 'uuid':
            import uuid
            return str(uuid.uuid4())

        # JSON / JSONB
        elif tipo in ('json', 'jsonb'):
            return json.dumps({
                'id': random.randint(1, 1000),
                'valor': self.generar_texto_basico(20),
                'activo': random.choice([True, False])
            })

        # ARRAY
        elif tipo.endswith('[]'):
            base_type = tipo[:-2]
            cantidad = random.randint(1, 5)
            return [self.generar_por_tipo(base_type, columna_info) for _ in range(cantidad)]

        # DEFAULT
        else:
            return self.generar_texto_basico(50)

    def generar_texto_basico(self, max_len):
        """Genera texto básico (usado como fallback)"""
        palabras = [
            'lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur', 'adipiscing', 'elit',
            'sed', 'eiusmod', 'tempor', 'incididunt', 'labore', 'dolore', 'magna', 'aliqua'
        ]

        texto = ''
        while len(texto) < max_len:
            palabra = random.choice(palabras)
            if len(texto) + len(palabra) + 1 <= max_len:
                texto += palabra + ' '
            else:
                break

        return texto.strip()[:max_len]

    def obtener_valor_fk(self, tabla_ref, columna_ref):
        """Obtiene un valor válido de una tabla referenciada"""
        cache_key = f"{tabla_ref}.{columna_ref}"

        # Si tenemos valores en cache, usar uno aleatorio
        if cache_key in self.data_cache and self.data_cache[cache_key]:
            return random.choice(self.data_cache[cache_key])

        # Obtener valores de la tabla referenciada
        tabla_completa = f"{self.esquema}.{tabla_ref}"
        query = f'SELECT "{columna_ref}" FROM {tabla_completa} WHERE "{columna_ref}" IS NOT NULL LIMIT 1000'

        try:
            self.cursor.execute(query)
            valores = [row[0] for row in self.cursor.fetchall()]

            if valores:
                self.data_cache[cache_key] = valores
                return random.choice(valores)
            else:
                return None
        except Exception as e:
            print(f"  [WARN] Error obteniendo FK {tabla_ref}.{columna_ref}: {e}")
            return None

    def generar_registros_tabla(self, tabla, cantidad):
        """Genera registros para una tabla"""
        registros = []
        columnas = self.metadata['columnas'][tabla]
        registros_saltados = 0
        columnas_procesadas = 0
        columnas_con_default = 0

        for i in range(cantidad):
            registro = {}
            registro_valido = True

            for columna in columnas:
                nombre_col = columna['nombre']

                # Saltar columnas con DEFAULT que usan sequences
                if columna['default'] and 'nextval' in str(columna['default']):
                    columnas_con_default += 1
                    continue

                columnas_procesadas += 1
                valor = self.generar_valor_columna(tabla, columna, registro)

                # Validar columna requerida
                if valor is None and not columna['nullable']:
                    # Columna requerida sin valor, saltar este registro
                    registro_valido = False
                    registros_saltados += 1
                    break

                registro[nombre_col] = valor

            if registro_valido and registro:
                registros.append(registro)

        # Diagnostico
        if len(registros) == 0:
            print(f"  [WARN] 0 registros generados para {tabla}")
            print(f"  - Columnas totales: {len(columnas)}")
            print(f"  - Columnas con DEFAULT/sequence: {columnas_con_default}")
            print(f"  - Columnas procesadas: {columnas_procesadas}")
            print(f"  - Registros saltados por validacion: {registros_saltados}")

            # Mostrar primera columna problematica
            if columnas_procesadas > 0 and registros_saltados == cantidad:
                print(f"  [WARN] Todas las iteraciones fueron saltadas - revisar FKs o columnas requeridas")

        # Advertir si se saltaron registros
        elif registros_saltados > 0:
            print(f"  [WARN] {registros_saltados} registros saltados por columnas requeridas sin valor")

        return registros

    # =============================================================================
    # INSERCIÓN OPTIMIZADA
    # =============================================================================

    def insertar_registros(self, tabla, registros):
        """
        Inserta registros usando el método más eficiente.
        Usa COPY si está habilitado, sino execute_batch.
        """
        if not registros:
            return 0

        usar_copy = self.config.get('optimizacion', {}).get('usar_copy', True)

        if usar_copy:
            return self._insertar_con_copy(tabla, registros)
        else:
            return self._insertar_con_batch(tabla, registros)

    def _insertar_con_copy(self, tabla, registros):
        """Inserción masiva usando COPY (más rápido)"""
        if not registros:
            return 0

        try:
            columnas = list(registros[0].keys())
            tabla_completa = f"{self.esquema}.{tabla}"

            # Crear StringIO con datos en formato CSV
            output = io.StringIO()
            writer = csv.writer(output, delimiter='\t', quotechar='"',
                               quoting=csv.QUOTE_MINIMAL, lineterminator='\n')

            for registro in registros:
                fila = []
                for col in columnas:
                    valor = registro.get(col)

                    # Conversión de tipos para COPY
                    if valor is None:
                        fila.append('\\N')
                    elif isinstance(valor, (datetime, )):
                        fila.append(valor.isoformat())
                    elif isinstance(valor, bool):
                        fila.append('t' if valor else 'f')
                    elif isinstance(valor, (list, dict)):
                        fila.append(json.dumps(valor))
                    else:
                        fila.append(str(valor))

                writer.writerow(fila)

            # Ejecutar COPY
            output.seek(0)
            columnas_str = ', '.join([f'"{col}"' for col in columnas])

            self.cursor.copy_expert(
                f"COPY {tabla_completa} ({columnas_str}) FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t', NULL '\\N', QUOTE '\"')",
                output
            )

            self.conn.commit()

            # Actualizar cache
            self._actualizar_cache_insercion(tabla, registros, columnas)

            return len(registros)

        except Exception as e:
            self.conn.rollback()
            print(f"  [ERROR] Error con COPY en {tabla}: {e}")
            print(f"  [INFO] Intentando con execute_batch...")
            # Fallback a execute_batch
            return self._insertar_con_batch(tabla, registros)

    def _insertar_con_batch(self, tabla, registros):
        """Inserción usando execute_batch (fallback)"""
        if not registros:
            return 0

        try:
            columnas = list(registros[0].keys())
            tabla_completa = f"{self.esquema}.{tabla}"

            columnas_str = ', '.join([f'"{col}"' for col in columnas])
            placeholders = ', '.join(['%s'] * len(columnas))

            query = f'INSERT INTO {tabla_completa} ({columnas_str}) VALUES ({placeholders})'

            datos = []
            for registro in registros:
                fila = [registro.get(col) for col in columnas]
                datos.append(tuple(fila))

            batch_size = self.config.get('optimizacion', {}).get('batch_size', 1000)
            execute_batch(self.cursor, query, datos, page_size=batch_size)
            self.conn.commit()

            # Actualizar cache
            self._actualizar_cache_insercion(tabla, registros, columnas)

            return len(registros)

        except Exception as e:
            self.conn.rollback()
            print(f"  [ERROR] Error insertando en {tabla}: {e}")
            self.stats['errores'].append(f"{tabla}: {str(e)}")
            return 0

    def _actualizar_cache_insercion(self, tabla, registros, columnas):
        """Actualiza el cache con valores insertados (para FKs)"""
        if tabla in self.metadata['pks']:
            for pk_col in self.metadata['pks'][tabla]:
                if pk_col in columnas:
                    cache_key = f"{tabla}.{pk_col}"
                    valores = [
                        registro[pk_col]
                        for registro in registros
                        if pk_col in registro and registro[pk_col] is not None
                    ]
                    if cache_key not in self.data_cache:
                        self.data_cache[cache_key] = []
                    self.data_cache[cache_key].extend(valores)

    # =============================================================================
    # PROCESO PRINCIPAL
    # =============================================================================

    def generar_data_completa(self, cantidad_base=None):
        """Genera data de prueba para todas las tablas"""
        if cantidad_base is None:
            cantidad_base = self.config.get('cantidad_base', 100)

        self.stats['tiempo_inicio'] = datetime.now()

        print(f"\n{'='*70}")
        print(f"GENERACION DE DATA DE PRUEBA")
        print(f"{'='*70}\n")
        print(f"Cantidad base: {cantidad_base} registros")
        print(f"Tablas a procesar: {len(self.metadata['orden_carga'])}")
        print(f"Metodo de insercion: {'COPY' if self.config.get('optimizacion', {}).get('usar_copy') else 'INSERT BATCH'}\n")

        total_insertados = 0

        for i, tabla in enumerate(self.metadata['orden_carga'], 1):
            print(f"[{i}/{len(self.metadata['orden_carga'])}] {tabla}")

            # Calcular cantidad de registros
            cantidad = self.config.get('cantidad_por_tabla', {}).get(tabla, cantidad_base)

            # Multiplicador por FKs
            if (self.config['multiplicadores_fk']['habilitado'] and
                tabla in self.metadata['fks'] and self.metadata['fks'][tabla]):
                factor = self.config['multiplicadores_fk']['factor']
                cantidad = int(cantidad_base * len(self.metadata['fks'][tabla]) * factor)

            print(f"  -> Generando {cantidad} registros...")
            registros = self.generar_registros_tabla(tabla, cantidad)

            print(f"  -> Insertando...")
            insertados = self.insertar_registros(tabla, registros)

            if insertados > 0:
                print(f"  [OK] {insertados} registros insertados\n")
                total_insertados += insertados
                self.stats['por_tabla'][tabla] = insertados
            else:
                print(f"  [WARN] 0 registros insertados\n")
                self.stats['por_tabla'][tabla] = 0

        self.stats['tiempo_fin'] = datetime.now()
        self.stats['total_registros'] = total_insertados

        self._mostrar_reporte_final()

    def _mostrar_reporte_final(self):
        """Muestra reporte final de la generación"""
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
                tasa = self.stats['total_registros'] / duracion
                print(f"  - Tasa de insercion: {tasa:.0f} registros/segundo")

        if self.stats['errores']:
            print(f"\n[WARN] Errores encontrados: {len(self.stats['errores'])}")
            for error in self.stats['errores'][:5]:
                print(f"  - {error}")

        print(f"\n{'='*70}\n")

    def limpiar_tablas(self):
        """Limpia todas las tablas del esquema"""
        print(f"\nLimpiando tablas existentes...")

        for tabla in reversed(self.metadata['orden_carga']):
            try:
                tabla_completa = f"{self.esquema}.{tabla}"
                self.cursor.execute(f'TRUNCATE TABLE {tabla_completa} CASCADE')
                self.conn.commit()
                print(f"  [OK] {tabla}")
            except Exception as e:
                print(f"  [ERROR] Error en {tabla}: {e}")
                self.conn.rollback()


def main():
    """Función principal"""
    # Configurar encoding para Windows
    if sys.platform == 'win32':
        try:
            import io
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except:
            pass

    if len(sys.argv) < 7:
        print("Error: Faltan parámetros")
        print("Uso: python data_prueba.py <host> <puerto> <bd> <usuario> <password> <esquema> [cantidad]")
        sys.exit(1)

    host = sys.argv[1]
    puerto = sys.argv[2]
    bd = sys.argv[3]
    usuario = sys.argv[4]
    password = sys.argv[5]
    esquema = sys.argv[6]
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
        # Análisis de estructura (ingeniería inversa)
        generator.analizar_base_datos()

        # Limpiar datos existentes
        if generator.config['limpieza_previa']['automatico']:
            generator.limpiar_tablas()
        elif generator.config['limpieza_previa']['preguntar']:
            # Si no hay terminal interactiva (ejecución desde GUI), no limpiar por defecto
            try:
                respuesta = input("\n¿Limpiar tablas antes de insertar? (s/n): ")
                if respuesta.lower() == 's':
                    generator.limpiar_tablas()
            except EOFError:
                # No hay entrada disponible (GUI), continuar sin limpiar
                print("\n[INFO] Modo no interactivo detectado. Continuando sin limpieza previa.")
                print("[INFO] Para limpiar tablas automaticamente, configura 'limpieza_previa.automatico': true")

        # Generar data inteligente
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
