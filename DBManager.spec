# -*- mode: python ; coding: utf-8 -*-
import os, shutil, tempfile

# Convierte ico.ico a formato ICO nativo de Windows (necesario si el
# archivo es en realidad un PNG/JPG renombrado).  Requiere Pillow.
def _ensure_ico(src_name):
    src = os.path.join(SPECPATH, src_name)
    try:
        from PIL import Image
        img = Image.open(src)
        tmp = os.path.join(tempfile.gettempdir(), '_dbmanager_icon.ico')
        img.save(tmp, format='ICO', sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
        return tmp
    except Exception:
        return src          # Si falla, usa el archivo original

_icon_path = _ensure_ico('ico.ico')

#
# DBManager.spec — PyInstaller spec para un único ejecutable.
#
# Uso:
#   pyinstaller DBManager.spec --clean
#
# Resultado (--onedir):
#   dist\DBManager\
#     DBManager.exe
#     _internal\       ← runtime Python (requerido junto al .exe)
#     resources\
#     data\

block_cipher = None

# Solo los providers de Faker que realmente usa data_prueba.py.
# Evita arrastrar los ~80 locales y providers no usados.
faker_providers = [
    'faker',
    'faker.providers',
    'faker.providers.address',
    'faker.providers.address.es_ES',
    'faker.providers.company',
    'faker.providers.company.es_ES',
    'faker.providers.date_time',
    'faker.providers.date_time.es_ES',
    'faker.providers.internet',
    'faker.providers.internet.es_ES',
    'faker.providers.lorem',
    'faker.providers.lorem.es_ES',
    'faker.providers.misc',
    'faker.providers.person',
    'faker.providers.person.es_ES',
    'faker.providers.phone_number',
    'faker.providers.phone_number.es_ES',
]

# Módulos importados dinámicamente con importlib en tiempo de ejecución
# (PyInstaller no los detecta por análisis estático).
modules_hidden = [
    'agregar_comentarios',
    'validar_nomenclatura',
    'generar_diccionario',
    'data_prueba',
    'data_prueba_gui',
]

hiddenimports_all = [
    'psycopg2',
    'psycopg2.extensions',
    'psycopg2.extras',
    'psycopg2._psycopg',
] + faker_providers + modules_hidden

# Módulos de stdlib y paquetes que definitivamente no se usan.
# Reduces el tamaño de _internal sin afectar la funcionalidad.
excludes_list = [
    # Ciencia de datos (pesados)
    'pandas', 'numpy', 'matplotlib', 'scipy', 'PIL', 'cv2',
    # Entornos interactivos
    'IPython', 'jupyter', 'notebook', 'ipykernel', 'ipywidgets',
    # Herramientas de desarrollo
    'sphinx', 'docutils', 'pydoc', 'doctest',
    'lib2to3', 'distutils',
    'ensurepip', 'venv', 'pip', 'setuptools', 'pkg_resources',
    # GUI alternativas que no usamos
    'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'wx', 'gi',
    # stdlib rara vez usada
    'idlelib', 'turtle', 'curses',
    'xmlrpc', 'antigravity', 'this',
    'unittest', 'test',
    'tkinter.test',
    # Async (no usamos)
    'asyncio', 'asynchat', 'asyncore',
]

a = Analysis(
    ['ejecutable.py'],
    pathex=['.', 'modules'],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('data',      'data'),
        ('ico.ico',   '.'),
    ],
    hiddenimports=hiddenimports_all,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes_list,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DBManager',
    icon=_icon_path,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,           # False en el .exe: UPX puede corromper el ícono incrustado.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DBManager',
)
