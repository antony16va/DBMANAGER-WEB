import psycopg2
import pandas as pd
import json
from datetime import datetime
import sys
from pathlib import Path

class MetadataExtractor:
    def __init__(self, config_file='db_config.json'):
        """Inicializa el extractor con la configuracion de la base de datos"""
        base_dir = Path(__file__).resolve().parent
        project_root = base_dir.parent.parent
        config_path = Path(config_file)
        if not config_path.is_absolute():
            config_path = project_root / 'resources' / config_file

        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

        self.conn = None
        self.cursor = None
    
    def conectar(self):
        """Establece conexión con PostgreSQL"""
        try:
            self.conn = psycopg2.connect(
                host=self.config['host'],
                port=self.config['port'],
                database=self.config['database'],
                user=self.config['user'],
                password=self.config['password']
            )
            self.cursor = self.conn.cursor()
            print(f"✓ Conectado a la base de datos: {self.config['database']}")
            return True
        except Exception as e:
            print(f"✗ Error al conectar: {e}", file=sys.stderr)
            return False
    
    def extraer_resumen_objetos(self):
        """Extrae conteo de objetos por tipo y esquema"""
        query = """
        WITH objetos AS (
            -- Tablas
            SELECT 
                schemaname AS esquema,
                'TABLE' AS tipo_objeto,
                tablename AS nombre_objeto
            FROM pg_tables
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
            
            UNION ALL
            
            -- Vistas
            SELECT 
                schemaname,
                'VIEW',
                viewname
            FROM pg_views
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
            
            UNION ALL
            
            -- Funciones
            SELECT 
                n.nspname,
                'FUNCTION',
                p.proname
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
                AND p.prokind = 'f'
            
            UNION ALL
            
            -- Procedimientos almacenados
            SELECT 
                n.nspname,
                'PROCEDURE',
                p.proname
            FROM pg_proc p
            JOIN pg_namespace n ON p.pronamespace = n.oid
            WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
                AND p.prokind = 'p'
            
            UNION ALL
            
            -- Triggers
            SELECT 
                n.nspname,
                'TRIGGER',
                t.tgname
            FROM pg_trigger t
            JOIN pg_class c ON t.tgrelid = c.oid
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
                AND NOT t.tgisinternal
            
            UNION ALL
            
            -- Sequences
            SELECT 
                schemaname,
                'SEQUENCE',
                sequencename
            FROM pg_sequences
            WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
        )
        SELECT 
            esquema,
            tipo_objeto,
            COUNT(*) as cantidad
        FROM objetos
        GROUP BY esquema, tipo_objeto
        ORDER BY esquema, tipo_objeto;
        """
        
        try:
            self.cursor.execute(query)
            resultados = self.cursor.fetchall()
            
            df = pd.DataFrame(resultados, columns=['esquema', 'tipo_objeto', 'cantidad'])
            print(f"✓ Resumen de objetos extraído: {len(df)} registros")
            return df
        except Exception as e:
            print(f"✗ Error al extraer resumen de objetos: {e}", file=sys.stderr)
            return pd.DataFrame()
    
    def extraer_totales_globales(self):
        """Extrae totales generales para los KPIs principales"""
        query = """
        SELECT 
            (SELECT COUNT(*) FROM pg_tables 
             WHERE schemaname NOT IN ('pg_catalog', 'information_schema')) AS total_tablas,
            
            (SELECT COUNT(*) FROM pg_views 
             WHERE schemaname NOT IN ('pg_catalog', 'information_schema')) AS total_vistas,
            
            (SELECT COUNT(*) FROM pg_proc p
             JOIN pg_namespace n ON p.pronamespace = n.oid
             WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
                AND p.prokind = 'f') AS total_funciones,
            
            (SELECT COUNT(*) FROM pg_proc p
             JOIN pg_namespace n ON p.pronamespace = n.oid
             WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
                AND p.prokind = 'p') AS total_procedimientos,
            
            (SELECT COUNT(*) FROM pg_trigger t
             JOIN pg_class c ON t.tgrelid = c.oid
             JOIN pg_namespace n ON c.relnamespace = n.oid
             WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
                AND NOT t.tgisinternal) AS total_triggers,
            
            (SELECT COUNT(*) FROM pg_sequences
             WHERE schemaname NOT IN ('pg_catalog', 'information_schema')) AS total_sequences,
            
            (SELECT COUNT(DISTINCT schemaname) FROM pg_tables
             WHERE schemaname NOT IN ('pg_catalog', 'information_schema')) AS total_esquemas;
        """
        
        try:
            self.cursor.execute(query)
            resultado = self.cursor.fetchone()
            
            df = pd.DataFrame([resultado], columns=[
                'total_tablas', 'total_vistas', 'total_funciones', 
                'total_procedimientos', 'total_triggers', 'total_sequences',
                'total_esquemas'
            ])
            print(f"✓ Totales globales extraídos")
            return df
        except Exception as e:
            print(f"✗ Error al extraer totales globales: {e}", file=sys.stderr)
            return pd.DataFrame()
    
    def extraer_distribucion_tipos_datos(self):
        """Extrae distribución de tipos de datos en columnas"""
        query = """
        SELECT 
            CASE 
                WHEN data_type IN ('character varying', 'varchar', 'character', 'char', 'text') THEN 'TEXT'
                WHEN data_type IN ('integer', 'bigint', 'smallint', 'numeric', 'decimal', 'real', 'double precision') THEN 'NUMERIC'
                WHEN data_type IN ('timestamp', 'timestamp without time zone', 'timestamp with time zone', 'date', 'time') THEN 'DATE/TIME'
                WHEN data_type IN ('boolean') THEN 'BOOLEAN'
                WHEN data_type IN ('json', 'jsonb') THEN 'JSON'
                ELSE 'OTHER'
            END AS categoria_tipo,
            data_type AS tipo_dato_especifico,
            COUNT(*) AS cantidad_columnas
        FROM information_schema.columns
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
        GROUP BY categoria_tipo, data_type
        ORDER BY cantidad_columnas DESC;
        """
        
        try:
            self.cursor.execute(query)
            resultados = self.cursor.fetchall()
            
            df = pd.DataFrame(resultados, columns=['categoria_tipo', 'tipo_dato_especifico', 'cantidad_columnas'])
            print(f"✓ Distribución de tipos de datos extraída: {len(df)} registros")
            return df
        except Exception as e:
            print(f"✗ Error al extraer distribución de tipos: {e}", file=sys.stderr)
            return pd.DataFrame()
    
    def exportar_a_excel(self, output_file='metadata_overview.xlsx'):
        """Exporta todos los dataframes a un archivo Excel con múltiples hojas"""
        try:
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                # Hoja 1: Totales globales
                df_totales = self.extraer_totales_globales()
                if not df_totales.empty:
                    df_totales.to_excel(writer, sheet_name='Totales_Globales', index=False)
                
                # Hoja 2: Resumen por esquema y tipo
                df_resumen = self.extraer_resumen_objetos()
                if not df_resumen.empty:
                    df_resumen.to_excel(writer, sheet_name='Resumen_Objetos', index=False)
                
                # Hoja 3: Distribución de tipos de datos
                df_tipos = self.extraer_distribucion_tipos_datos()
                if not df_tipos.empty:
                    df_tipos.to_excel(writer, sheet_name='Tipos_Datos', index=False)
                
                # Hoja 4: Metadata del proceso
                df_metadata = pd.DataFrame([{
                    'fecha_extraccion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'base_datos': self.config['database'],
                    'host': self.config['host']
                }])
                df_metadata.to_excel(writer, sheet_name='Metadata', index=False)
            
            print(f"\n✓ Archivo exportado exitosamente: {output_file}")
            return True
        except Exception as e:
            print(f"✗ Error al exportar a Excel: {e}", file=sys.stderr)
            return False
    
    def cerrar(self):
        """Cierra las conexiones"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("✓ Conexión cerrada")


def main():
    # Archivo de configuración
    base_dir = Path(__file__).resolve().parent
    project_root = base_dir.parent.parent
    resources_dir = project_root / "resources"
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    config_file = resources_dir / 'db_config.json'
    output_file = data_dir / 'metadata_overview.xlsx'
    
    print("=" * 60)
    print("EXTRACTOR DE METADATA - OVERVIEW DASHBOARD")
    print("=" * 60)
    
    extractor = MetadataExtractor(str(config_file))
    
    if extractor.conectar():
        extractor.exportar_a_excel(str(output_file))
        extractor.cerrar()
        
        print("\n" + "=" * 60)
        print("Proceso completado")
        print("=" * 60)
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
