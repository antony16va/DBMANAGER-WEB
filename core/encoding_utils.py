"""
Utilidades para manejo de codificación UTF-8
Centraliza la lógica duplicada en múltiples módulos
"""
import sys
import builtins
import io


def setup_utf8_encoding():
    """
    Configura la codificación UTF-8 para stdout/stderr
    Reemplaza la lógica duplicada en múltiples archivos
    """
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Fallback para sistemas sin reconfigure
        _setup_safe_print()


def _setup_safe_print():
    """
    Configura un sistema de impresión seguro para evitar errores de codificación
    """
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
            except:
                _orig_print(text.encode('utf-8', errors='replace').decode('utf-8'))

    builtins.print = _safe_print


def setup_windows_utf8():
    """
    Configuración específica de UTF-8 para Windows
    """
    if sys.platform == 'win32':
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except:
            pass
