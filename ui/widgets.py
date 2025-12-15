"""
Widgets reutilizables para la interfaz
"""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
from .styles import COLORS


def create_button(parent, text: str, command: Callable, style: str = 'primary', **kwargs):
    """
    Crea un botón estilizado

    Args:
        parent: Widget padre
        text: Texto del botón
        command: Función a ejecutar
        style: Estilo del botón ('primary', 'success', 'danger', 'warning')
        **kwargs: Argumentos adicionales de tk.Button
    """
    color = COLORS.get(style, COLORS['primary'])

    default_config = {
        'text': text,
        'command': command,
        'bg': color,
        'fg': 'white',
        'font': ('Segoe UI', 9, 'bold'),
        'relief': tk.FLAT,
        'cursor': 'hand2',
        'borderwidth': 0,
        'padx': 10,
        'pady': 6
    }
    default_config.update(kwargs)

    btn = tk.Button(parent, **default_config)

    # Añadir efecto hover
    hover_color = _darken_color(color)
    _add_hover_effect(btn, color, hover_color)

    return btn


def create_card(parent, title: Optional[str] = None, **kwargs):
    """
    Crea un contenedor tipo tarjeta

    Args:
        parent: Widget padre
        title: Título opcional de la tarjeta
        **kwargs: Argumentos adicionales del Frame
    """
    default_config = {
        'bg': COLORS['bg_card'],
        'relief': tk.SOLID,
        'borderwidth': 1,
        'highlightbackground': COLORS['border'],
        'highlightthickness': 1
    }
    default_config.update(kwargs)

    card = tk.Frame(parent, **default_config)

    if title:
        header = tk.Frame(card, bg=COLORS['primary'])
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text=title,
            font=('Segoe UI', 11, 'bold'),
            bg=COLORS['primary'],
            fg='white',
            padx=10,
            pady=8
        ).pack(anchor=tk.W)

    return card


def create_labeled_entry(parent, label_text: str, **kwargs):
    """
    Crea un Entry con label

    Args:
        parent: Widget padre
        label_text: Texto del label
        **kwargs: Argumentos adicionales del Entry
    """
    container = tk.Frame(parent, bg=COLORS['bg_card'])
    container.pack(fill=tk.X, pady=5)

    tk.Label(
        container,
        text=label_text,
        font=('Segoe UI', 9, 'bold'),
        bg=COLORS['bg_card'],
        fg=COLORS['text_dark'],
        width=20,
        anchor=tk.W
    ).pack(side=tk.LEFT)

    var = tk.StringVar()
    entry = tk.Entry(container, textvariable=var, font=('Segoe UI', 9), **kwargs)
    entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

    return var, entry


def _add_hover_effect(button, normal_color: str, hover_color: str):
    """Añade efecto hover a un botón"""
    def on_enter(e):
        button['bg'] = hover_color

    def on_leave(e):
        button['bg'] = normal_color

    button.bind('<Enter>', on_enter)
    button.bind('<Leave>', on_leave)


def _darken_color(hex_color: str, factor: float = 0.8) -> str:
    """Oscurece un color hex"""
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    darkened = tuple(int(c * factor) for c in rgb)
    return '#{:02x}{:02x}{:02x}'.format(*darkened)


class ScrollableFrame(tk.Frame):
    """Frame con scroll automático"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        # Canvas para scroll
        self.canvas = tk.Canvas(self, highlightthickness=0, bg=kwargs.get('bg', 'white'))
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=kwargs.get('bg', 'white'))

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Scroll con mouse wheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)
