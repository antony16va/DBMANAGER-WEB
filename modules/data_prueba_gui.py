import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from data_prueba import SmartDataGenerator

class DataPruebaGUI:

    def __init__(self, root, host, puerto, bd, usuario, password, esquema):
        self.root     = root
        self.root.title("Generación de Data")
        self.root.geometry("1000x700")
        self.root.minsize(1000, 700)
        self.host     = host
        self.puerto   = puerto
        self.bd       = bd
        self.usuario  = usuario
        self.password = password
        self.esquema  = esquema
        self.generator               = None
        self.tabla_vars              = {}
        self.tabla_expanded          = {}
        self.columnas_personalizadas = {}
        self.columna_config_expanded = {}
        self.proceso_activo          = False
        self.cantidad_base_default   = 100
        self.colors = {
            'primary':   '#2c3e50',
            'secondary': '#3498db',
            'bg_light':  '#ecf0f1',
            'bg_card':   '#ffffff',
            'text_dark': '#2c3e50',
            'muted':     '#7f8c8d',
        }
        self.fonts = {
            'title':   ('Segoe UI', 16, 'bold'),
            'section': ('Segoe UI', 11, 'bold'),
            'label':   ('Segoe UI', 10, 'bold'),
            'body':    ('Segoe UI', 9),
            'body_b':  ('Segoe UI', 9, 'bold'),
            'small':   ('Segoe UI', 8),
            'small_b': ('Segoe UI', 8, 'bold'),
            'tiny':    ('Segoe UI', 7),
            'tiny_b':  ('Segoe UI', 7, 'bold'),
            'tiny_i':  ('Segoe UI', 7, 'italic'),
            'console': ('Cascadia Code', 7),
        }
        self.setup_ui()
        self.inicializar_generador()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _tag_for(self, text):
        if '[OK]' in text:    return 'success'
        if '[WARN]' in text:  return 'warning'
        if '[ERROR]' in text: return 'error'
        return 'info'

    def _redirect_stdout(self):
        gui = self
        class _Out:
            def write(self, text):
                if t := text.strip():
                    gui.root.after(0, lambda s=t: gui.log(s, gui._tag_for(s)))
            def flush(self): pass
        return _Out()

    def _flat_btn(self, parent, text, command, bg, fg='white', font_key='small', **kw):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg,
                         font=self.fonts[font_key], relief=tk.FLAT, cursor='hand2', **kw)

    def _add_spinrow(self, parent, label, var, **kw):
        f = tk.Frame(parent, bg='white')
        f.pack(fill=tk.X, pady=3, padx=5)
        tk.Label(f, text=label, font=self.fonts['small'], bg='white').pack(side=tk.LEFT)
        tk.Spinbox(f, textvariable=var, width=12, font=self.fonts['small'], **kw).pack(side=tk.RIGHT)

    # ── UI Setup ──────────────────────────────────────────────────────────────
    def setup_ui(self):
        self.root.configure(bg=self.colors['bg_light'])

        header = tk.Frame(self.root, bg=self.colors['primary'], height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="Generación de data",
                 font=self.fonts['title'],
                 bg=self.colors['primary'], fg='white').pack(pady=8)
        tk.Label(header, text=f"Base de Datos: {self.bd} | Esquema: {self.esquema}",
                 font=self.fonts['body'],
                 bg=self.colors['primary'], fg=self.colors['bg_light']).pack()

        main_container = tk.Frame(self.root, bg=self.colors['bg_light'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        top_panel = tk.Frame(main_container, bg=self.colors['bg_card'], relief=tk.RAISED, bd=2)
        top_panel.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 10))

        header_panel = tk.Frame(top_panel, bg=self.colors['bg_card'])
        header_panel.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(header_panel, text="Seleccionar Tablas",
                 font=self.fonts['section'],
                 bg=self.colors['bg_card'], fg=self.colors['primary']).pack(side=tk.LEFT)
        self._flat_btn(header_panel, "Ninguna", self.deseleccionar_todas,
                       self.colors['primary'], padx=10, pady=3).pack(side=tk.RIGHT, padx=2)
        self._flat_btn(header_panel, "Todas", self.seleccionar_todas,
                       self.colors['secondary'], padx=10, pady=3).pack(side=tk.RIGHT, padx=2)

        ttk.Separator(top_panel, orient='horizontal').pack(fill=tk.X, padx=10)

        self.tabla_frame_container = tk.Frame(top_panel, bg=self.colors['bg_card'])
        self.tabla_frame_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas    = tk.Canvas(self.tabla_frame_container, bg=self.colors['bg_card'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.tabla_frame_container, orient="vertical", command=canvas.yview)
        self.tabla_frame = tk.Frame(canvas, bg=self.colors['bg_card'])
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas_window = canvas.create_window((0, 0), window=self.tabla_frame, anchor="nw")

        def configure_scroll(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_window, width=event.width)
        self.tabla_frame.bind("<Configure>", configure_scroll)
        canvas.bind("<Configure>", configure_scroll)
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        action_panel = tk.Frame(top_panel, bg=self.colors['bg_card'])
        action_panel.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Separator(action_panel, orient='horizontal').pack(fill=tk.X, pady=(0, 10))
        self.limpiar_var = tk.BooleanVar(value=False)
        tk.Checkbutton(action_panel, text="Limpiar tablas antes de insertar",
                       variable=self.limpiar_var,
                       bg=self.colors['bg_card'],
                       font=self.fonts['body_b'],
                       fg=self.colors['primary']).pack(anchor=tk.W, pady=(0, 10))
        self.btn_ejecutar = self._flat_btn(action_panel, "GENERAR DATOS",
                                           self.ejecutar_generacion, self.colors['secondary'],
                                           font_key='section')
        self.btn_ejecutar.pack(fill=tk.X)

        console_panel = tk.Frame(main_container, bg=self.colors['bg_card'], relief=tk.RAISED, bd=2)
        console_panel.pack(side=tk.BOTTOM, fill=tk.X)
        console_header = tk.Frame(console_panel, bg=self.colors['bg_card'])
        console_header.pack(fill=tk.X, pady=5, padx=10)
        tk.Label(console_header, text="Progreso de Generación",
                 font=self.fonts['label'],
                 bg=self.colors['bg_card'], fg=self.colors['primary']).pack(side=tk.LEFT)
        self._flat_btn(console_header, "Limpiar", self.limpiar_console,
                       self.colors['primary'], font_key='tiny_b',
                       padx=8, pady=2).pack(side=tk.RIGHT)

        console_frame = tk.Frame(console_panel, bg='#1e1e1e', relief=tk.SOLID, bd=1)
        console_frame.pack(fill=tk.BOTH, padx=10, pady=(0, 10))
        self.console = scrolledtext.ScrolledText(console_frame,
                                                 font=self.fonts['console'],
                                                 bg="#1e1e1e", fg="#d4d4d4",
                                                 wrap=tk.WORD, relief=tk.FLAT,
                                                 padx=6, pady=6, height=8)
        self.console.pack(fill=tk.BOTH)
        self.console.tag_config("info",    foreground="#4fc1ff")
        self.console.tag_config("success", foreground="#73c991")
        self.console.tag_config("warning", foreground="#cca700")
        self.console.tag_config("error",   foreground="#f48771")

    def log(self, mensaje, tag="info"):
        self.console.insert(tk.END, mensaje + "\n", tag)
        self.console.see(tk.END)
        self.console.update()

    def limpiar_console(self):
        self.console.delete('1.0', tk.END)

    # ── Inicialización y análisis ─────────────────────────────────────────────
    def inicializar_generador(self):
        self.log("="*60, "info")
        self.log("INICIALIZANDO GENERADOR DE DATOS", "info")
        self.log("="*60, "info")
        self.log(f"Conectando a: {self.bd}@{self.host}:{self.puerto}", "info")
        try:
            self.generator = SmartDataGenerator(
                self.host, self.puerto, self.bd,
                self.usuario, self.password, self.esquema
            )
            if not self.generator.conectar():
                messagebox.showerror("Error de Conexión", "No se pudo conectar a la base de datos")
                self.root.destroy()
                return
            self.log("[OK] Conexión establecida", "success")
            self.cantidad_base_default = self.generator.config.get('cantidad_base', 100)
            self.log(f"[OK] Cantidad base configurada: {self.cantidad_base_default} registros", "success")
            self.log("\nAnalizando estructura de la base de datos...", "info")
            threading.Thread(target=self._analizar_bd_thread, daemon=True).start()
        except Exception as e:
            self.log(f"[ERROR] {str(e)}", "error")
            messagebox.showerror("Error", f"Error al inicializar: {e}")
            self.root.destroy()

    def _analizar_bd_thread(self):
        old_stdout, sys.stdout = sys.stdout, self._redirect_stdout()
        try:
            self.generator.analizar_base_datos()
        except Exception as e:
            self.root.after(0, lambda: self.log(f"[ERROR] {str(e)}", "error"))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Error en análisis: {e}"))
        else:
            self.root.after(0, self.crear_controles_tablas)
        finally:
            sys.stdout = old_stdout

    def crear_controles_tablas(self):
        self.log("\n" + "="*60, "info")
        self.log("TABLAS DISPONIBLES", "info")
        self.log("="*60 + "\n", "info")
        orden_carga = self.generator.metadata['orden_carga']
        for i, tabla in enumerate(orden_carga, 1):
            self.crear_control_tabla(i, tabla)
        self.log("\nAjusta los rangos por defecto si hay columnas sin patrón identificado.", "info")
        self.log(f"Total de tablas: {len(orden_carga)}", "success")
        self.log("\nConfigura las tablas y presiona 'GENERAR DATOS'", "info")

    # ── Controles de tabla ────────────────────────────────────────────────────
    def crear_control_tabla(self, numero, tabla):
        container_frame = tk.Frame(self.tabla_frame, bg='white', relief=tk.SOLID, bd=1)
        container_frame.pack(fill=tk.X, pady=3, padx=5)
        header_frame = tk.Frame(container_frame, bg='white')
        header_frame.pack(fill=tk.X, padx=8, pady=8)

        self.tabla_expanded[tabla] = tk.BooleanVar(value=False)
        expand_btn = tk.Button(header_frame, text="▶", font=self.fonts['small'],
                               bg='white', fg=self.colors['secondary'],
                               relief=tk.FLAT, cursor='hand2', width=2,
                               command=lambda t=tabla, c=container_frame: self._toggle_columnas(t, c))
        expand_btn.pack(side=tk.LEFT, padx=(0, 5))

        var_check = tk.BooleanVar(value=True)
        tk.Checkbutton(header_frame, variable=var_check, bg='white').pack(side=tk.LEFT)

        nombre_frame = tk.Frame(header_frame, bg='white')
        nombre_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        tk.Label(nombre_frame, text=f"{numero}.",
                 font=self.fonts['body'], bg='white', fg='#7f8c8d').pack(side=tk.LEFT)
        tk.Label(nombre_frame, text=tabla,
                 font=self.fonts['label'], bg='white', fg=self.colors['primary']).pack(side=tk.LEFT, padx=5)
        info_text = self._get_tabla_info(tabla)
        if info_text:
            tk.Label(nombre_frame, text=info_text,
                     font=self.fonts['small'], bg='white', fg='#95a5a6').pack(side=tk.LEFT, padx=5)

        cantidad_frame = tk.Frame(header_frame, bg='white')
        cantidad_frame.pack(side=tk.RIGHT)
        tk.Label(cantidad_frame, text="Registros:",
                 font=self.fonts['body'], bg='white').pack(side=tk.LEFT, padx=(0, 5))
        var_cantidad = tk.IntVar(value=self._calcular_cantidad_inicial(tabla))
        tk.Spinbox(cantidad_frame, from_=1, to=100000, textvariable=var_cantidad,
                   width=8, font=self.fonts['body']).pack(side=tk.LEFT)

        columnas_frame = tk.Frame(container_frame, bg='#f8f9fa')
        self.tabla_vars[tabla] = (var_check, var_cantidad, expand_btn, columnas_frame)

    def _calcular_cantidad_inicial(self, tabla):
        cantidad_config = self.generator.config.get('cantidad_por_tabla', {}).get(tabla)
        return cantidad_config if cantidad_config is not None else self.cantidad_base_default

    def _get_tabla_info(self, tabla):
        num_fks = len(self.generator.metadata['fks'].get(tabla, []))
        return f"FK: {num_fks}" if num_fks else ""

    def _toggle_columnas(self, tabla, container_frame):
        _, _, expand_btn, columnas_frame = self.tabla_vars[tabla]
        if self.tabla_expanded[tabla].get():
            columnas_frame.pack_forget()
            expand_btn.config(text="▶")
            self.tabla_expanded[tabla].set(False)
        else:
            if not columnas_frame.winfo_children():
                self._crear_lista_columnas(tabla, columnas_frame)
            columnas_frame.pack(fill=tk.BOTH, padx=15, pady=(0, 10))
            expand_btn.config(text="▼")
            self.tabla_expanded[tabla].set(True)

    def _crear_lista_columnas(self, tabla, columnas_frame):
        if tabla not in self.generator.metadata['columnas']:
            return
        for i, col_info in enumerate(self.generator.metadata['columnas'][tabla]):
            self._crear_control_columna(columnas_frame, tabla, col_info, i)

    def _crear_control_columna(self, parent, tabla, col_info, index):
        bg = '#f8f9fa' if index % 2 == 0 else '#ffffff'
        col_container = tk.Frame(parent, bg=bg)
        col_container.pack(fill=tk.X, padx=5, pady=1)
        col_header = tk.Frame(col_container, bg=bg)
        col_header.pack(fill=tk.X, padx=8, pady=4)

        col_key    = f"{tabla}.{col_info['nombre']}"
        expand_btn = tk.Button(col_header, text="▶", font=self.fonts['tiny'],
                               bg=bg, fg=self.colors['secondary'],
                               relief=tk.FLAT, cursor='hand2', width=1,
                               command=lambda: self._toggle_config_columna(tabla, col_info, col_container))
        expand_btn.pack(side=tk.LEFT, padx=(0, 5))

        tk.Label(col_header, text=col_info['nombre'],
                 font=self.fonts['body'], bg=bg, fg=self.colors['primary']).pack(side=tk.LEFT)

        tipo_display = col_info['udt_name'] or col_info['tipo_dato']
        if col_info.get('max_length'):
            tipo_display = f"{tipo_display}({col_info['max_length']})"
        tk.Label(col_header, text=tipo_display,
                 font=self.fonts['small'], bg=bg, fg='#6c757d').pack(side=tk.LEFT, padx=10)

        meta        = self.generator.metadata
        indicadores = []
        if tabla in meta['pks'] and col_info['nombre'] in meta['pks'][tabla]:
            indicadores.append('PK')
        if any(fk['columna'] == col_info['nombre'] for fk in meta['fks'].get(tabla, [])):
            indicadores.append('FK')
        if tabla in meta['uniques'] and col_info['nombre'] in meta['uniques'][tabla]:
            indicadores.append('UQ')
        if not col_info['nullable']:
            indicadores.append('NN')
        if indicadores:
            tk.Label(col_header, text=' | '.join(indicadores),
                     font=self.fonts['tiny_b'], bg=bg, fg=self.colors['muted']).pack(side=tk.LEFT, padx=5)
        if col_key in self.columnas_personalizadas:
            tk.Label(col_header, text="Personalizado",
                     font=self.fonts['tiny_b'], bg=bg, fg=self.colors['secondary']).pack(side=tk.LEFT, padx=10)

        config_frame = tk.Frame(col_container, bg='#e9ecef')
        expand_btn.config_frame = config_frame
        expand_btn.col_key      = col_key

    def _toggle_config_columna(self, tabla, col_info, col_container):
        col_key               = f"{tabla}.{col_info['nombre']}"
        expand_btn, config_frame = None, None
        for widget in col_container.winfo_children():
            if isinstance(widget, tk.Frame) and widget['bg'] == '#e9ecef':
                config_frame = widget
            else:
                for child in widget.winfo_children():
                    if isinstance(child, tk.Button) and getattr(child, 'col_key', None) == col_key:
                        expand_btn = child
                        break
        if not config_frame or not expand_btn:
            return
        if self.columna_config_expanded.get(col_key, False):
            config_frame.pack_forget()
            expand_btn.config(text="▶")
            self.columna_config_expanded[col_key] = False
        else:
            if not config_frame.winfo_children():
                self._crear_panel_config_columna(config_frame, tabla, col_info)
            config_frame.pack(fill=tk.X, padx=20, pady=(0, 8))
            expand_btn.config(text="▼")
            self.columna_config_expanded[col_key] = True

    def _auto_save_columna(self, col_key, col_tipo, config_vars, *_):
        """Guarda la configuración de la columna al instante, sin recargar la UI."""
        try:
            if col_tipo in ('int2', 'smallint', 'int4', 'integer', 'int8', 'bigint'):
                config = {'min': config_vars['min'].get(), 'max': config_vars['max'].get()}
            elif col_tipo in ('numeric', 'decimal'):
                config = {'min': config_vars['min'].get(), 'max': config_vars['max'].get(),
                          'decimales': config_vars['decimales'].get()}
            elif col_tipo in ('varchar', 'character varying', 'bpchar', 'char', 'character', 'text'):
                config = {'longitud': config_vars['longitud'].get(),
                          'usar_faker': config_vars.get('usar_faker', tk.BooleanVar(value=False)).get()}
            elif col_tipo in ('date', 'timestamp', 'timestamptz', 'timestamp with time zone'):
                config = {'fecha_inicio': config_vars['fecha_inicio'].get(),
                          'fecha_fin':    config_vars['fecha_fin'].get()}
            elif col_tipo == 'bool':
                config = {'prob_true': config_vars['prob_true'].get()}
            else:
                return
            self.columnas_personalizadas[col_key] = {'tipo': col_tipo, 'config': config}
        except Exception:
            pass  # ignorar estados intermedios (e.g. campo vacío mientras se escribe)

    # ── Panel de configuración de columna ─────────────────────────────────────
    def _crear_panel_config_columna(self, parent, tabla, col_info):
        col_nombre = col_info['nombre']
        col_tipo   = (col_info['udt_name'] or col_info['tipo_dato']).lower()
        col_key    = f"{tabla}.{col_nombre}"

        config_area = tk.Frame(parent, bg='#ffffff')
        config_area.pack(fill=tk.X, padx=10, pady=8)
        config_vars = {}

        if col_tipo in ('int2', 'smallint', 'int4', 'integer', 'int8', 'bigint'):
            self._crear_controles_integer(config_area, col_info, col_key, config_vars)
        elif col_tipo in ('numeric', 'decimal'):
            self._crear_controles_numeric(config_area, col_info, col_key, config_vars)
        elif col_tipo in ('varchar', 'character varying', 'bpchar', 'char', 'character', 'text'):
            self._crear_controles_text(config_area, col_info, col_key, config_vars)
        elif col_tipo in ('date', 'timestamp', 'timestamptz', 'timestamp with time zone'):
            self._crear_controles_date(config_area, col_info, col_key, config_vars)
        elif col_tipo == 'bool':
            self._crear_controles_boolean(config_area, col_info, col_key, config_vars)
        else:
            tk.Label(config_area, text=f"Tipo '{col_tipo}' no soportado",
                     font=self.fonts['small'], bg='white', fg=self.colors['primary']).pack(pady=10)
            return

        # Vincular auto-guardado a cada variable
        for var in config_vars.values():
            var.trace_add('write', lambda *_, k=col_key, t=col_tipo, cv=config_vars:
                          self._auto_save_columna(k, t, cv))

    def _crear_controles_integer(self, parent, col_info, col_key, config_vars):
        config_actual = self.columnas_personalizadas.get(col_key, {}).get('config', {})
        rangos        = self.generator.config.get('rangos_personalizados', {}).get('integer', {})
        config_vars['min'] = tk.IntVar(value=config_actual.get('min', rangos.get('min', 1)))
        config_vars['max'] = tk.IntVar(value=config_actual.get('max', rangos.get('max', 1000000)))
        self._add_spinrow(parent, "Min:", config_vars['min'], from_=-2147483648, to=2147483647)
        self._add_spinrow(parent, "Max:", config_vars['max'], from_=-2147483648, to=2147483647)

    def _crear_controles_numeric(self, parent, col_info, col_key, config_vars):
        config_actual = self.columnas_personalizadas.get(col_key, {}).get('config', {})
        config_vars['min']       = tk.DoubleVar(value=config_actual.get('min', 0.0))
        config_vars['max']       = tk.DoubleVar(value=config_actual.get('max', 10000.0))
        config_vars['decimales'] = tk.IntVar(value=config_actual.get('decimales', 2))
        self._add_spinrow(parent, "Min:",       config_vars['min'],       from_=-999999999, to=999999999, increment=0.01)
        self._add_spinrow(parent, "Max:",       config_vars['max'],       from_=-999999999, to=999999999, increment=0.01)
        self._add_spinrow(parent, "Decimales:", config_vars['decimales'], from_=0, to=10)

    def _crear_controles_text(self, parent, col_info, col_key, config_vars):
        config_actual = self.columnas_personalizadas.get(col_key, {}).get('config', {})
        texto_config  = self.generator.config.get('texto', {})
        max_len       = col_info.get('max_length') or texto_config.get('max_length_text', 50)
        config_vars['longitud'] = tk.IntVar(value=config_actual.get('longitud', max_len))
        self._add_spinrow(parent, "Longitud:", config_vars['longitud'], from_=1, to=5000)
        if self.generator and self.generator.faker:
            config_vars['usar_faker'] = tk.BooleanVar(value=config_actual.get('usar_faker', False))
            tk.Checkbutton(parent, text="Usar Faker (texto realista)",
                           variable=config_vars['usar_faker'],
                           bg='white', font=self.fonts['small']).pack(anchor=tk.W, pady=5, padx=5)

    def _crear_controles_date(self, parent, col_info, col_key, config_vars):
        config_actual = self.columnas_personalizadas.get(col_key, {}).get('config', {})
        for key, label, default in [('fecha_inicio', 'Desde:', '2020-01-01'),
                                    ('fecha_fin',    'Hasta:', '2025-12-31')]:
            f = tk.Frame(parent, bg='white')
            f.pack(fill=tk.X, pady=3, padx=5)
            tk.Label(f, text=label, font=self.fonts['small'], bg='white').pack(side=tk.LEFT)
            config_vars[key] = tk.StringVar(value=config_actual.get(key, default))
            tk.Entry(f, textvariable=config_vars[key], width=12,
                     font=self.fonts['small']).pack(side=tk.RIGHT)

    def _crear_controles_boolean(self, parent, col_info, col_key, config_vars):
        config_actual = self.columnas_personalizadas.get(col_key, {}).get('config', {})
        config_vars['prob_true'] = tk.DoubleVar(value=config_actual.get('prob_true', 0.5))
        self._add_spinrow(parent, "Prob. True:", config_vars['prob_true'],
                          from_=0.0, to=1.0, increment=0.05)
        tk.Label(parent, text="(ej: 0.8 = 80% True)",
                 font=self.fonts['tiny_i'], bg='white', fg='#6c757d').pack(anchor=tk.W, pady=3, padx=5)

    def _refrescar_indicador_columna(self, tabla, col_nombre):
        if tabla not in self.tabla_vars:
            return
        _, _, _, columnas_frame = self.tabla_vars[tabla]
        if self.tabla_expanded[tabla].get():
            for widget in columnas_frame.winfo_children():
                widget.destroy()
            self._crear_lista_columnas(tabla, columnas_frame)

    def seleccionar_todas(self):
        for var_check, *_ in self.tabla_vars.values():
            var_check.set(True)

    def deseleccionar_todas(self):
        for var_check, *_ in self.tabla_vars.values():
            var_check.set(False)

    # ── Ejecución de generación ───────────────────────────────────────────────
    def ejecutar_generacion(self):
        if self.proceso_activo:
            messagebox.showwarning("Advertencia", "Ya hay un proceso en ejecución")
            return
        tablas_seleccionadas = [
            (tabla, var_cantidad.get())
            for tabla, (var_check, var_cantidad, _, _) in self.tabla_vars.items()
            if var_check.get()
        ]
        self._aplicar_config_desde_ui()
        if not tablas_seleccionadas:
            messagebox.showwarning("Advertencia", "Debes seleccionar al menos una tabla")
            return
        mensaje = f"¿Generar datos para {len(tablas_seleccionadas)} tabla(s)?"
        if self.limpiar_var.get():
            mensaje += "\n\n[ADVERTENCIA] Se limpiaran las tablas antes de insertar"
        if not messagebox.askyesno("Confirmar", mensaje):
            return
        self.btn_ejecutar.config(state=tk.DISABLED, text="GENERANDO...")
        self.proceso_activo = True
        self.console.delete('1.0', tk.END)
        threading.Thread(target=self._generar_datos_thread, args=(tablas_seleccionadas,), daemon=True).start()

    def _aplicar_config_desde_ui(self):
        self.generator.config['columnas_personalizadas'] = self.columnas_personalizadas.copy()

    def _generar_datos_thread(self, tablas_seleccionadas):
        old_stdout = sys.stdout
        try:
            sys.stdout = self._redirect_stdout()
            self.log("="*60, "info")
            self.log("INICIANDO GENERACIÓN DE DATOS", "info")
            self.log("="*60 + "\n", "info")

            orden_carga      = self.generator.metadata['orden_carga']
            tablas_dict      = dict(tablas_seleccionadas)
            tablas_ordenadas = [(t, tablas_dict[t]) for t in orden_carga if t in tablas_dict]
            self.log(f"Orden de carga (respetando FK): {[t for t, _ in tablas_ordenadas]}\n", "info")

            if self.limpiar_var.get():
                self.log("Limpiando SOLO tablas seleccionadas (no todas del esquema)...\n", "warning")
                for tabla, _ in reversed(tablas_ordenadas):
                    try:
                        self.generator.cursor.execute(f'TRUNCATE TABLE {self.esquema}.{tabla} CASCADE')
                        self.generator.conn.commit()
                        self.log(f"  [OK] {tabla} limpiada", "success")
                    except Exception as e:
                        self.log(f"  [ERROR] {tabla}: {e}", "error")
                        self.generator.conn.rollback()
                self.log("", "info")

            total_insertados = 0
            for i, (tabla, cantidad) in enumerate(tablas_ordenadas, 1):
                self.log(f"[{i}/{len(tablas_ordenadas)}] {tabla}", "info")
                self.log(f"  -> Generando {cantidad} registros...", "info")
                try:
                    registros  = self.generator.generar_registros_tabla(tabla, cantidad)
                    self.log(f"  -> Insertando...", "info")
                    insertados = self.generator.insertar_registros(tabla, registros)
                    if insertados > 0:
                        self.log(f"  [OK] {insertados} registros insertados\n", "success")
                        total_insertados += insertados
                    else:
                        self.log(f"  [WARN] 0 registros insertados\n", "warning")
                except Exception as e:
                    self.log(f"  [ERROR] {str(e)}\n", "error")

            self.log("\n" + "="*60, "info")
            self.log("GENERACIÓN COMPLETADA", "success")
            self.log("="*60 + "\n", "info")
            self.log(f"Total de registros insertados: {total_insertados:,}", "success")
            self.root.after(0, lambda: messagebox.showinfo(
                "Completado",
                f"Generación completada exitosamente\n\nTotal de registros: {total_insertados:,}"
            ))
        except Exception as e:
            self.log(f"\n[ERROR] {str(e)}", "error")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Error durante la generación: {e}"))
        finally:
            sys.stdout = old_stdout
            self.root.after(0, lambda: self.btn_ejecutar.config(state=tk.NORMAL, text="GENERAR DATOS"))
            self.proceso_activo = False


def main():
    if len(sys.argv) < 7:
        print("Error: Faltan parámetros")
        print("Uso: python data_prueba_gui.py <host> <puerto> <bd> <usuario> <password> <esquema>")
        sys.exit(1)
    host     = sys.argv[1]
    puerto   = sys.argv[2]
    bd       = sys.argv[3]
    usuario  = sys.argv[4]
    password = sys.argv[5]
    esquema  = sys.argv[6]
    root = tk.Tk()
    DataPruebaGUI(root, host, puerto, bd, usuario, password, esquema)
    root.mainloop()

if __name__ == "__main__":
    main()
