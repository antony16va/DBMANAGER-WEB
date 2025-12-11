import subprocess
import sys
from pathlib import Path

def generar_dump_sql(host: str, puerto: str, usuario: str, base_datos: str, archivo_salida: str, password: str = None):
    """
    Genera un dump SQL de la base de datos PostgreSQL
    """
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
        print(f"Generando dump SQL...")
        print(f"Host: {host}")
        print(f"Puerto: {puerto}")
        print(f"Base de datos: {base_datos}")
        print(f"Usuario: {usuario}")
        print(f"Archivo de salida: {archivo_salida}")
        resultado = subprocess.run(
            comando,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"\n[OK] Dump SQL generado exitosamente: {archivo_salida}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Error al ejecutar pg_dump: {e.stderr}")
        return False
    except FileNotFoundError:
        print("\n[ERROR] Error: pg_dump no esta instalado o no esta en el PATH")
        return False

def main():
    if len(sys.argv) != 7:
        print("Error: Se requieren 6 parametros")
        print("Uso: python generar_dump.py <host> <puerto> <bd> <usuario> <password> <ruta_salida>")
        sys.exit(1)
    host = sys.argv[1]
    puerto = sys.argv[2]
    bd = sys.argv[3]
    usuario = sys.argv[4]
    password = sys.argv[5]
    ruta_salida = sys.argv[6]
    exito = generar_dump_sql(host, puerto, usuario, bd, ruta_salida, password)
    sys.exit(0 if exito else 1)
if __name__ == "__main__":
    main()
