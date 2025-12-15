"""
Componente de consola reutilizable
"""
import tkinter as tk
from tkinter import scrolledtext
from .styles import CONSOLE_STYLES


class Console(scrolledtext.ScrolledText):
    """Widget de consola con coloreado de tags"""

    def __init__(self, parent, **kwargs):
        # Merge estilos por defecto
        default_config = {
            'font': ("Cascadia Code", 9),
            'bg': CONSOLE_STYLES['bg'],
            'fg': CONSOLE_STYLES['fg'],
            'insertbackground': CONSOLE_STYLES['insertbackground'],
            'wrap': tk.WORD,
            'relief': tk.FLAT,
            'padx': 10,
            'pady': 10,
            'selectbackground': CONSOLE_STYLES['selectbackground'],
            'selectforeground': CONSOLE_STYLES['selectforeground']
        }
        default_config.update(kwargs)

        super().__init__(parent, **default_config)

        # Configurar tags
        for tag_name, tag_config in CONSOLE_STYLES['tags'].items():
            self.tag_config(tag_name, **tag_config)

    def log(self, message: str, tag: str = "info"):
        """Añade mensaje a la consola con tag específico"""
        self.insert(tk.END, message + "\n", tag)
        self.see(tk.END)
        self.update()

    def clear(self):
        """Limpia el contenido de la consola"""
        self.delete('1.0', tk.END)
