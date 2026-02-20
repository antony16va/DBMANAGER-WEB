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
        self.root.title("DB-MANAGER")
        self.root.geometry("1200x600")
        self.root.minsize(1200, 800)
        self.base_dir = Path(__file__).resolve().parent
        self.modules_dir = self.base_dir / "modules"
        self.resources_dir = self.base_dir / "resources"
        self.data_dir = self.base_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = str(self.data_dir / "db_manager_config.json")
        self.config = self.load_config()
        self.global_params = self.config.get('_global_params', {})
        self.current_process = None
        self.colors = {
            'ink':       '#3d3d3d',
            'verde':     '#5a9e6e',  
            'verde_drk': '#498a5e',
            'plomo':     '#7a8b96',  
            'plomo_drk': '#657585',
            'parchment': '#f5f5f5',
            'cream':     '#ffffff', 
            'dust':      '#9a9a9a',
            'line':      '#d0d0d0',
            'console_bg':     '#1e1a15',
            'console_fg':     '#d4cbb8',
            'console_cursor': '#c4955a',
            'console_sel_bg': '#4a3828',
            'tag_info':    '#7ab3c4',
            'tag_error':   '#c4786a',
            'tag_success': '#7aab7a',
            'tag_warning': '#c4a65a',
            'tag_module':  '#a07ab0',
        }
        self.fonts = {
            'title':   ('Segoe UI', 22, 'bold'),
            'section': ('Segoe UI', 13, 'bold'),
            'heading': ('Segoe UI', 10, 'bold'),
            'bold':    ('Segoe UI', 9, 'bold'),
            'normal':  ('Segoe UI', 9),
            'small':   ('Segoe UI', 7),
            'console': ('Cascadia Code', 9),
        }
        self.setup_ui()
        self.load_module_configs()

    def setup_ui(self):
        self.root.configure(bg=self.colors['parchment'])
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Module.TButton',
                   font=self.fonts['bold'],
                   padding=6,
                   background=self.colors['verde'],)
        style.map('Module.TButton',
                 background=[('active', self.colors['verde_drk']), ('pressed', self.colors['ink'])],
                 foreground=[('active', 'white')])
        style.configure('Execute.TButton',
                       font=self.fonts['heading'],
                       padding=10,
                       background=self.colors['verde'],
                       foreground='white')
        style.map('Execute.TButton',
                 background=[('active', self.colors['verde_drk']), ('pressed', self.colors['verde_drk'])])
        style.configure('Top.TButton',
                       font=self.fonts['normal'],
                       padding=8,
                       background=self.colors['cream'],
                       borderwidth=1)
        style.map('Top.TButton',
                 background=[('active', self.colors['parchment'])])
        style.configure('Card.TFrame',
                       background=self.colors['cream'],
                       borderwidth=0)
        style.configure('TLabelframe',
                       background=self.colors['cream'],
                       borderwidth=2,
                       relief='groove')
        style.configure('TLabelframe.Label',
                       font=self.fonts['heading'],
                       foreground=self.colors['ink'],
                       background=self.colors['cream'])
        main_container = ttk.Frame(self.root, style='Card.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True)
        title_frame = tk.Frame(main_container, bg=self.colors['ink'])
        title_frame.pack(fill=tk.X, pady=(0, 15))
        header_content = tk.Frame(title_frame, bg=self.colors['ink'])
        header_content.pack(fill=tk.BOTH, expand=True, padx=20, pady=15)
        title_container = tk.Frame(header_content, bg=self.colors['ink'])
        title_container.pack(side=tk.LEFT)
        title_text = tk.Frame(title_container, bg=self.colors['ink'])
        title_text.pack(side=tk.LEFT)

        tk.Label(title_text, text="DB MANAGER",
                font=self.fonts['title'],
                bg=self.colors['ink'],
                fg='white').pack(anchor=tk.W)
        
        content_frame = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        content_frame.pack(fill=tk.BOTH, expand=True)
        left_panel = ttk.Frame(content_frame)
        content_frame.add(left_panel, weight=2)
        modules_frame = ttk.LabelFrame(left_panel, text="   Modulos", padding=6)
        modules_frame.pack(fill=tk.BOTH, expand=True)
        
        self.modules = [
            {
                "id": 1,
                "name": "AGREGAR COMENTARIOS",
                "script": str(self.modules_dir / "agregar_comentarios.py"),
                "type": "python",
                "icon": "1",
                "color": "#6495b0",
                "params": ["host", "puerto", "bd", "usuario", "password", "esquema"]
            },
            {
                "id": 2,
                "name": "VALIDAR NOMENCLATURA",
                "script": str(self.modules_dir / "validar_nomenclatura.py"),
                "type": "python",
                "icon": "2",
                "color": "#7a8b96",
                "params": ["host", "puerto", "bd", "usuario", "password", "ruta_salida_html"]
            },
            {
                "id": 3,
                "name": "DICCIONARIO DE DATOS",
                "script": str(self.modules_dir / "generar_diccionario.py"),
                "type": "python",
                "icon": "3",
                "color": "#6495b0",
                "params": ["host", "puerto", "bd", "usuario", "password", "esquema", "ruta_salida_rtf"]
            },
            {
                "id": 4,
                "name": "DATA DE PRUEBA",
                "script": str(self.modules_dir / "data_prueba.py"),
                "type": "python",
                "icon": "4",
                "color": "#7a8b96",
                "params": ["host", "puerto", "bd", "usuario", "password", "esquema", "cantidad_registros"]
            }
        ]
        self.module_buttons = []
        
        for module in self.modules:
            self.create_module_card(modules_frame, module)
            
        right_panel = ttk.Frame(content_frame)
        content_frame.add(right_panel, weight=4)
        config_frame = ttk.LabelFrame(right_panel, text="  Configuracion del Modulo", padding=15)
        config_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        module_header = tk.Frame(config_frame, bg=self.colors['cream'])
        module_header.pack(fill=tk.X, pady=(0, 15))
        self.module_name_var = tk.StringVar(value="Selecciona un módulo")
        tk.Label(module_header, font=self.fonts['section'],
                bg=self.colors['cream'],
                fg=self.colors['ink']).pack(anchor=tk.W)
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

        def _on_mousewheel(event):
            try:
                delta = event.delta
            except AttributeError:
                delta = 0
            if delta:
                move = int(-1 * (delta / 120))
                if move == 0:
                    move = -1 if delta > 0 else 1
                canvas.yview_scroll(move, "units")
            else:
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
        self.btn_frame = tk.Frame(config_frame, bg=self.colors['cream'])
        self.btn_frame.pack(fill=tk.X, pady=(15, 0))
        console_frame = ttk.LabelFrame(right_panel, text=" Consola", padding=10)
        console_frame.configure(height=220)
        console_frame.pack(fill=tk.BOTH, expand=False, pady=(10, 0))
        console_frame.pack_propagate(False)
        console_btn_frame = tk.Frame(console_frame, bg=self.colors['cream'])
        console_btn_frame.pack(fill=tk.X, pady=(0, 8))
        clear_btn = self._make_flat_btn(console_btn_frame, "Limpiar",
                                        self.clear_console, bg=self.colors['plomo'],
                                        font_key='normal', padx=12)
        clear_btn.pack(side=tk.LEFT, padx=5)
        self._add_hover_effect(clear_btn, self.colors['plomo'], self.colors['plomo_drk'])
        copy_btn = self._make_flat_btn(console_btn_frame, "Copiar Log",
                                       self.copy_log, bg=self.colors['plomo'],
                                       font_key='normal', padx=12)
        copy_btn.pack(side=tk.LEFT, padx=5)
        self._add_hover_effect(copy_btn, self.colors['plomo'], self.colors['plomo_drk'])
        console_container = tk.Frame(console_frame,
                                    bg=self.colors['console_bg'],
                                    relief=tk.SOLID,
                                    borderwidth=1,
                                    highlightbackground=self.colors['console_bg'],
                                    highlightthickness=1)
        console_container.pack(fill=tk.BOTH, expand=True)
        self.console_text = scrolledtext.ScrolledText(console_container,
                                                      font=self.fonts['console'],
                                                      bg=self.colors['console_bg'],
                                                      fg=self.colors['console_fg'],
                                                      insertbackground=self.colors['console_cursor'],
                                                      wrap=tk.WORD,
                                                      relief=tk.FLAT,
                                                      padx=10, pady=10,
                                                      selectbackground=self.colors['console_sel_bg'],
                                                      selectforeground='white')
        self.console_text.pack(fill=tk.BOTH, expand=True)
        self.console_text.tag_config("info",    foreground=self.colors['tag_info'])
        self.console_text.tag_config("error",   foreground=self.colors['tag_error'])
        self.console_text.tag_config("success", foreground=self.colors['tag_success'])
        self.console_text.tag_config("warning", foreground=self.colors['tag_warning'])
        self.console_text.tag_config("module",  foreground=self.colors['tag_module'])

    def create_module_card(self, parent, module):
        card_container = tk.Frame(parent, bg=self.colors['cream'],
                                 relief=tk.SOLID, borderwidth=1,
                                 highlightbackground=self.colors['line'],
                                 highlightthickness=1)
        card_container.pack(fill=tk.X, pady=4, padx=6)
        color_bar = tk.Frame(card_container, bg=module['color'], height=2)
        color_bar.pack(fill=tk.X)
        card_content = tk.Frame(card_container, bg=self.colors['cream'])
        card_content.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)
        header = tk.Frame(card_content, bg=self.colors['cream'])
        header.pack(fill=tk.X, pady=(0, 4))
        icon_frame = tk.Frame(header, bg=module['color'], width=36, height=36)
        icon_frame.pack(side=tk.LEFT, padx=(0, 12))
        icon_frame.pack_propagate(False)
        tk.Label(icon_frame, text=module['icon'], font=self.fonts['section'],
                bg=module['color'], fg='white').pack(expand=True)
        info_frame = tk.Frame(header, bg=self.colors['cream'])
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(info_frame, text=f"Módulo {module['id']}",
            font=self.fonts['small'],
                bg=self.colors['cream'],
                fg=self.colors['dust']).pack(anchor=tk.W)
        tk.Label(info_frame, text=module['name'],
            font=self.fonts['bold'],
                bg=self.colors['cream'],
                fg=self.colors['ink']).pack(anchor=tk.W)
        type_badge = tk.Label(header, text=module['type'].upper(),
                     font=self.fonts['small'],
                     bg=self.colors['parchment'],
                     fg=self.colors['dust'],
                     padx=6, pady=2)
        type_badge.pack(side=tk.RIGHT)
        separator = tk.Frame(card_content, bg=self.colors['line'], height=1)
        separator.pack(fill=tk.X, pady=(6, 8))
        btn = self._make_flat_btn(card_content, "Configurar",
                                  lambda m=module: self.select_module(m),
                                  bg=module['color'])
        btn.pack(fill=tk.X)
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

    def _make_flat_btn(self, parent, text, command, bg, fg='white',
                       font_key='bold', padx=10, pady=6):
        """Crea un tk.Button plano con estilo estándar."""
        return tk.Button(parent, text=text, command=command,
                         font=self.fonts[font_key], bg=bg, fg=fg, 
                         cursor='hand2', borderwidth=0,
                         padx=padx, pady=pady)

    def _save_param_history(self, param, value):
        """Guarda el valor de un parámetro en el historial (LRU, máx 10)."""
        if param == 'password':
            return
        self.global_params[param] = value
        history_key = f'_history_{param}'
        param_history = self.config.get(history_key, [])
        if value in param_history:
            param_history.remove(value)
        param_history.append(value)
        if len(param_history) > 10:
            param_history = param_history[-10:]
        self.config[history_key] = param_history

    def _create_param_row(self, parent, param, param_labels):
        """Crea una fila label + widget de entrada para un parámetro. Retorna el tk.StringVar."""
        label_text = param_labels.get(param, param + ":")
        param_history = self.config.get(f'_history_{param}', [])

        param_frame = tk.Frame(parent, bg=self.colors['cream'])
        param_frame.pack(fill=tk.X, pady=5)

        tk.Label(param_frame, text=label_text,
                 font=self.fonts['bold'],
                 bg=self.colors['cream'],
                 fg=self.colors['ink'],
                 width=20, anchor=tk.W).pack(side=tk.LEFT)

        var = tk.StringVar()
        if param_history and param != 'password':
            var.set(param_history[-1])

        if 'ruta' in param.lower():
            entry_frame = tk.Frame(param_frame, bg=self.colors['cream'])
            entry_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
            ttk.Combobox(entry_frame, textvariable=var,
                         font=self.fonts['normal'],
                         values=[''] + param_history,
                         width=38).pack(side=tk.LEFT, fill=tk.X, expand=True)
            is_input = ('plantilla' in param.lower() or
                        ('ddl' in param.lower() and 'salida' not in param.lower()))
            browse_btn = self._make_flat_btn(
                entry_frame, "Abrir" if is_input else "Ruta",
                lambda v=var, p=param: self.browse_path(v, p),
                bg=self.colors['verde'],
                font_key='normal', padx=6, pady=3)
            browse_btn.pack(side=tk.LEFT, padx=(5, 0))
            self._add_hover_effect(browse_btn, self.colors['verde'],
                                   self.colors['verde_drk'])
        elif param == 'password':
            tk.Entry(param_frame, textvariable=var, show="●",
                     font=self.fonts['normal'],
                     width=40).pack(side=tk.LEFT, fill=tk.X, expand=True)
        else:
            ttk.Combobox(param_frame, textvariable=var,
                         font=self.fonts['normal'],
                         values=[''] + param_history,
                         width=38).pack(side=tk.LEFT, fill=tk.X, expand=True)
        return var

    def select_module(self, module):
        self.selected_module = module
        self.module_name_var.set(f"{module['icon']} {module['name']}")
        if module['id'] == 4:
            self.abrir_interfaz_data_prueba(module)
            return

        # Limpiar frames
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        for widget in self.btn_frame.winfo_children():
            widget.destroy()
        self.param_widgets.clear()

        param_labels = {
            "ruta_plantilla_excel": "Ruta Plantilla Excel:",
            "ruta_salida_ddl_base": "Ruta Salida DDL:",
            "host": "Host PostgreSQL:",
            "puerto": "Puerto:",
            "bd": "Base de Datos:",
            "usuario": "Usuario:",
            "password": "Contraseña:",
            "ruta_salida_html": "Ruta de resultados:",
            "ruta_ddl_completo": "Ruta DDL Completo:",
            "esquema": "Esquema:",
            "ruta_salida_rtf": "Ruta para el Diccionario:",
            "cantidad_registros": "Cantidad Registros:"
        }

        info_frame = tk.Frame(self.params_frame, bg=self.colors['cream'])
        info_frame.pack(fill=tk.BOTH, expand=True)

        params_section = tk.Frame(info_frame, bg=self.colors['cream'])
        params_section.pack(fill=tk.X, padx=20, pady=10)

        tk.Label(params_section,
                font=self.fonts['heading'],
                bg=self.colors['cream'],
                fg=self.colors['ink']).pack(anchor=tk.W, pady=(0, 10))

        for param in module['params']:
            self.param_widgets[param] = self._create_param_row(params_section, param, param_labels)

        button_container = tk.Frame(info_frame, bg=self.colors['cream'])
        button_container.pack(pady=15)

        exec_btn = self._make_flat_btn(button_container, "EJECUTAR MODULO",
                                       self.execute_current_module,
                                       bg=self.colors['verde'],
                                       font_key='heading', padx=15, pady=8)
        exec_btn.pack()
        self._add_hover_effect(exec_btn, self.colors['verde'], self.colors['verde_drk'])
        self.log_message(f"Modulo seleccionado: {module['name']}", "module")

    def browse_path(self, var, param_name):
        if 'salida' in param_name.lower():
            p = param_name.lower()
            if 'html' in p:
                ext, types = '.html', [("HTML files", "*.html"), ("All files", "*.*")]
            elif 'ddl' in p:
                ext, types = '.sql',  [("SQL files",  "*.sql"),  ("All files", "*.*")]
            else:
                ext, types = '.rtf',  [("RTF files",  "*.rtf"),  ("All files", "*.*")]
            path = filedialog.asksaveasfilename(
                title="Guardar archivo como",
                defaultextension=ext,
                filetypes=types,
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

    def abrir_interfaz_data_prueba(self, module):
        """interfaz para el módulo de data de prueba"""
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        for widget in self.btn_frame.winfo_children():
            widget.destroy()
        info_frame = tk.Frame(self.params_frame, bg=self.colors['cream'])
        info_frame.pack(fill=tk.BOTH, expand=True)
        params_section = tk.Frame(info_frame, bg=self.colors['cream'])
        params_section.pack(fill=tk.X, padx=10)
        tk.Label(params_section,
                font=self.fonts['heading'],
                bg=self.colors['cream'],
                fg=self.colors['ink']).pack(anchor=tk.W)
        param_labels = {
            "host": "Host PostgreSQL:", "puerto": "Puerto:",
            "bd": "Base de Datos:", "usuario": "Usuario:",
            "password": "Contraseña:", "esquema": "Esquema:",
        }
        basic_params = ["host", "puerto", "bd", "usuario", "password", "esquema"]
        for param in basic_params:
            self.param_widgets[param] = self._create_param_row(params_section, param, param_labels)
        button_container = tk.Frame(info_frame, bg=self.colors['cream'])
        button_container.pack(pady=30)
        open_btn = self._make_flat_btn(button_container, "ABRIR CONFIGURACION",
                                       lambda: self.launch_data_prueba_gui(module),
                                       bg=self.colors['verde'],
                                       font_key='heading', padx=5, pady=5)
        open_btn.pack()
        self._add_hover_effect(open_btn, self.colors['verde'], self.colors['verde_drk'])

    def launch_data_prueba_gui(self, module):
        """interfaz gráfica del módulo de data de prueba"""
        required_params = ["host", "puerto", "bd", "usuario", "password", "esquema"]
        params_values = {}
        for param in required_params:
            if param not in self.param_widgets:
                messagebox.showerror("Error", f"Parámetro '{param}' no configurado")
                return
            value = self.param_widgets[param].get().strip()
            if not value:
                messagebox.showerror("Error", f"El parámetro '{param}' es obligatorio")
                return
            params_values[param] = value
        for param, value in params_values.items():
            self._save_param_history(param, value)
        self.config['_global_params'] = self.global_params
        self.save_config()
        try:
            script_path = self.modules_dir / "data_prueba_gui.py"
            if not script_path.exists():
                messagebox.showerror("Error", f"No se encontró el script: {script_path}")
                return
            import sys
            python_exe = sys.executable
            cmd = [
                python_exe,
                str(script_path),
                params_values['host'],
                params_values['puerto'],
                params_values['bd'],
                params_values['usuario'],
                params_values['password'],
                params_values['esquema']
            ]
            self.log_message("\n" + "="*70, "info")
            self.log_message(f"Abriendo interfaz avanzada de {module['name']}...", "module")
            self.log_message("="*70 + "\n", "info")
            subprocess.Popen(cmd)
            self.log_message("[OK] Interfaz abierta en ventana separada", "success")
            self.log_message("\nConfigura las tablas y genera los datos desde la nueva ventana", "info")
        except Exception as e:
            self.log_message(f"[ERROR] Error al abrir interfaz: {e}", "error")
            messagebox.showerror("Error", f"No se pudo abrir la interfaz: {e}")

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
            self._save_param_history(param, value)
        self.config['_global_params'] = self.global_params
        self.save_config()
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
            import sys
            cmd_args = [params_values[param] for param in module['params']]
            cmd = [sys.executable, module['script']] + cmd_args
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
            duration = (datetime.now() - start_time).total_seconds()
            if self.current_process.returncode == 0:
                self.log_message(f"Tiempo de ejecucion: {duration:.2f} segundos", "success")
            else:
                self.log_message(f"\n Modulo termino con codigo: {self.current_process.returncode}", "error")
            self.current_process = None
        except FileNotFoundError:
            self.log_message(" Error: Python no esta instalado o no esta en PATH", "error")
            found = shutil.which('python')
            if found:
                self.log_message(f"Localizado python en: {found}", "info")
            else:
                self.log_message("No se encontro 'python' en PATH. PATH actual:", "warning")
                self.log_message(os.environ.get('PATH', ''), "info")
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

    def copy_log(self):
        """Copia el contenido del log al portapapeles"""
        log_content = self.console_text.get('1.0', tk.END)
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(log_content)
            self.root.update()
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo copiar el log: {e}")

    def log_message(self, message, tag="info"):
        self.console_text.insert(tk.END, message + "\n", tag)
        self.console_text.see(tk.END)
        self.console_text.update()

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
