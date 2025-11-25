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


class DataPruebaGenerator:
    """
    Generador genérico de data de prueba para PostgreSQL.
    Analiza la metadata de la BD y genera datos coherentes respetando todas las constraints.
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
        self.metadata = {
            'tablas': [],
            'columnas': {},
            'pks': {},
            'fks': {},
            'checks': {},
            'uniques': {},
            'sequences': {},
            'orden_carga': []
        }
        self.data_cache = {}  # Cache de valores FK
        
        # Cargar configuración
        base_dir = Path(__file__).resolve().parent
        if config_file is None:
            config_file = base_dir.parent / "resources" / "config_data_prueba.json"
        self.config = self.cargar_config(config_file)
        
        # Aplicar seed si está configurado
        if self.config.get('seeds', {}).get('random_seed'):
            random.seed(self.config['seeds']['random_seed'])
    
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
            }
        }
        
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_archivo = json.load(f)
                    # Merge con defaults
                    if 'config_generacion' in config_archivo:
                        config_archivo = config_archivo['config_generacion']
                    config_default.update(config_archivo)
                    print(f"✓ Configuración cargada desde: {config_file}")
            except Exception as e:
                print(f"⚠ Error cargando config, usando defaults: {e}")
        
        return config_default
        
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
            print(f"✓ Conectado a PostgreSQL: {self.bd}")
            return True
        except Exception as e:
            print(f"✗ Error al conectar: {e}")
            return False
    
    def desconectar(self):
        """Cierra la conexión a la base de datos"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def analizar_base_datos(self):
        """Analiza la estructura completa de la base de datos"""
        print(f"\n{'='*70}")
        print(f"🔍 ANALIZANDO ESTRUCTURA DE LA BASE DE DATOS")
        print(f"{'='*70}\n")
        
        print(f"Esquema: {self.esquema}")
        
        # 1. Obtener tablas
        self.metadata['tablas'] = self.obtener_tablas()
        print(f"✓ Tablas encontradas: {len(self.metadata['tablas'])}")
        
        # 2. Obtener columnas por tabla
        for tabla in self.metadata['tablas']:
            self.metadata['columnas'][tabla] = self.obtener_columnas(tabla)
        print(f"✓ Metadata de columnas extraída")
        
        # 3. Obtener primary keys
        self.metadata['pks'] = self.obtener_primary_keys()
        print(f"✓ Primary keys identificadas: {len(self.metadata['pks'])}")
        
        # 4. Obtener foreign keys
        self.metadata['fks'] = self.obtener_foreign_keys()
        print(f"✓ Foreign keys identificadas: {sum(len(fks) for fks in self.metadata['fks'].values())}")
        
        # 5. Obtener CHECK constraints
        self.metadata['checks'] = self.obtener_check_constraints()
        print(f"✓ CHECK constraints encontradas: {sum(len(checks) for checks in self.metadata['checks'].values())}")
        
        # 6. Obtener UNIQUE constraints
        self.metadata['uniques'] = self.obtener_unique_constraints()
        print(f"✓ UNIQUE constraints encontradas: {sum(len(uniques) for uniques in self.metadata['uniques'].values())}")
        
        # 7. Obtener sequences
        self.metadata['sequences'] = self.obtener_sequences()
        print(f"✓ Sequences encontradas: {len(self.metadata['sequences'])}")
        
        # 8. Resolver orden de carga
        self.metadata['orden_carga'] = self.resolver_orden_carga()
        print(f"✓ Orden de carga resuelto: {len(self.metadata['orden_carga'])} tablas")
        
        print(f"\n{'='*70}")
        print(f"✓ ANÁLISIS COMPLETADO")
        print(f"{'='*70}\n")
    
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
        """Obtiene información detallada de columnas de una tabla"""
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
        """Obtiene las primary keys de todas las tablas"""
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
        """Obtiene las foreign keys de todas las tablas"""
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
        """Obtiene los CHECK constraints"""
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
        """Obtiene los UNIQUE constraints"""
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
        """Obtiene las sequences disponibles"""
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
    
    def resolver_orden_carga(self):
        """Resuelve el orden de carga de tablas respetando dependencias FK"""
        # Construir grafo de dependencias
        dependencias = defaultdict(set)
        sin_dependencias = set(self.metadata['tablas'])
        
        for tabla, fks in self.metadata['fks'].items():
            if fks:
                sin_dependencias.discard(tabla)
                for fk in fks:
                    tabla_ref = fk['tabla_ref']
                    if tabla_ref != tabla:  # Evitar auto-referencias
                        dependencias[tabla].add(tabla_ref)
        
        # Algoritmo de ordenamiento topológico
        orden = []
        procesadas = set()
        
        def procesar_tabla(tabla):
            if tabla in procesadas:
                return
            
            # Procesar dependencias primero
            if tabla in dependencias:
                for dep in dependencias[tabla]:
                    procesar_tabla(dep)
            
            if tabla not in procesadas:
                orden.append(tabla)
                procesadas.add(tabla)
        
        # Primero las tablas sin dependencias
        for tabla in sorted(sin_dependencias):
            procesar_tabla(tabla)
        
        # Luego las que tienen dependencias
        for tabla in sorted(self.metadata['tablas']):
            procesar_tabla(tabla)
        
        return orden
    
    def generar_valor_columna(self, tabla, columna_info, registro_actual=None):
        """Genera un valor apropiado para una columna según su tipo y constraints"""
        nombre_col = columna_info['nombre']
        tipo = columna_info['udt_name'] or columna_info['tipo_dato']
        
        # Si es FK, obtener valor de tabla referenciada
        if tabla in self.metadata['fks']:
            for fk in self.metadata['fks'][tabla]:
                if fk['columna'] == nombre_col:
                    return self.obtener_valor_fk(fk['tabla_ref'], fk['columna_ref'])
        
        # Si es PK con sequence
        if tabla in self.metadata['pks'] and nombre_col in self.metadata['pks'][tabla]:
            if columna_info['default'] and 'nextval' in str(columna_info['default']):
                return None  # Dejar que la BD use la sequence
        
        # Si permite NULL (según configuración)
        if columna_info['nullable'] and self.config['generacion_nulls']['habilitado']:
            # No NULL en PKs si está configurado
            es_pk = tabla in self.metadata['pks'] and nombre_col in self.metadata['pks'][tabla]
            es_fk = False
            if tabla in self.metadata['fks']:
                es_fk = any(fk['columna'] == nombre_col for fk in self.metadata['fks'][tabla])
            
            excluir_pk = self.config['generacion_nulls']['excluir_pks'] and es_pk
            excluir_fk = self.config['generacion_nulls']['excluir_fks'] and es_fk
            
            if not excluir_pk and not excluir_fk:
                if random.random() < self.config['generacion_nulls']['probabilidad']:
                    return None
        
        # Generación según tipo de dato
        return self.generar_por_tipo(tipo, columna_info)
    
    def generar_por_tipo(self, tipo, columna_info):
        """Genera un valor según el tipo de dato"""
        tipo = tipo.lower()
        
        # VARCHAR / CHAR / TEXT
        if tipo in ('varchar', 'character varying', 'bpchar', 'char', 'character'):
            max_len = columna_info['max_length'] or 50
            return self.generar_texto(max_len)
        
        elif tipo == 'text':
            return self.generar_texto_largo()
        
        # INTEGER
        elif tipo in ('int4', 'integer'):
            return random.randint(1, 2147483647)
        
        # BIGINT
        elif tipo in ('int8', 'bigint'):
            return random.randint(1, 9223372036854775807)
        
        # SMALLINT
        elif tipo in ('int2', 'smallint'):
            return random.randint(1, 32767)
        
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
            dias_atras = random.randint(0, 1825)  # 5 años
            return (datetime.now() - timedelta(days=dias_atras)).date()
        
        # TIMESTAMP
        elif tipo in ('timestamp', 'timestamptz', 'timestamp without time zone', 'timestamp with time zone'):
            dias_atras = random.randint(0, 730)  # 2 años
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
                'valor': self.generar_texto(20),
                'activo': random.choice([True, False])
            })
        
        # ARRAY
        elif tipo.endswith('[]'):
            base_type = tipo[:-2]
            cantidad = random.randint(1, 5)
            return [self.generar_por_tipo(base_type, columna_info) for _ in range(cantidad)]
        
        # DEFAULT
        else:
            return self.generar_texto(50)
    
    def generar_texto(self, max_len):
        """Genera texto aleatorio de longitud específica"""
        palabras = [
            'Lorem', 'ipsum', 'dolor', 'sit', 'amet', 'consectetur', 'adipiscing', 'elit',
            'sed', 'do', 'eiusmod', 'tempor', 'incididunt', 'ut', 'labore', 'et', 'dolore',
            'magna', 'aliqua', 'enim', 'ad', 'minim', 'veniam', 'quis', 'nostrud',
            'exercitation', 'ullamco', 'laboris', 'nisi', 'aliquip', 'ex', 'ea', 'commodo',
            'consequat', 'duis', 'aute', 'irure', 'in', 'reprehenderit', 'voluptate',
            'velit', 'esse', 'cillum', 'fugiat', 'nulla', 'pariatur', 'excepteur', 'sint',
            'occaecat', 'cupidatat', 'non', 'proident', 'sunt', 'culpa', 'qui', 'officia',
            'deserunt', 'mollit', 'anim', 'id', 'est', 'laborum'
        ]
        
        texto = ''
        while len(texto) < max_len:
            palabra = random.choice(palabras)
            if len(texto) + len(palabra) + 1 <= max_len:
                texto += palabra + ' '
            else:
                break
        
        return texto.strip()[:max_len]
    
    def generar_texto_largo(self):
        """Genera texto largo para campos TEXT"""
        return self.generar_texto(random.randint(100, 500))
    
    def obtener_valor_fk(self, tabla_ref, columna_ref):
        """Obtiene un valor válido de una tabla referenciada"""
        cache_key = f"{tabla_ref}.{columna_ref}"
        
        # Si ya tenemos valores en cache, usar uno aleatorio
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
                # La tabla referenciada está vacía - retornar None
                return None
        except Exception as e:
            print(f"⚠ Warning: No se pudo obtener valor FK de {tabla_ref}.{columna_ref}: {e}")
            return None
    
    def generar_registros_tabla(self, tabla, cantidad):
        """Genera registros para una tabla"""
        registros = []
        columnas = self.metadata['columnas'][tabla]
        
        for i in range(cantidad):
            registro = {}
            
            for columna in columnas:
                nombre_col = columna['nombre']
                
                # Saltar columnas con DEFAULT que usan sequences
                if columna['default'] and 'nextval' in str(columna['default']):
                    continue
                
                valor = self.generar_valor_columna(tabla, columna, registro)
                
                # Si es FK y no pudimos obtener valor, saltar este registro
                if valor is None and tabla in self.metadata['fks']:
                    for fk in self.metadata['fks'][tabla]:
                        if fk['columna'] == nombre_col and not columna['nullable']:
                            break
                    else:
                        registro[nombre_col] = valor
                else:
                    registro[nombre_col] = valor
            
            # Solo agregar registro si tiene valores
            if registro:
                registros.append(registro)
        
        return registros
    
    def insertar_registros(self, tabla, registros):
        """Inserta registros en una tabla"""
        if not registros:
            return 0
        
        # Construir query de inserción
        columnas = list(registros[0].keys())
        tabla_completa = f"{self.esquema}.{tabla}"
        
        columnas_str = ', '.join([f'"{col}"' for col in columnas])
        placeholders = ', '.join(['%s'] * len(columnas))
        
        query = f'INSERT INTO {tabla_completa} ({columnas_str}) VALUES ({placeholders})'
        
        # Preparar datos
        datos = []
        for registro in registros:
            fila = [registro.get(col) for col in columnas]
            datos.append(tuple(fila))
        
        try:
            execute_batch(self.cursor, query, datos, page_size=100)
            self.conn.commit()
            
            # Actualizar cache con los valores insertados
            if tabla in self.metadata['pks']:
                for pk_col in self.metadata['pks'][tabla]:
                    if pk_col in columnas:
                        cache_key = f"{tabla}.{pk_col}"
                        valores = [registro[pk_col] for registro in registros if pk_col in registro and registro[pk_col] is not None]
                        if cache_key not in self.data_cache:
                            self.data_cache[cache_key] = []
                        self.data_cache[cache_key].extend(valores)
            
            return len(registros)
        
        except Exception as e:
            self.conn.rollback()
            print(f"✗ Error insertando en {tabla}: {e}")
            return 0
    
    def generar_data_completa(self, cantidad_base=None):
        """Genera data de prueba para todas las tablas"""
        if cantidad_base is None:
            cantidad_base = self.config.get('cantidad_base', 100)
        
        print(f"\n{'='*70}")
        print(f"📊 GENERANDO DATA DE PRUEBA")
        print(f"{'='*70}\n")
        
        print(f"Cantidad base de registros: {cantidad_base}")
        print(f"Orden de carga: {len(self.metadata['orden_carga'])} tablas\n")
        
        total_insertados = 0
        
        for i, tabla in enumerate(self.metadata['orden_carga'], 1):
            print(f"[{i}/{len(self.metadata['orden_carga'])}] Procesando tabla: {tabla}")
            
            # Calcular cantidad de registros
            cantidad = self.config.get('cantidad_por_tabla', {}).get(tabla, cantidad_base)
            
            # Si tiene FK y multiplicadores están habilitados, generar más registros
            if (self.config['multiplicadores_fk']['habilitado'] and 
                tabla in self.metadata['fks'] and self.metadata['fks'][tabla]):
                factor = self.config['multiplicadores_fk']['factor']
                cantidad = int(cantidad_base * len(self.metadata['fks'][tabla]) * factor)
            
            print(f"    → Generando {cantidad} registros...")
            registros = self.generar_registros_tabla(tabla, cantidad)
            
            print(f"    → Insertando registros...")
            insertados = self.insertar_registros(tabla, registros)
            
            if insertados > 0:
                print(f"    ✓ Insertados: {insertados} registros\n")
                total_insertados += insertados
            else:
                print(f"    ⚠ No se insertaron registros\n")
        
        print(f"{'='*70}")
        print(f"✓ GENERACIÓN COMPLETADA")
        print(f"{'='*70}")
        print(f"\nTotal de registros insertados: {total_insertados}")
    
    def limpiar_tablas(self):
        """Limpia todas las tablas del esquema (en orden inverso)"""
        print(f"\n🗑 Limpiando tablas existentes...")
        
        for tabla in reversed(self.metadata['orden_carga']):
            try:
                tabla_completa = f"{self.esquema}.{tabla}"
                self.cursor.execute(f'TRUNCATE TABLE {tabla_completa} CASCADE')
                self.conn.commit()
                print(f"  ✓ Limpiada: {tabla}")
            except Exception as e:
                print(f"  ⚠ Error limpiando {tabla}: {e}")
                self.conn.rollback()


def main():
    if len(sys.argv) < 7:
        print("Error: Faltan parámetros")
        print("Uso: python data_prueba.py <host> <puerto> <bd> <usuario> <password> <esquema> [cantidad] [config_file]")
        sys.exit(1)
    
    host = sys.argv[1]
    puerto = sys.argv[2]
    bd = sys.argv[3]
    usuario = sys.argv[4]
    password = sys.argv[5]
    esquema = sys.argv[6]
    cantidad = int(sys.argv[7]) if len(sys.argv) > 7 else None
    config_file = sys.argv[8] if len(sys.argv) > 8 else None
    
    print(f"\n{'='*70}")
    print(f"🚀 GENERADOR DE DATA DE PRUEBA - PostgreSQL")
    print(f"{'='*70}\n")
    
    generator = DataPruebaGenerator(host, puerto, bd, usuario, password, esquema, config_file)
    
    if not generator.conectar():
        sys.exit(1)
    
    try:
        # Analizar estructura
        generator.analizar_base_datos()
        
        # Limpiar datos existentes según configuración
        if generator.config['limpieza_previa']['automatico']:
            generator.limpiar_tablas()
        elif generator.config['limpieza_previa']['preguntar']:
            respuesta = input("\n¿Desea limpiar las tablas antes de insertar? (s/n): ")
            if respuesta.lower() == 's':
                generator.limpiar_tablas()
        
        # Generar data
        generator.generar_data_completa(cantidad_base=cantidad)
        
        print(f"\n✅ Proceso completado exitosamente")
        
    except Exception as e:
        print(f"\n✗ Error durante la ejecución: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        generator.desconectar()
        print(f"\n{'='*70}\n")


if __name__ == "__main__":
    main()
