import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import os
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from data_prueba import SmartDataGenerator

class DataPruebaGUI:

    def __init__(self, root, host, puerto, bd, usuario, password, esquema):
        self.root = root
        self.root.title("Generación de Data")
        self.root.geometry("1000x700")
        self.root.minsize(1000, 700)
        self.host = host
        self.puerto = puerto
        self.bd = bd
        self.usuario = usuario
        self.password = password
        self.esquema = esquema
        self.generator = None
        self.tabla_vars = {}
        self.tabla_expanded = {}
        self.columnas_personalizadas = {}
        self.columna_config_expanded = {}
        self.proceso_activo = False
        self.cantidad_base_default = 100
        self.colors = {
            'primary': '#2c3e50',
            'secondary': '#3498db',
            'success': '#27ae60',
            'warning': '#f39c12',
            'danger': '#e74c3c',
            'bg_light': '#ecf0f1',
            'bg_card': '#ffffff',
            'text_dark': '#2c3e50',
        }
        self.setup_ui()
        self.inicializar_generador()

    def setup_ui(self):
        self.root.configure(bg=self.colors['bg_light'])
        header = tk.Frame(self.root, bg=self.colors['primary'], height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="Generación de data",
                font=('Segoe UI', 16, 'bold'),
                bg=self.colors['primary'], fg='white').pack(pady=8)
        info_text = f"Base de Datos: {self.bd} | Esquema: {self.esquema}"
        tk.Label(header, text=info_text,
                font=('Segoe UI', 9),
                bg=self.colors['primary'], fg=self.colors['bg_light']).pack()
        main_container = tk.Frame(self.root, bg=self.colors['bg_light'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        top_panel = tk.Frame(main_container, bg=self.colors['bg_card'], relief=tk.RAISED, bd=2)
        top_panel.pack(side=tk.TOP, fill=tk.BOTH, expand=True, pady=(0, 10))
        header_panel = tk.Frame(top_panel, bg=self.colors['bg_card'])
        header_panel.pack(fill=tk.X, padx=10, pady=10)
        tk.Label(header_panel, text="Seleccionar Tablas",
                font=('Segoe UI', 11, 'bold'),
                bg=self.colors['bg_card'], fg=self.colors['primary']).pack(side=tk.LEFT)
        tk.Button(header_panel, text="Todas",
                 command=self.seleccionar_todas,
                 bg=self.colors['success'], fg='white',
                 font=('Segoe UI', 8), relief=tk.FLAT, cursor='hand2',
                 padx=10, pady=3).pack(side=tk.RIGHT, padx=2)
        tk.Button(header_panel, text="Ninguna",
                 command=self.deseleccionar_todas,
                 bg=self.colors['danger'], fg='white',
                 font=('Segoe UI', 8), relief=tk.FLAT, cursor='hand2',
                 padx=10, pady=3).pack(side=tk.RIGHT, padx=2)
        ttk.Separator(top_panel, orient='horizontal').pack(fill=tk.X, padx=10)
        self.tabla_frame_container = tk.Frame(top_panel, bg=self.colors['bg_card'])
        self.tabla_frame_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        canvas = tk.Canvas(self.tabla_frame_container, bg=self.colors['bg_card'], highlightthickness=0)
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

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        action_panel = tk.Frame(top_panel, bg=self.colors['bg_card'])
        action_panel.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Separator(action_panel, orient='horizontal').pack(fill=tk.X, pady=(0, 10))
        self.limpiar_var = tk.BooleanVar(value=False)
        tk.Checkbutton(action_panel, text="Limpiar tablas antes de insertar",
                      variable=self.limpiar_var,
                      bg=self.colors['bg_card'],
                      font=('Segoe UI', 9, 'bold'),
                      fg=self.colors['danger']).pack(anchor=tk.W, pady=(0, 10))
        self.btn_ejecutar = tk.Button(action_panel, text="GENERAR DATOS",
                                      command=self.ejecutar_generacion,
                                      bg=self.colors['success'], fg='white',
                                      font=('Segoe UI', 11, 'bold'),
                                      relief=tk.FLAT, cursor='hand2')
        self.btn_ejecutar.pack(fill=tk.X)
        console_panel = tk.Frame(main_container, bg=self.colors['bg_card'], relief=tk.RAISED, bd=2)
        console_panel.pack(side=tk.BOTTOM, fill=tk.X)
        console_header = tk.Frame(console_panel, bg=self.colors['bg_card'])
        console_header.pack(fill=tk.X, pady=5, padx=10)
        tk.Label(console_header, text="Progreso de Generación",
                font=('Segoe UI', 10, 'bold'),
                bg=self.colors['bg_card'], fg=self.colors['primary']).pack(side=tk.LEFT)
        tk.Button(console_header, text="Limpiar",
                 command=self.limpiar_console,
                 bg=self.colors['warning'], fg='white',
                 font=('Segoe UI', 7, 'bold'),
                 relief=tk.FLAT, cursor='hand2',
                 padx=8, pady=2).pack(side=tk.RIGHT)
        console_frame = tk.Frame(console_panel, bg='#1e1e1e', relief=tk.SOLID, bd=1)
        console_frame.pack(fill=tk.BOTH, padx=10, pady=(0, 10))
        self.console = scrolledtext.ScrolledText(console_frame,
                                                 font=("Cascadia Code", 7),
                                                 bg="#1e1e1e", fg="#d4d4d4",
                                                 wrap=tk.WORD, relief=tk.FLAT,
                                                 padx=6, pady=6,
                                                 height=8)
        self.console.pack(fill=tk.BOTH)
        self.console.tag_config("info", foreground="#4fc1ff")
        self.console.tag_config("success", foreground="#73c991")
        self.console.tag_config("warning", foreground="#cca700")
        self.console.tag_config("error", foreground="#f48771")

    def log(self, mensaje, tag="info"):
        self.console.insert(tk.END, mensaje + "\n", tag)
        self.console.see(tk.END)
        self.console.update()

    def limpiar_console(self):
        self.console.delete('1.0', tk.END)

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
                messagebox.showerror("Error de Conexión",
                                   "No se pudo conectar a la base de datos")
                self.root.destroy()
                return
            self.log("[OK] Conexión establecida", "success")
            self.cantidad_base_default = self.generator.config.get('cantidad_base', 100)
            self.log(f"[OK] Cantidad base configurada: {self.cantidad_base_default} registros", "success")
            self.log("\nAnalizando estructura de la base de datos...", "info")
            thread = threading.Thread(target=self._analizar_bd_thread, daemon=True)
            thread.start()
        except Exception as e:
            self.log(f"[ERROR] {str(e)}", "error")
            messagebox.showerror("Error", f"Error al inicializar: {e}")
            self.root.destroy()

    def _analizar_bd_thread(self):
        try:
            import sys

            class GUIOutput:

                def __init__(self, gui):
                    self.gui = gui

                def write(self, text):
                    if text.strip():
                        t = text.strip()
                        if '[OK]' in t:
                            self.gui.root.after(0, lambda txt=t: self.gui.log(txt, "success"))
                        elif '[WARN]' in t:
                            self.gui.root.after(0, lambda txt=t: self.gui.log(txt, "warning"))
                        elif '[ERROR]' in t:
                            self.gui.root.after(0, lambda txt=t: self.gui.log(txt, "error"))
                        else:
                            self.gui.root.after(0, lambda txt=t: self.gui.log(txt, "info"))

                def flush(self):
                    pass
            old_stdout = sys.stdout
            sys.stdout = GUIOutput(self)
            try:
                self.generator.analizar_base_datos()
            finally:
                sys.stdout = old_stdout
            self.root.after(0, self.crear_controles_tablas)
        except Exception as e:
            self.root.after(0, lambda: self.log(f"[ERROR] {str(e)}", "error"))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Error en análisis: {e}"))

    def crear_controles_tablas(self):
        self.log("\n" + "="*60, "info")
        self.log("TABLAS DISPONIBLES", "info")
        self.log("="*60 + "\n", "info")
        orden_carga = self.generator.metadata['orden_carga']
        for i, tabla in enumerate(orden_carga, 1):
            self.crear_control_tabla(i, tabla)
        self.log("\nAjusta los rangos por defecto (panel izquierdo) si hay columnas sin patrón identificado.", "info")
        self.log(f"Total de tablas: {len(orden_carga)}", "success")
        self.log("\nConfigura las tablas y presiona 'GENERAR DATOS'", "info")

    def crear_control_tabla(self, numero, tabla):
        container_frame = tk.Frame(self.tabla_frame, bg='white', relief=tk.SOLID, bd=1)
        container_frame.pack(fill=tk.X, pady=3, padx=5)
        header_frame = tk.Frame(container_frame, bg='white')
        header_frame.pack(fill=tk.X, padx=8, pady=8)
        expand_var = tk.BooleanVar(value=False)
        self.tabla_expanded[tabla] = expand_var
        expand_btn = tk.Button(header_frame, text="▶", font=('Segoe UI', 8),
                              bg='white', fg=self.colors['secondary'],
                              relief=tk.FLAT, cursor='hand2', width=2,
                              command=lambda t=tabla, c=container_frame: self._toggle_columnas(t, c))
        expand_btn.pack(side=tk.LEFT, padx=(0, 5))
        var_check = tk.BooleanVar(value=True)
        check = tk.Checkbutton(header_frame, variable=var_check, bg='white')
        check.pack(side=tk.LEFT)
        nombre_frame = tk.Frame(header_frame, bg='white')
        nombre_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        tk.Label(nombre_frame, text=f"{numero}.",
                font=('Segoe UI', 9),
                bg='white', fg='#7f8c8d').pack(side=tk.LEFT)
        tk.Label(nombre_frame, text=tabla,
                font=('Segoe UI', 10, 'bold'),
                bg='white', fg=self.colors['primary']).pack(side=tk.LEFT, padx=5)
        info_text = self._get_tabla_info(tabla)
        if info_text:
            tk.Label(nombre_frame, text=info_text,
                    font=('Segoe UI', 8),
                    bg='white', fg='#95a5a6').pack(side=tk.LEFT, padx=5)
        cantidad_frame = tk.Frame(header_frame, bg='white')
        cantidad_frame.pack(side=tk.RIGHT)
        tk.Label(cantidad_frame, text="Registros:",
                font=('Segoe UI', 9),
                bg='white').pack(side=tk.LEFT, padx=(0, 5))
        cantidad_inicial = self._calcular_cantidad_inicial(tabla)
        var_cantidad = tk.IntVar(value=cantidad_inicial)
        spinbox = tk.Spinbox(cantidad_frame, from_=1, to=100000,
                            textvariable=var_cantidad,
                            width=8, font=('Segoe UI', 9))
        spinbox.pack(side=tk.LEFT)
        columnas_frame = tk.Frame(container_frame, bg='#f8f9fa')
        self.tabla_vars[tabla] = (var_check, var_cantidad, expand_btn, columnas_frame)

    def _calcular_cantidad_inicial(self, tabla):
        cantidad_config = self.generator.config.get('cantidad_por_tabla', {}).get(tabla)
        if cantidad_config is not None:
            return cantidad_config
        return self.cantidad_base_default

    def _get_tabla_info(self, tabla):
        info_parts = []
        if tabla in self.generator.metadata['fks']:
            num_fks = len(self.generator.metadata['fks'][tabla])
            if num_fks > 0:
                info_parts.append(f"FK: {num_fks}")
        return " | ".join(info_parts) if info_parts else ""

    def _toggle_columnas(self, tabla, container_frame):
        var_check, var_cantidad, expand_btn, columnas_frame = self.tabla_vars[tabla]
        is_expanded = self.tabla_expanded[tabla].get()
        if is_expanded:
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
        columnas = self.generator.metadata['columnas'][tabla]
        for i, col_info in enumerate(columnas):
            self._crear_control_columna(columnas_frame, tabla, col_info, i)

    def _crear_control_columna(self, parent, tabla, col_info, index):
        col_container = tk.Frame(parent, bg='#f8f9fa' if index % 2 == 0 else '#ffffff')
        col_container.pack(fill=tk.X, padx=5, pady=1)
        col_header = tk.Frame(col_container, bg=col_container['bg'])
        col_header.pack(fill=tk.X, padx=8, pady=4)
        col_key = f"{tabla}.{col_info['nombre']}"
        expand_btn = tk.Button(col_header, text="▶", font=('Segoe UI', 7),
                              bg=col_container['bg'], fg=self.colors['secondary'],
                              relief=tk.FLAT, cursor='hand2', width=1,
                              command=lambda: self._toggle_config_columna(tabla, col_info, col_container))
        expand_btn.pack(side=tk.LEFT, padx=(0, 5))
        nombre_label = tk.Label(col_header, text=col_info['nombre'],
                               font=('Segoe UI', 9),
                               bg=col_container['bg'], fg=self.colors['primary'])
        nombre_label.pack(side=tk.LEFT)
        tipo_display = col_info['udt_name'] or col_info['tipo_dato']
        if col_info.get('max_length'):
            tipo_display = f"{tipo_display}({col_info['max_length']})"
        tipo_label = tk.Label(col_header, text=tipo_display,
                             font=('Segoe UI', 8),
                             bg=col_container['bg'], fg='#6c757d')
        tipo_label.pack(side=tk.LEFT, padx=10)
        indicadores = []
        if tabla in self.generator.metadata['pks'] and col_info['nombre'] in self.generator.metadata['pks'][tabla]:
            indicadores.append('PK')
        if tabla in self.generator.metadata['fks']:
            for fk in self.generator.metadata['fks'][tabla]:
                if fk['columna'] == col_info['nombre']:
                    indicadores.append('FK')
                    break
        if tabla in self.generator.metadata['uniques'] and col_info['nombre'] in self.generator.metadata['uniques'][tabla]:
            indicadores.append('UQ')
        if not col_info['nullable']:
            indicadores.append('NN')
        if indicadores:
            ind_text = ' | '.join(indicadores)
            tk.Label(col_header, text=ind_text,
                    font=('Segoe UI', 7, 'bold'),
                    bg=col_container['bg'], fg=self.colors['warning']).pack(side=tk.LEFT, padx=5)
        if col_key in self.columnas_personalizadas:
            tk.Label(col_header, text="✓ Personalizado",
                    font=('Segoe UI', 7, 'bold'),
                    bg=col_container['bg'], fg=self.colors['success']).pack(side=tk.LEFT, padx=10)
        config_frame = tk.Frame(col_container, bg='#e9ecef')
        expand_btn.config_frame = config_frame
        expand_btn.col_key = col_key

    def _toggle_config_columna(self, tabla, col_info, col_container):
        col_key = f"{tabla}.{col_info['nombre']}"
        expand_btn = None
        config_frame = None
        for widget in col_container.winfo_children():
            if isinstance(widget, tk.Frame) and widget['bg'] == '#e9ecef':
                config_frame = widget
            else:
                for child in widget.winfo_children():
                    if isinstance(child, tk.Button) and hasattr(child, 'col_key'):
                        if child.col_key == col_key:
                            expand_btn = child
                            break
        if not config_frame or not expand_btn:
            return
        is_expanded = self.columna_config_expanded.get(col_key, False)
        if is_expanded:
            config_frame.pack_forget()
            expand_btn.config(text="▶")
            self.columna_config_expanded[col_key] = False
        else:
            if not config_frame.winfo_children():
                self._crear_panel_config_columna(config_frame, tabla, col_info)
            config_frame.pack(fill=tk.X, padx=20, pady=(0, 8))
            expand_btn.config(text="▼")
            self.columna_config_expanded[col_key] = True

    def _crear_panel_config_columna(self, parent, tabla, col_info):
        col_nombre = col_info['nombre']
        col_tipo = (col_info['udt_name'] or col_info['tipo_dato']).lower()
        col_key = f"{tabla}.{col_nombre}"
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
                    font=('Segoe UI', 8),
                    bg='white', fg=self.colors['danger']).pack(pady=10)
        btn_frame = tk.Frame(parent, bg='#e9ecef')
        btn_frame.pack(fill=tk.X, padx=10, pady=(5, 10))

        def guardar_config():
            if col_tipo in ('int2', 'smallint', 'int4', 'integer', 'int8', 'bigint'):
                config = {
                    'min': config_vars['min'].get(),
                    'max': config_vars['max'].get()
                }
            elif col_tipo in ('numeric', 'decimal'):
                config = {
                    'min': config_vars['min'].get(),
                    'max': config_vars['max'].get(),
                    'decimales': config_vars['decimales'].get()
                }
            elif col_tipo in ('varchar', 'character varying', 'bpchar', 'char', 'character', 'text'):
                config = {
                    'longitud': config_vars['longitud'].get(),
                    'usar_faker': config_vars.get('usar_faker', tk.BooleanVar(value=False)).get()
                }
            elif col_tipo in ('date', 'timestamp', 'timestamptz', 'timestamp with time zone'):
                config = {
                    'fecha_inicio': config_vars['fecha_inicio'].get(),
                    'fecha_fin': config_vars['fecha_fin'].get()
                }
            elif col_tipo == 'bool':
                config = {
                    'prob_true': config_vars['prob_true'].get()
                }
            else:
                config = {}
            self.columnas_personalizadas[col_key] = {
                'tipo': col_tipo,
                'config': config
            }
            self._refrescar_indicador_columna(tabla, col_nombre)
            self._toggle_config_columna(tabla, col_info, parent.master)
            self.log(f"[OK] Configuración guardada para {col_nombre}", "success")

        def eliminar_config():
            if col_key in self.columnas_personalizadas:
                del self.columnas_personalizadas[col_key]
                self._refrescar_indicador_columna(tabla, col_nombre)
                self.log(f"[OK] Configuración eliminada para {col_nombre}", "info")
            self._toggle_config_columna(tabla, col_info, parent.master)
        tk.Button(btn_frame, text="✓ Guardar",
                 command=guardar_config,
                 bg=self.colors['success'], fg='white',
                 font=('Segoe UI', 8, 'bold'),
                 relief=tk.FLAT, cursor='hand2',
                 padx=10, pady=4).pack(side=tk.LEFT, padx=(0, 5))
        tk.Button(btn_frame, text="✗ Eliminar",
                 command=eliminar_config,
                 bg=self.colors['danger'], fg='white',
                 font=('Segoe UI', 8, 'bold'),
                 relief=tk.FLAT, cursor='hand2',
                 padx=10, pady=4).pack(side=tk.LEFT)

    def _crear_controles_integer(self, parent, col_info, col_key, config_vars):
        config_actual = self.columnas_personalizadas.get(col_key, {}).get('config', {})
        rangos = self.generator.config.get('rangos_personalizados', {}).get('integer', {})
        min_default = config_actual.get('min', rangos.get('min', 1))
        max_default = config_actual.get('max', rangos.get('max', 1000000))
        min_frame = tk.Frame(parent, bg='white')
        min_frame.pack(fill=tk.X, pady=3, padx=5)
        tk.Label(min_frame, text="Min:",
                font=('Segoe UI', 8),
                bg='white').pack(side=tk.LEFT)
        config_vars['min'] = tk.IntVar(value=min_default)
        tk.Spinbox(min_frame, from_=-2147483648, to=2147483647,
                  textvariable=config_vars['min'],
                  width=12, font=('Segoe UI', 8)).pack(side=tk.RIGHT)
        max_frame = tk.Frame(parent, bg='white')
        max_frame.pack(fill=tk.X, pady=3, padx=5)
        tk.Label(max_frame, text="Max:",
                font=('Segoe UI', 8),
                bg='white').pack(side=tk.LEFT)
        config_vars['max'] = tk.IntVar(value=max_default)
        tk.Spinbox(max_frame, from_=-2147483648, to=2147483647,
                  textvariable=config_vars['max'],
                  width=12, font=('Segoe UI', 8)).pack(side=tk.RIGHT)

    def _crear_controles_numeric(self, parent, col_info, col_key, config_vars):
        config_actual = self.columnas_personalizadas.get(col_key, {}).get('config', {})
        min_default = config_actual.get('min', 0.0)
        max_default = config_actual.get('max', 10000.0)
        decimales_default = config_actual.get('decimales', 2)
        min_frame = tk.Frame(parent, bg='white')
        min_frame.pack(fill=tk.X, pady=3, padx=5)
        tk.Label(min_frame, text="Min:",
                font=('Segoe UI', 8),
                bg='white').pack(side=tk.LEFT)
        config_vars['min'] = tk.DoubleVar(value=min_default)
        tk.Spinbox(min_frame, from_=-999999999, to=999999999, increment=0.01,
                  textvariable=config_vars['min'],
                  width=12, font=('Segoe UI', 8)).pack(side=tk.RIGHT)
        max_frame = tk.Frame(parent, bg='white')
        max_frame.pack(fill=tk.X, pady=3, padx=5)
        tk.Label(max_frame, text="Max:",
                font=('Segoe UI', 8),
                bg='white').pack(side=tk.LEFT)
        config_vars['max'] = tk.DoubleVar(value=max_default)
        tk.Spinbox(max_frame, from_=-999999999, to=999999999, increment=0.01,
                  textvariable=config_vars['max'],
                  width=12, font=('Segoe UI', 8)).pack(side=tk.RIGHT)
        dec_frame = tk.Frame(parent, bg='white')
        dec_frame.pack(fill=tk.X, pady=3, padx=5)
        tk.Label(dec_frame, text="Decimales:",
                font=('Segoe UI', 8),
                bg='white').pack(side=tk.LEFT)
        config_vars['decimales'] = tk.IntVar(value=decimales_default)
        tk.Spinbox(dec_frame, from_=0, to=10,
                  textvariable=config_vars['decimales'],
                  width=12, font=('Segoe UI', 8)).pack(side=tk.RIGHT)

    def _crear_controles_text(self, parent, col_info, col_key, config_vars):
        config_actual = self.columnas_personalizadas.get(col_key, {}).get('config', {})
        texto_config = self.generator.config.get('texto', {})
        max_len = col_info.get('max_length') or texto_config.get('max_length_text', 50)
        longitud_default = config_actual.get('longitud', max_len)
        len_frame = tk.Frame(parent, bg='white')
        len_frame.pack(fill=tk.X, pady=3, padx=5)
        tk.Label(len_frame, text="Longitud:",
                font=('Segoe UI', 8),
                bg='white').pack(side=tk.LEFT)
        config_vars['longitud'] = tk.IntVar(value=longitud_default)
        tk.Spinbox(len_frame, from_=1, to=5000,
                  textvariable=config_vars['longitud'],
                  width=12, font=('Segoe UI', 8)).pack(side=tk.RIGHT)
        if self.generator and self.generator.faker:
            config_vars['usar_faker'] = tk.BooleanVar(value=config_actual.get('usar_faker', False))
            tk.Checkbutton(parent, text="Usar Faker (texto realista)",
                          variable=config_vars['usar_faker'],
                          bg='white',
                          font=('Segoe UI', 8)).pack(anchor=tk.W, pady=5, padx=5)

    def _crear_controles_date(self, parent, col_info, col_key, config_vars):
        config_actual = self.columnas_personalizadas.get(col_key, {}).get('config', {})
        fecha_inicio_default = config_actual.get('fecha_inicio', '2020-01-01')
        fecha_fin_default = config_actual.get('fecha_fin', '2025-12-31')
        inicio_frame = tk.Frame(parent, bg='white')
        inicio_frame.pack(fill=tk.X, pady=3, padx=5)
        tk.Label(inicio_frame, text="Desde:",
                font=('Segoe UI', 8),
                bg='white').pack(side=tk.LEFT)
        config_vars['fecha_inicio'] = tk.StringVar(value=fecha_inicio_default)
        tk.Entry(inicio_frame, textvariable=config_vars['fecha_inicio'],
                width=12, font=('Segoe UI', 8)).pack(side=tk.RIGHT)
        fin_frame = tk.Frame(parent, bg='white')
        fin_frame.pack(fill=tk.X, pady=3, padx=5)
        tk.Label(fin_frame, text="Hasta:",
                font=('Segoe UI', 8),
                bg='white').pack(side=tk.LEFT)
        config_vars['fecha_fin'] = tk.StringVar(value=fecha_fin_default)
        tk.Entry(fin_frame, textvariable=config_vars['fecha_fin'],
                width=12, font=('Segoe UI', 8)).pack(side=tk.RIGHT)

    def _crear_controles_boolean(self, parent, col_info, col_key, config_vars):
        config_actual = self.columnas_personalizadas.get(col_key, {}).get('config', {})
        prob_true_default = config_actual.get('prob_true', 0.5)
        prob_frame = tk.Frame(parent, bg='white')
        prob_frame.pack(fill=tk.X, pady=3, padx=5)
        tk.Label(prob_frame, text="Prob. True:",
                font=('Segoe UI', 8),
                bg='white').pack(side=tk.LEFT)
        config_vars['prob_true'] = tk.DoubleVar(value=prob_true_default)
        tk.Spinbox(prob_frame, from_=0.0, to=1.0, increment=0.05,
                  textvariable=config_vars['prob_true'],
                  width=12, font=('Segoe UI', 8)).pack(side=tk.RIGHT)
        tk.Label(parent, text="(ej: 0.8 = 80% True)",
                font=('Segoe UI', 7, 'italic'),
                bg='white', fg='#6c757d').pack(anchor=tk.W, pady=3, padx=5)

    def _refrescar_indicador_columna(self, tabla, col_nombre):
        if tabla not in self.tabla_vars:
            return
        _, _, _, columnas_frame = self.tabla_vars[tabla]
        if self.tabla_expanded[tabla].get():
            for widget in columnas_frame.winfo_children():
                widget.destroy()
            self._crear_lista_columnas(tabla, columnas_frame)

    def seleccionar_todas(self):
        for var_check, var_cantidad, _, _ in self.tabla_vars.values():
            var_check.set(True)

    def deseleccionar_todas(self):
        for var_check, var_cantidad, _, _ in self.tabla_vars.values():
            var_check.set(False)

    def ejecutar_generacion(self):
        if self.proceso_activo:
            messagebox.showwarning("Advertencia", "Ya hay un proceso en ejecución")
            return
        tablas_seleccionadas = []
        for tabla, (var_check, var_cantidad, _, _) in self.tabla_vars.items():
            if var_check.get():
                cantidad = var_cantidad.get()
                tablas_seleccionadas.append((tabla, cantidad))
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
        thread = threading.Thread(
            target=self._generar_datos_thread,
            args=(tablas_seleccionadas,),
            daemon=True
        )
        thread.start()

    def _aplicar_config_desde_ui(self):
        self.generator.config['columnas_personalizadas'] = self.columnas_personalizadas.copy()

    def _generar_datos_thread(self, tablas_seleccionadas):
        try:
            import sys

            class GUIOutput:

                def __init__(self, gui):
                    self.gui = gui

                def write(self, text):
                    if text.strip():
                        t = text.strip()
                        if '[OK]' in t:
                            self.gui.root.after(0, lambda txt=t: self.gui.log(txt, "success"))
                        elif '[WARN]' in t:
                            self.gui.root.after(0, lambda txt=t: self.gui.log(txt, "warning"))
                        elif '[ERROR]' in t:
                            self.gui.root.after(0, lambda txt=t: self.gui.log(txt, "error"))
                        else:
                            self.gui.root.after(0, lambda txt=t: self.gui.log(txt, "info"))

                def flush(self):
                    pass
            old_stdout = sys.stdout
            sys.stdout = GUIOutput(self)
            self.log("="*60, "info")
            self.log("INICIANDO GENERACIÓN DE DATOS", "info")
            self.log("="*60 + "\n", "info")
            orden_carga = self.generator.metadata['orden_carga']
            tablas_dict = {tabla: cantidad for tabla, cantidad in tablas_seleccionadas}
            tablas_ordenadas = [(t, tablas_dict[t]) for t in orden_carga if t in tablas_dict]
            self.log(f"Orden de carga (respetando FK): {[t for t, _ in tablas_ordenadas]}\n", "info")
            if self.limpiar_var.get():
                self.log("Limpiando SOLO tablas seleccionadas (no todas del esquema)...\n", "warning")
                for tabla, _ in reversed(tablas_ordenadas):
                    try:
                        tabla_completa = f"{self.esquema}.{tabla}"
                        self.generator.cursor.execute(f'TRUNCATE TABLE {tabla_completa} CASCADE')
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
                    registros = self.generator.generar_registros_tabla(tabla, cantidad)
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
                f"Generación completada exitosamente\n\n"
                f"Total de registros: {total_insertados:,}"
            ))
        except Exception as e:
            self.log(f"\n[ERROR] {str(e)}", "error")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Error durante la generación: {e}"))
        finally:
            import sys
            if 'old_stdout' in locals():
                sys.stdout = old_stdout
            self.root.after(0, lambda: self.btn_ejecutar.config(state=tk.NORMAL, text="GENERAR DATOS"))
            self.proceso_activo = False

def main():
    if len(sys.argv) < 7:
        print("Error: Faltan parámetros")
        print("Uso: python data_prueba_gui.py <host> <puerto> <bd> <usuario> <password> <esquema>")
        sys.exit(1)
    host = sys.argv[1]
    puerto = sys.argv[2]
    bd = sys.argv[3]
    usuario = sys.argv[4]
    password = sys.argv[5]
    esquema = sys.argv[6]
    root = tk.Tk()
    app = DataPruebaGUI(root, host, puerto, bd, usuario, password, esquema)
    root.mainloop()
if __name__ == "__main__":
    main()
