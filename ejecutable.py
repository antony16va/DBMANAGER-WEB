import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import json
import os
import subprocess
import threading
from datetime import datetime
from pathlib import Path
import shutil

class DBManager:
    def __init__(self, root):
        self.root = root
        self.root.title("DB MANAGER")
        self.root.geometry("1300x900")
        self.root.minsize(1200, 800)
        
        self.base_dir = Path(__file__).resolve().parent
        self.modules_dir = self.base_dir / "modules"
        self.resources_dir = self.base_dir / "resources"
        self.data_dir = self.base_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.config_file = str(self.data_dir / "db_manager_config.json")
        self.history_file = str(self.data_dir / "execution_history.json")
        self.config = self.load_config()
        self.current_process = None
        
        self.setup_ui()
        self.load_module_configs()
        
    def setup_ui(self):
        # Configuración de colores modernos
        self.colors = {
            'primary': '#2c3e50',      # Azul oscuro profesional
            'secondary': '#3498db',     # Azul brillante
            'accent': '#9b59b6',        # Púrpura elegante
            'success': '#27ae60',       # Verde
            'warning': '#f39c12',       # Naranja
            'danger': '#e74c3c',        # Rojo
            'bg_light': '#ecf0f1',      # Gris claro
            'bg_card': '#ffffff',       # Blanco
            'text_dark': '#2c3e50',     # Texto oscuro
            'text_light': '#7f8c8d',    # Texto gris
            'border': '#bdc3c7',        # Borde gris
            'hover': '#3498db',         # Azul hover
        }

        # Configurar ventana principal con color de fondo moderno
        self.root.configure(bg=self.colors['bg_light'])

        style = ttk.Style()
        style.theme_use('clam')

        # Estilos para botones de módulos con efectos modernos
        # Estilo compacto para botones de módulos (reduce tamaño y padding)
        style.configure('Module.TButton',
                   font=('Segoe UI', 9, 'bold'),
                   padding=6,
                   background=self.colors['secondary'],
                   foreground='white',
                   borderwidth=0,
                   focuscolor='none',
                   relief='flat')
        style.map('Module.TButton',
                 background=[('active', self.colors['hover']), ('pressed', self.colors['primary'])],
                 foreground=[('active', 'white')])

        # Estilos para botones de ejecución
        style.configure('Execute.TButton',
                       font=('Segoe UI', 10, 'bold'),
                       padding=10,
                       background=self.colors['success'],
                       foreground='white',
                       borderwidth=0,
                       relief='flat')
        style.map('Execute.TButton',
                 background=[('active', '#229954'), ('pressed', '#1e8449')])

        # Estilos para botones de control superior
        style.configure('Top.TButton',
                       font=('Segoe UI', 9),
                       padding=8,
                       background=self.colors['bg_card'],
                       borderwidth=1,
                       relief='flat')
        style.map('Top.TButton',
                 background=[('active', self.colors['bg_light'])])

        # Estilos para frames y labels
        style.configure('Card.TFrame',
                       background=self.colors['bg_card'],
                       relief='flat',
                       borderwidth=0)

        style.configure('TLabelframe',
                       background=self.colors['bg_card'],
                       borderwidth=2,
                       relief='groove')
        style.configure('TLabelframe.Label',
                       font=('Segoe UI', 11, 'bold'),
                       foreground=self.colors['primary'],
                       background=self.colors['bg_card'])
        
        main_container = ttk.Frame(self.root, style='Card.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Header mejorado con gradiente simulado
        title_frame = tk.Frame(main_container, bg=self.colors['primary'], height=80)
        title_frame.pack(fill=tk.X, pady=(0, 15))
        title_frame.pack_propagate(False)

        # Contenedor interno del header
        header_content = tk.Frame(title_frame, bg=self.colors['primary'])
        header_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)

        # Icono y título principal
        title_container = tk.Frame(header_content, bg=self.colors['primary'])
        title_container.pack(side=tk.LEFT)

        tk.Label(title_container, text="🗄️", font=('Segoe UI', 28),
                bg=self.colors['primary'], fg='white').pack(side=tk.LEFT, padx=(0, 10))

        title_text = tk.Frame(title_container, bg=self.colors['primary'])
        title_text.pack(side=tk.LEFT)

        tk.Label(title_text, text="DB MANAGER",
                font=('Segoe UI', 22, 'bold'),
                bg=self.colors['primary'],
                fg='white').pack(anchor=tk.W)

        tk.Label(title_text, text="Arquitectura de Base de Datos",
                font=('Segoe UI', 10),
                bg=self.colors['primary'],
                fg=self.colors['bg_light']).pack(anchor=tk.W)

        # Botones de control mejorados
        right_buttons_frame = tk.Frame(header_content, bg=self.colors['primary'])
        right_buttons_frame.pack(side=tk.RIGHT, padx=5)

        # Crear botones con estilo personalizado
        hist_btn = tk.Button(right_buttons_frame, text="📊 Historial",
                            command=self.show_history,
                            font=('Segoe UI', 9, 'bold'),
                            bg=self.colors['accent'],
                            fg='white',
                            relief='flat',
                    padx=10, pady=6,
                            cursor='hand2',
                            borderwidth=0)
        hist_btn.pack(side=tk.RIGHT, padx=5)
        self._add_hover_effect(hist_btn, self.colors['accent'], '#8e44ad')

        req_btn = tk.Button(right_buttons_frame, text="✓ Validar Requisitos",
                           command=self.check_requirements,
                           font=('Segoe UI', 9, 'bold'),
                           bg=self.colors['secondary'],
                           fg='white',
                           relief='flat',
                   padx=10, pady=6,
                           cursor='hand2',
                           borderwidth=0)
        req_btn.pack(side=tk.RIGHT, padx=5)
        self._add_hover_effect(req_btn, self.colors['secondary'], '#2980b9')
        
        content_frame = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        left_panel = ttk.Frame(content_frame)
        content_frame.add(left_panel, weight=2)
        
        # Hacer el panel de módulos más compacto
        modules_frame = ttk.LabelFrame(left_panel, text="   Modulos", padding=6)
        modules_frame.pack(fill=tk.BOTH, expand=True)
        
        self.modules = [
            {
                "id": 1,
                "name": "GENERAR DDL INICIAL",
                "script": str(self.modules_dir / "generar_ddl_inicial.py"),
                "type": "python",
                "icon": "📝",
                "color": "#3498db",
                "params": ["ruta_plantilla_excel", "ruta_salida_ddl_base"]
            },
            {
                "id": 2,
                "name": "VALIDAR NOMENCLATURA",
                "script": str(self.modules_dir / "validar_nomenclatura.py"),
                "type": "python",
                "icon": "✓",
                "color": "#27ae60",
                "params": ["host", "puerto", "bd", "usuario", "password", "ruta_salida_ddl_completo"]
            },
            {
                "id": 3,
                "name": "DICCIONARIO DE DATOS",
                "script": str(self.modules_dir / "generar_diccionario.py"),
                "type": "python",
                "icon": "📚",
                "color": "#9b59b6",
                "params": ["host", "puerto", "bd", "usuario", "password", "esquema", "ruta_salida_rtf"]
            },
            {
                "id": 4,
                "name": "DATA DE PRUEBA",
                "script": str(self.modules_dir / "data_prueba.py"),
                "type": "python",
                "icon": "🧪",
                "color": "#f39c12",
                "params": ["host", "puerto", "bd", "usuario", "password", "esquema", "cantidad_registros"]
            },
            {
                "id": 5,
                "name": "DASHBOARD",
                "script": str(self.modules_dir / "dashboard" / "extraer_metadata_overview.py"),
                "type": "python",
                "icon": "📊",
                "color": "#e74c3c",
                "params": ["ruta_ddl_completo"]
            }
        ]
        self.module_buttons = []
        for module in self.modules:
            self.create_module_card(modules_frame, module)
        
        right_panel = ttk.Frame(content_frame)
        content_frame.add(right_panel, weight=3)
        
        config_frame = ttk.LabelFrame(right_panel, text="  Configuracion del Modulo", padding=15)
        config_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Header del módulo seleccionado
        module_header = tk.Frame(config_frame, bg=self.colors['bg_card'])
        module_header.pack(fill=tk.X, pady=(0, 15))

        self.module_name_var = tk.StringVar(value="Selecciona un módulo")
        tk.Label(module_header, textvariable=self.module_name_var,
                font=('Segoe UI', 13, 'bold'),
                bg=self.colors['bg_card'],
                fg=self.colors['primary']).pack(anchor=tk.W)
        
        params_container = ttk.Frame(config_frame)
        params_container.pack(fill=tk.BOTH, expand=True)
        
        canvas = tk.Canvas(params_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(params_container, orient="vertical", command=canvas.yview)
        self.params_frame = ttk.Frame(canvas)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        canvas_frame = canvas.create_window((0, 0), window=self.params_frame, anchor="nw")
        
        def configure_scroll(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_frame, width=event.width)
        
        self.params_frame.bind("<Configure>", configure_scroll)
        canvas.bind("<Configure>", configure_scroll)

        # Habilitar scrolling con la rueda del ratón dentro del canvas (Windows/macOS/Linux)
        def _on_mousewheel(event):
            try:
                delta = event.delta
            except AttributeError:
                delta = 0
            if delta:
                # Windows y macOS: event.delta suele ser múltiplo de 120 por 'notch'
                move = int(-1 * (delta / 120))
                if move == 0:
                    move = -1 if delta > 0 else 1
                canvas.yview_scroll(move, "units")
            else:
                # Linux: eventos Button-4 (arriba) / Button-5 (abajo)
                if hasattr(event, 'num'):
                    if event.num == 4:
                        canvas.yview_scroll(-1, "units")
                    elif event.num == 5:
                        canvas.yview_scroll(1, "units")

        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", _on_mousewheel)
            canvas.bind_all("<Button-5>", _on_mousewheel)

        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        canvas.bind("<Enter>", _bind_mousewheel)
        canvas.bind("<Leave>", _unbind_mousewheel)
        
        self.param_widgets = {}
        
        btn_frame = tk.Frame(config_frame, bg=self.colors['bg_card'])
        btn_frame.pack(fill=tk.X, pady=(15, 0))

        # Botones de acción mejorados con iconos
        save_btn = tk.Button(btn_frame, text="💾 Guardar Configuración",
                            command=self.save_module_config,
                            font=('Segoe UI', 10, 'bold'),
                            bg=self.colors['secondary'],
                            fg='white',
                            relief='flat',
                            cursor='hand2',
                            borderwidth=0,
                    padx=10, pady=6)
        save_btn.grid(row=0, column=0, sticky='ew', padx=5)
        self._add_hover_effect(save_btn, self.colors['secondary'], '#2980b9')

        exec_btn = tk.Button(btn_frame, text="▶ Ejecutar Módulo",
                            command=self.execute_current_module,
                            font=('Segoe UI', 10, 'bold'),
                            bg=self.colors['success'],
                            fg='white',
                            relief='flat',
                            cursor='hand2',
                            borderwidth=0,
                    padx=10, pady=6)
        exec_btn.grid(row=0, column=1, sticky='ew', padx=5)
        self._add_hover_effect(exec_btn, self.colors['success'], '#229954')

        stop_btn = tk.Button(btn_frame, text="⬛ Detener",
                            command=self.stop_execution,
                            font=('Segoe UI', 10, 'bold'),
                            bg=self.colors['danger'],
                            fg='white',
                            relief='flat',
                            cursor='hand2',
                            borderwidth=0,
                    padx=10, pady=6)
        stop_btn.grid(row=0, column=2, sticky='ew', padx=5)
        self._add_hover_effect(stop_btn, self.colors['danger'], '#c0392b')

        for i in range(3):
            btn_frame.columnconfigure(i, weight=1)
        
        console_frame = ttk.LabelFrame(right_panel, text="  Consola de Ejecucion", padding=10)
        console_frame.configure(height=220)
        console_frame.pack(fill=tk.BOTH, expand=False, pady=(10, 0))
        console_frame.pack_propagate(False)

        console_btn_frame = tk.Frame(console_frame, bg=self.colors['bg_card'])
        console_btn_frame.pack(fill=tk.X, pady=(0, 8))

        # Botones de la consola con estilo mejorado
        clear_btn = tk.Button(console_btn_frame, text="🗑 Limpiar",
                             command=self.clear_console,
                             font=('Segoe UI', 9),
                             bg=self.colors['bg_light'],
                             fg=self.colors['text_dark'],
                             relief='flat',
                             cursor='hand2',
                             borderwidth=0,
                             padx=12, pady=6)
        clear_btn.pack(side=tk.LEFT, padx=5)
        self._add_hover_effect(clear_btn, self.colors['bg_light'], self.colors['border'])

        save_btn = tk.Button(console_btn_frame, text="💾 Guardar Log",
                            command=self.save_log,
                            font=('Segoe UI', 9),
                            bg=self.colors['bg_light'],
                            fg=self.colors['text_dark'],
                            relief='flat',
                            cursor='hand2',
                            borderwidth=0,
                            padx=12, pady=6)
        save_btn.pack(side=tk.LEFT, padx=5)
        self._add_hover_effect(save_btn, self.colors['bg_light'], self.colors['border'])

        # Consola con diseño moderno y mejor contraste
        console_container = tk.Frame(console_frame, bg='#1e1e1e', relief=tk.SOLID,
                                    borderwidth=1, highlightbackground='#3e3e42',
                                    highlightthickness=1)
        console_container.pack(fill=tk.BOTH, expand=True)

        self.console_text = scrolledtext.ScrolledText(console_container,
                                                      font=("Cascadia Code", 9),
                                                      bg="#1e1e1e", fg="#d4d4d4",
                                                      insertbackground="#4ec9b0",
                                                      wrap=tk.WORD,
                                                      relief=tk.FLAT,
                                                      padx=10, pady=10,
                                                      selectbackground='#264f78',
                                                      selectforeground='#ffffff')
        self.console_text.pack(fill=tk.BOTH, expand=True)

        # Tags con colores mejorados tipo VS Code
        self.console_text.tag_config("info", foreground="#4fc1ff")
        self.console_text.tag_config("error", foreground="#f48771")
        self.console_text.tag_config("success", foreground="#73c991")
        self.console_text.tag_config("warning", foreground="#cca700")
        self.console_text.tag_config("module", foreground="#c586c0")
        
    def create_module_card(self, parent, module):
        # Contenedor principal de la tarjeta con fondo blanco y borde
        card_container = tk.Frame(parent, bg=self.colors['bg_card'],
                                 relief=tk.SOLID, borderwidth=1,
                                 highlightbackground=self.colors['border'],
                                 highlightthickness=1)
        # Reduce margenes y espaciado para tarjetas compactas
        card_container.pack(fill=tk.X, pady=4, padx=6)

        # Barra de color superior
        # Barra de color superior más delgada
        color_bar = tk.Frame(card_container, bg=module['color'], height=2)
        color_bar.pack(fill=tk.X)

        # Contenido de la tarjeta
        card_content = tk.Frame(card_container, bg=self.colors['bg_card'])
        card_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        # Header con icono y número
        header = tk.Frame(card_content, bg=self.colors['bg_card'])
        header.pack(fill=tk.X, pady=(0, 4))

        # Icono grande del módulo
        # Icono ligeramente más pequeño
        icon_frame = tk.Frame(header, bg=module['color'], width=36, height=36)
        icon_frame.pack(side=tk.LEFT, padx=(0, 12))
        icon_frame.pack_propagate(False)

        tk.Label(icon_frame, text=module['icon'], font=('Segoe UI', 14),
                bg=module['color'], fg='white').pack(expand=True)

        # Información del módulo
        info_frame = tk.Frame(header, bg=self.colors['bg_card'])
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(info_frame, text=f"Módulo {module['id']}",
            font=('Segoe UI', 7),
                bg=self.colors['bg_card'],
                fg=self.colors['text_light']).pack(anchor=tk.W)

        tk.Label(info_frame, text=module['name'],
            font=('Segoe UI', 9, 'bold'),
                bg=self.colors['bg_card'],
                fg=self.colors['text_dark']).pack(anchor=tk.W)

        # Badge del tipo
        type_badge = tk.Label(header, text=module['type'].upper(),
                     font=('Segoe UI', 7, 'bold'),
                     bg=self.colors['bg_light'],
                     fg=self.colors['text_light'],
                     padx=6, pady=2)
        type_badge.pack(side=tk.RIGHT)

        # Separador sutil
        separator = tk.Frame(card_content, bg=self.colors['border'], height=1)
        separator.pack(fill=tk.X, pady=(6, 8))

        # Botón de acción mejorado
        # Botón más compacto
        btn = tk.Button(card_content, text="⚙ Configurar y Ejecutar",
                       command=lambda m=module: self.select_module(m),
                   font=('Segoe UI', 9, 'bold'),
                       bg=module['color'],
                       fg='white',
                       relief='flat',
                       cursor='hand2',
                       borderwidth=0,
                   padx=10, pady=6)
        btn.pack(fill=tk.X)

        # Agregar efecto hover al botón
        self._add_hover_effect(btn, module['color'], self._darken_color(module['color']))

        self.module_buttons.append(btn)

    def _add_hover_effect(self, button, normal_color, hover_color):
        """Agrega efecto hover a un botón"""
        def on_enter(e):
            button['bg'] = hover_color

        def on_leave(e):
            button['bg'] = normal_color

        button.bind('<Enter>', on_enter)
        button.bind('<Leave>', on_leave)

    def _darken_color(self, hex_color, factor=0.8):
        """Oscurece un color hex"""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darkened = tuple(int(c * factor) for c in rgb)
        return '#{:02x}{:02x}{:02x}'.format(*darkened)

    def select_module(self, module):
        self.selected_module = module
        self.module_name_var.set(f"{module['icon']} {module['name']}")
        
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        
        self.param_widgets.clear()
        
        # Información del script con mejor diseño
        script_info = tk.Frame(self.params_frame, bg=self.colors['bg_light'],
                              relief=tk.FLAT, borderwidth=0)
        script_info.grid(row=0, column=0, columnspan=2, sticky='ew', pady=(0, 12), padx=0)

        tk.Label(script_info, text="📄 Script:",
                font=('Segoe UI', 9, 'bold'),
                bg=self.colors['bg_light'],
                fg=self.colors['text_dark'],
                padx=10, pady=8).pack(side=tk.LEFT)

        tk.Label(script_info, text=module['script'],
                font=('Segoe UI', 8),
                bg=self.colors['bg_light'],
                fg=self.colors['text_light'],
                padx=5, pady=8).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Separador decorativo
        sep_frame = tk.Frame(self.params_frame, bg=self.colors['bg_card'])
        sep_frame.grid(row=1, column=0, columnspan=3, sticky='ew', pady=(0, 15))

        tk.Frame(sep_frame, bg=self.colors['border'], height=2).pack(fill=tk.X)
        
        param_labels = {
            "ruta_plantilla_excel": "Ruta Plantilla Excel:",
            "ruta_salida_ddl_base": "Ruta Salida DDL:",
            "host": "Host PostgreSQL:",
            "puerto": "Puerto:",
            "bd": "Base de Datos:",
            "usuario": "Usuario:",
            "password": "Contrasena:",
            "ruta_salida_ddl_completo": "Ruta Salida DDL:",
            "ruta_ddl_completo": "Ruta DDL Completo:",
            "esquema": "Esquema:",
            "ruta_salida_rtf": "Ruta Salida RTF:",
            "ruta_ddl_base": "Ruta DDL:"
        }
        
        row = 2
        for param in module['params']:
            label_text = param_labels.get(param, param + ":")

            # Label del parámetro con estilo mejorado
            tk.Label(self.params_frame, text=label_text,
                    font=('Segoe UI', 9, 'bold'),
                    bg=self.colors['bg_card'],
                    fg=self.colors['text_dark']).grid(row=row, column=0, sticky=tk.W,
                                                     pady=8, padx=(0, 15))

            if 'ruta' in param.lower():
                frame = tk.Frame(self.params_frame, bg=self.colors['bg_card'])
                frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=8)

                var = tk.StringVar()
                entry = tk.Entry(frame, textvariable=var,
                               font=('Segoe UI', 9),
                               bg='white',
                               fg=self.colors['text_dark'],
                               relief=tk.SOLID,
                               borderwidth=1,
                               highlightthickness=0)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

                is_input = 'plantilla' in param.lower() or ('ddl' in param.lower() and 'salida' not in param.lower())
                btn = tk.Button(frame, text="📁",
                              font=('Segoe UI', 10),
                              command=lambda v=var, p=param: self.browse_path(v, p),
                              bg=self.colors['secondary'],
                              fg='white',
                              relief='flat',
                              cursor='hand2',
                              borderwidth=0,
                              padx=6, pady=3)
                btn.pack(side=tk.LEFT, padx=(5, 0))
                self._add_hover_effect(btn, self.colors['secondary'], '#2980b9')

                self.param_widgets[param] = var
            elif param == 'password':
                var = tk.StringVar()
                entry = tk.Entry(self.params_frame, textvariable=var, show="●",
                               font=('Segoe UI', 9),
                               bg='white',
                               fg=self.colors['text_dark'],
                               relief=tk.SOLID,
                               borderwidth=1,
                               highlightthickness=0)
                entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=8, ipady=3)
                self.param_widgets[param] = var
            else:
                var = tk.StringVar()
                entry = tk.Entry(self.params_frame, textvariable=var,
                               font=('Segoe UI', 9),
                               bg='white',
                               fg=self.colors['text_dark'],
                               relief=tk.SOLID,
                               borderwidth=1,
                               highlightthickness=0)
                entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=8, ipady=3)
                self.param_widgets[param] = var

            row += 1
        
        self.params_frame.columnconfigure(1, weight=1)
        
        module_config_key = f"module_{module['id']}"
        if module_config_key in self.config:
            saved_config = self.config[module_config_key]
            for param, value in saved_config.items():
                if param in self.param_widgets:
                    self.param_widgets[param].set(value)
        
        self.log_message(f"\n{'='*70}", "info")
        self.log_message(f"Modulo seleccionado: {module['name']}", "module")
        self.log_message(f"Tipo: {module['type'].upper()}", "info")
        self.log_message(f"Script: {module['script']}", "info")
        self.log_message(f"{'='*70}\n", "info")
        
    def browse_path(self, var, param_name):
        if 'salida' in param_name.lower():
            path = filedialog.asksaveasfilename(
                title="Guardar archivo como",
                defaultextension=".sql" if 'ddl' in param_name.lower() else ".rtf",
                filetypes=[
                    ("SQL files", "*.sql") if 'ddl' in param_name.lower() else ("RTF files", "*.rtf"),
                    ("All files", "*.*")
                ]
            )
        elif 'plantilla' in param_name.lower():
            path = filedialog.askopenfilename(
                title="Seleccionar archivo",
                filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
            )
        elif 'ddl' in param_name.lower():
            path = filedialog.askopenfilename(
                title="Seleccionar archivo DDL",
                filetypes=[("SQL files", "*.sql"), ("All files", "*.*")]
            )
        else:
            path = filedialog.askopenfilename(
                title="Seleccionar archivo",
                filetypes=[("All files", "*.*")]
            )
        
        if path:
            var.set(path)
            
    def save_module_config(self):
        if not hasattr(self, 'selected_module'):
            messagebox.showwarning("Advertencia", "No hay modulo seleccionado")
            return
        
        module_config = {}
        for param, widget in self.param_widgets.items():
            module_config[param] = widget.get()
        
        module_config_key = f"module_{self.selected_module['id']}"
        self.config[module_config_key] = module_config
        self.save_config()
        
        self.log_message(" Configuracion guardada correctamente", "success")
        
    def execute_current_module(self):
        if not hasattr(self, 'selected_module'):
            messagebox.showwarning("Advertencia", "Selecciona un modulo primero")
            return
        
        module = self.selected_module
        
        params_values = {}
        for param, widget in self.param_widgets.items():
            value = widget.get().strip()
            if not value:
                messagebox.showerror("Error", f"El parametro '{param}' es obligatorio")
                return
            params_values[param] = value
        
        if not os.path.exists(module['script']):
            messagebox.showerror("Error", f"Script no encontrado: {module['script']}")
            return
        
        self.log_message(f"\n{'='*70}", "info")
        self.log_message(f" Ejecutando: {module['name']}", "module")
        self.log_message(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "info")
        self.log_message(f"{'='*70}\n", "info")
        
        threading.Thread(target=self._execute_module_thread, 
                        args=(module, params_values), daemon=True).start()
        
    def _execute_module_thread(self, module, params_values):
        try:
            cmd_args = []
            for param in module['params']:
                cmd_args.append(params_values[param])
            
            if module['type'] == 'python':
                cmd = ['python', module['script']] + cmd_args
            elif module['type'] == 'groovy':
                # Try to find groovy executable; on Windows this may be a .bat/.cmd
                groovy_exe = shutil.which('groovy')
                if groovy_exe:
                    self.log_message(f"Usando ejecutable Groovy: {groovy_exe}", "info")
                    # If it's a batch file, run via cmd /c to ensure proper execution on Windows
                    if groovy_exe.lower().endswith(('.bat', '.cmd')):
                        cmd = ['cmd', '/c', groovy_exe, module['script']] + cmd_args
                    else:
                        cmd = [groovy_exe, module['script']] + cmd_args
                else:
                    # Fallback to plain 'groovy' (will raise FileNotFoundError if not available)
                    cmd = ['groovy', module['script']] + cmd_args
            else:
                self.log_message(f" Tipo no soportado: {module['type']}", "error")
                return
            
            self.log_message(f"Comando: {' '.join(cmd)}\n", "warning")
            
            start_time = datetime.now()
            
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            for line in self.current_process.stdout:
                self.log_message(line.rstrip(), "info")
            
            self.current_process.wait()
            
            stderr = self.current_process.stderr.read()
            if stderr:
                self.log_message("\n Errores/Advertencias:", "warning")
                self.log_message(stderr, "error")
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            if self.current_process.returncode == 0:
                self.log_message(f"\nModulo completado", "success")
                self.log_message(f"Tiempo de ejecucion: {duration:.2f} segundos", "success")
                status = "success"
            else:
                self.log_message(f"\n Modulo termino con codigo: {self.current_process.returncode}", "error")
                status = "error"
            
            self.save_to_history(module, params_values, status, duration)
            
            self.current_process = None
            
        except FileNotFoundError:
            interpreter = "Python" if module['type'] == 'python' else "Groovy"
            self.log_message(f" Error: {interpreter} no esta instalado o no esta en PATH", "error")
            # Intentar diagnosticar: buscar ejecutable y mostrar PATH para depuracion
            exe_name = 'python' if module['type'] == 'python' else 'groovy'
            found = shutil.which(exe_name)
            if found:
                self.log_message(f"Localizado {exe_name} en: {found}", "info")
            else:
                self.log_message(f"No se encontro '{exe_name}' en PATH. PATH actual:", "warning")
                path_env = os.environ.get('PATH', '')
                # Mostrar PATH (puede ser largo)
                self.log_message(path_env, "info")
                self.log_message(f"Prueba en terminal: 'where {exe_name}' (PowerShell) o 'which {exe_name}' (bash).", "info")
        except Exception as e:
            self.log_message(f" Error ejecutando modulo: {e}", "error")
            self.current_process = None
            
    def stop_execution(self):
        if self.current_process and self.current_process.poll() is None:
            self.current_process.terminate()
            self.log_message("\n Ejecucion detenida por el usuario\n", "warning")
        else:
            self.log_message("No hay ningun proceso en ejecucion", "warning")
            
    def clear_console(self):
        self.console_text.delete('1.0', tk.END)
        
    def save_log(self):
        log_content = self.console_text.get('1.0', tk.END)
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(log_content)
                self.log_message(f"\n Log guardado en: {filename}", "success")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo guardar el log: {e}")
                
    def log_message(self, message, tag="info"):
        self.console_text.insert(tk.END, message + "\n", tag)
        self.console_text.see(tk.END)
        self.console_text.update()
        
    def check_requirements(self):
        self.log_message(f"\n{'='*70}", "info")
        self.log_message(" Verificando requisitos del sistema...", "module")
        self.log_message(f"{'='*70}\n", "info")
        
        threading.Thread(target=self._check_requirements_thread, daemon=True).start()
        
    def _check_requirements_thread(self):
        checks = {}
        
        try:
            result = subprocess.run(['python', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.log_message(f" Python: {result.stdout.strip()}", "success")
                checks['python'] = True
            else:
                self.log_message(f" Python no encontrado", "error")
                checks['python'] = False
        except:
            self.log_message(f" Python no encontrado", "error")
            checks['python'] = False
        
        try:
            result = subprocess.run(['groovy', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                self.log_message(f" Groovy: {version_line}", "success")
                checks['groovy'] = True
            else:
                self.log_message(f" Groovy no encontrado (requerido para Modulo 3)", "warning")
                checks['groovy'] = False
        except:
            self.log_message(f" Groovy no encontrado (requerido para Modulo 3)", "warning")
            checks['groovy'] = False
        
        try:
            result = subprocess.run(['pg_dump', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.log_message(f" PostgreSQL: {result.stdout.strip()}", "success")
                checks['postgresql'] = True
            else:
                self.log_message(f" pg_dump no encontrado", "warning")
                checks['postgresql'] = False
        except:
            self.log_message(f" pg_dump no encontrado", "warning")
            checks['postgresql'] = False
        
        self.log_message(f"\n{'='*70}\n", "info")
        
        if checks.get('python') and checks.get('groovy'):
            self.log_message(" Todos los requisitos principales estan instalados", "success")
        else:
            self.log_message(" Algunos requisitos faltan. Revisa los mensajes arriba.", "warning")
            
    def show_history(self):
        history_window = tk.Toplevel(self.root)
        history_window.title("Historial de Ejecuciones")
        history_window.geometry("900x600")
        
        frame = ttk.Frame(history_window, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("Fecha/Hora", "Modulo", "Estado", "Duracion")
        tree = ttk.Treeview(frame, columns=columns, show='headings', height=20)
        
        tree.heading("Fecha/Hora", text="Fecha/Hora")
        tree.heading("Modulo", text="Modulo")
        tree.heading("Estado", text="Estado")
        tree.heading("Duracion", text="Duracion (seg)")
        
        tree.column("Fecha/Hora", width=150)
        tree.column("Modulo", width=400)
        tree.column("Estado", width=100)
        tree.column("Duracion", width=100)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        history = self.load_history()
        for entry in reversed(history):
            tree.insert('', 0, values=(
                entry['timestamp'],
                entry['module_name'],
                entry['status'],
                f"{entry['duration']:.2f}"
            ))
        
        btn_frame = ttk.Frame(history_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(btn_frame, text=" Limpiar Historial", 
                  command=lambda: self.clear_history(history_window)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cerrar", 
                  command=history_window.destroy).pack(side=tk.RIGHT, padx=5)
        
    def save_to_history(self, module, params, status, duration):
        history = self.load_history()
        
        entry = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "module_id": module['id'],
            "module_name": module['name'],
            "status": status,
            "duration": duration,
            "params": params
        }
        
        history.append(entry)
        
        if len(history) > 100:
            history = history[-100:]
        
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log_message(f" No se pudo guardar el historial: {e}", "warning")
            
    def load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
        
    def clear_history(self, window):
        if messagebox.askyesno("Confirmar", "Estas seguro de limpiar todo el historial?"):
            try:
                with open(self.history_file, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                messagebox.showinfo("Exito", "Historial limpiado")
                window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo limpiar el historial: {e}")
                
    def load_config(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
        
    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar la configuracion: {e}")
            
    def load_module_configs(self):
        """Load and log previously saved module configurations"""
        if self.config:
            loaded_modules = [key for key in self.config.keys() if key.startswith('module_')]
            if loaded_modules:
                self.log_message(f"\n{'='*70}", "info")
                self.log_message(f"Configuraciones cargadas para {len(loaded_modules)} modulo(s)", "success")
                for module_key in loaded_modules:
                    module_id = module_key.split('_')[1]
                    module_name = next((m['name'] for m in self.modules if str(m['id']) == module_id), 'Desconocido')
                    self.log_message(f"  - Modulo {module_id}: {module_name}", "info")
                self.log_message(f"{'='*70}\n", "info")
            else:
                self.log_message("No hay configuraciones guardadas\n", "info")
        else:
            self.log_message("No hay configuraciones guardadas\n", "info")

def main():
    root = tk.Tk()
    app = DBManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()
