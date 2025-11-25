import argparse
import sys
import os
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import Dict, List, Tuple
from pathlib import Path


class ExcelReader:
    def __init__(self, excel_file: str):
        self.excel_file = excel_file
        self.shared_strings = []
        self.sheet_data = []
        
    def read_shared_strings(self, zip_ref):
        try:
            with zip_ref.open('xl/sharedStrings.xml') as f:
                tree = ET.parse(f)
                root = tree.getroot()
                ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                
                for si in root.findall('.//main:si', ns):
                    text_parts = []
                    for t in si.findall('.//main:t', ns):
                        if t.text:
                            text_parts.append(t.text)
                    
                    if text_parts:
                        self.shared_strings.append(''.join(text_parts))
                    else:
                        self.shared_strings.append('')
        except KeyError:
            pass
    
    def get_cell_value(self, cell, ns):
        cell_type = cell.get('t')
        
        if cell_type == 'inlineStr':
            is_elem = cell.find('main:is', ns)
            if is_elem is not None:
                t = is_elem.find('main:t', ns)
                if t is not None and t.text is not None:
                    return t.text
            return None
        
        v = cell.find('main:v', ns)
        
        if v is None or v.text is None:
            return None
        
        if cell_type == 's':
            return self.shared_strings[int(v.text)]
        elif cell_type == 'b':
            return v.text == '1'
        elif cell_type == 'str':
            return v.text
        else:
            try:
                if '.' in v.text:
                    return float(v.text)
                return int(v.text)
            except ValueError:
                return v.text
    
    def read_sheet(self, sheet_name='source'):
        with zipfile.ZipFile(self.excel_file, 'r') as zip_ref:
            self.read_shared_strings(zip_ref)
            
            workbook_xml = zip_ref.read('xl/workbook.xml')
            wb_tree = ET.fromstring(workbook_xml)
            ns_wb = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
                     'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
            
            sheet_rid = None
            for sheet in wb_tree.findall('.//main:sheet', ns_wb):
                if sheet.get('name') == sheet_name:
                    sheet_rid = sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                    break
            
            if not sheet_rid:
                return []
            
            rels_xml = zip_ref.read('xl/_rels/workbook.xml.rels')
            rels_tree = ET.fromstring(rels_xml)
            ns_rels = {'r': 'http://schemas.openxmlformats.org/package/2006/relationships'}
            
            sheet_file = None
            for rel in rels_tree.findall('.//r:Relationship', ns_rels):
                if rel.get('Id') == sheet_rid:
                    target = rel.get('Target')
                    if target.startswith('/'):
                        sheet_file = target[1:]
                    elif target.startswith('worksheets/'):
                        sheet_file = 'xl/' + target
                    else:
                        sheet_file = target
                    break
            
            if not sheet_file:
                return []
            
            with zip_ref.open(sheet_file) as f:
                tree = ET.parse(f)
                root = tree.getroot()
                ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                
                rows_data = []
                for row in root.findall('.//main:row', ns):
                    row_data = []
                    cells = row.findall('.//main:c', ns)
                    
                    if not cells:
                        continue
                    
                    last_col = 0
                    for cell in cells:
                        ref = cell.get('r')
                        col = ''.join(filter(str.isalpha, ref))
                        col_num = self.column_letter_to_number(col)
                        
                        while last_col < col_num - 1:
                            row_data.append(None)
                            last_col += 1
                        
                        value = self.get_cell_value(cell, ns)
                        row_data.append(value)
                        last_col = col_num
                    
                    rows_data.append(row_data)
                
                return rows_data
    
    def column_letter_to_number(self, col):
        num = 0
        for c in col:
            num = num * 26 + (ord(c.upper()) - ord('A')) + 1
        return num


class PostgreSQLDDLGenerator:
    def __init__(self, excel_file: str):
        self.excel_file = excel_file
        self.tables = defaultdict(list)
        self.schemas = set()
        self.headers = []
        
    def parse_excel(self):
        reader = ExcelReader(self.excel_file)
        rows = reader.read_sheet('source')
        
        if not rows:
            raise ValueError("No se encontró la hoja 'source' en el archivo Excel")
        
        if len(rows) < 2:
            raise ValueError(f"El archivo Excel solo contiene encabezados. Se necesitan datos en las filas.\nTotal de filas encontradas: {len(rows)}")
        
        self.headers = rows[0]
        
        data_rows_processed = 0
        for row in rows[1:]:
            if not any(row):
                continue
            
            row_data = {}
            for i, header in enumerate(self.headers):
                if i < len(row):
                    row_data[header] = row[i]
                else:
                    row_data[header] = None
            
            schema = str(row_data.get('esquema', '')).strip() if row_data.get('esquema') else ''
            table = str(row_data.get('tabla', '')).strip() if row_data.get('tabla') else ''
            
            if not schema or not table:
                continue
            
            self.schemas.add(schema)
            table_key = f"{schema}.{table}"
            self.tables[table_key].append(row_data)
            data_rows_processed += 1
        
        if data_rows_processed == 0:
            raise ValueError("No se encontraron filas con datos válidos (esquema y tabla son requeridos)")
    
    def format_data_type(self, row: Dict) -> str:
        data_type_val = row.get('tipo_dato')
        data_type = str(data_type_val).strip().lower() if data_type_val else ''
        precision = row.get('precision')
        scale = row.get('escala')
        
        if data_type in ('varchar', 'character varying'):
            if precision:
                return f"VARCHAR({int(precision)})"
            return "VARCHAR"
        
        if data_type in ('numeric', 'decimal'):
            if precision and scale:
                return f"NUMERIC({int(precision)},{int(scale)})"
            elif precision:
                return f"NUMERIC({int(precision)})"
            return "NUMERIC"
        
        if data_type in ('char', 'character'):
            if precision:
                return f"CHAR({int(precision)})"
            return "CHAR"
        
        return data_type.upper()
    
    def generate_column_definition(self, row: Dict) -> str:
        column_val = row.get('columna')
        column_name = str(column_val).strip() if column_val else ''
        data_type = self.format_data_type(row)
        
        definition = f"    {column_name} {data_type}"
        
        not_null_val = row.get('no_nulo')
        not_null = str(not_null_val).strip().upper() if not_null_val else ''
        if not_null in ('YES', 'Y', 'S', 'SI'):
            definition += " NOT NULL"
        
        default_value = row.get('valor_default')
        if default_value:
            default_str = str(default_value).strip()
            if default_str:
                if data_type.startswith(('VARCHAR', 'CHAR', 'TEXT')):
                    definition += f" DEFAULT '{default_str}'"
                else:
                    definition += f" DEFAULT {default_str}"
        
        return definition
    
    def get_primary_keys(self, columns: List[Dict]) -> List[str]:
        pk_columns = []
        for col in columns:
            pk_val = col.get('pk')
            is_pk = str(pk_val).strip().upper() if pk_val else ''
            if is_pk in ('YES', 'Y', 'S', 'SI'):
                column_val = col.get('columna')
                pk_columns.append(str(column_val).strip() if column_val else '')
        return pk_columns
    
    def get_foreign_keys(self, columns: List[Dict]) -> List[Tuple[str, str, str]]:
        fk_list = []
        for col in columns:
            fk_val = col.get('fk')
            is_fk = str(fk_val).strip().upper() if fk_val else ''
            if is_fk in ('YES', 'Y', 'S', 'SI'):
                column_val = col.get('columna')
                fk_table_val = col.get('fk_tabla')
                fk_column_val = col.get('fk_columna')
                
                column_name = str(column_val).strip() if column_val else ''
                fk_table = str(fk_table_val).strip() if fk_table_val else ''
                fk_column = str(fk_column_val).strip() if fk_column_val else ''
                
                if column_name and fk_table and fk_column:
                    fk_list.append((column_name, fk_table, fk_column))
        
        return fk_list
    
    def generate_table_comment(self, schema: str, table: str, description) -> str:
        if description:
            desc_str = str(description).strip()
            if desc_str:
                return f"COMMENT ON TABLE {schema}.{table} IS '{desc_str}';"
        return ""
    
    def generate_column_comment(self, schema: str, table: str, column: str, description) -> str:
        if description:
            desc_str = str(description).strip()
            if desc_str:
                return f"COMMENT ON COLUMN {schema}.{table}.{column} IS '{desc_str}';"
        return ""
    
    def generate_ddl(self) -> str:
        self.parse_excel()
        
        ddl_statements = []
        ddl_statements.append("-- =============================================")
        ddl_statements.append("-- DDL Generated from Excel Template")
        ddl_statements.append("-- =============================================\n")
        
        for schema in sorted(self.schemas):
            ddl_statements.append(f"CREATE SCHEMA IF NOT EXISTS {schema};")
        
        ddl_statements.append("")
        
        for table_key in sorted(self.tables.keys()):
            columns = self.tables[table_key]
            schema, table = table_key.split('.')
            
            ddl_statements.append(f"-- Table: {table_key}")
            ddl_statements.append(f"CREATE TABLE {table_key} (")
            
            column_definitions = []
            for col in columns:
                column_definitions.append(self.generate_column_definition(col))
            
            pk_columns = self.get_primary_keys(columns)
            if pk_columns:
                pk_constraint = f"    CONSTRAINT pk_{table} PRIMARY KEY ({', '.join(pk_columns)})"
                column_definitions.append(pk_constraint)
            
            ddl_statements.append(",\n".join(column_definitions))
            ddl_statements.append(");\n")
            
            table_description = columns[0].get('descripcion_tabla')
            table_comment = self.generate_table_comment(schema, table, table_description)
            if table_comment:
                ddl_statements.append(table_comment)
            
            for col in columns:
                column_val = col.get('columna')
                column_name = str(column_val).strip() if column_val else ''
                column_description = col.get('descripcion_columna')
                column_comment = self.generate_column_comment(schema, table, column_name, column_description)
                if column_comment:
                    ddl_statements.append(column_comment)
            
            ddl_statements.append("")
        
        for table_key in sorted(self.tables.keys()):
            columns = self.tables[table_key]
            schema, table = table_key.split('.')
            
            fk_list = self.get_foreign_keys(columns)
            
            for idx, (column_name, fk_table, fk_column) in enumerate(fk_list, 1):
                fk_constraint_name = f"fk_{table}_{idx}"
                fk_statement = (
                    f"ALTER TABLE {table_key}\n"
                    f"    ADD CONSTRAINT {fk_constraint_name}\n"
                    f"    FOREIGN KEY ({column_name})\n"
                    f"    REFERENCES {fk_table}({fk_column});\n"
                )
                ddl_statements.append(fk_statement)
        
        return "\n".join(ddl_statements)
    
    def save_to_file(self, output_file: str):
        ddl_content = self.generate_ddl()
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(ddl_content)


def main():
    parser = argparse.ArgumentParser(
        prog='generar_ddl_inicial',
        description='Genera DDL de PostgreSQL a partir de una plantilla Excel.'
    )

    base_dir = Path(__file__).resolve().parent
    resources_dir = base_dir.parent / "resources"
    data_dir = base_dir.parent / "data"

    parser.add_argument('input_file', nargs='?',
                        default=str(resources_dir / 'Plantilla_Modelo.xlsx'),
                        help='Ruta al archivo plantilla Excel (.xlsx)')
    parser.add_argument('output_file', nargs='?',
                        default=str(data_dir / 'database_ddl.sql'),
                        help='Ruta de salida para el archivo DDL (.sql)')

    args = parser.parse_args()

    input_file = args.input_file
    output_file = args.output_file

    # Validar existencia del archivo de entrada
    if not os.path.exists(input_file):
        print(f"Error: archivo de plantilla no encontrado: {input_file}", file=sys.stderr)
        return 2

    # Asegurar que el directorio de salida exista
    out_dir = os.path.dirname(output_file)
    if out_dir:
        try:
            os.makedirs(out_dir, exist_ok=True)
        except Exception as e:
            print(f"Error creando directorio de salida '{out_dir}': {e}", file=sys.stderr)
            return 3

    generator = PostgreSQLDDLGenerator(input_file)
    try:
        generator.save_to_file(output_file)
        print(f"DDL generado exitosamente en: {output_file}")
    except Exception as e:
        print(f"Error generando DDL: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
