import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sys
import os
import threading
from pathlib import Path

# Importar el generador principal
sys.path.insert(0, str(Path(__file__).parent))
from data_prueba import SmartDataGenerator


class DataPruebaGUI:
    """
    Interfaz gráfica para el generador inteligente de datos de prueba.

    Diferencias de comportamiento vs CLI (data_prueba.py):
    - LIMPIEZA: GUI limpia SOLO las tablas seleccionadas (no todas del esquema)
    - CANTIDADES: GUI usa spinbox personalizables (respeta cantidad_base y multiplicadores FK)
    - SELECCIÓN: GUI permite elegir tablas específicas (CLI procesa todas)
    - CONFIG: GUI permite editar parámetros en tiempo real antes de generar

    La lógica de generación de datos es idéntica, solo difiere la selección y limpieza.
    """
    def __init__(self, root, host, puerto, bd, usuario, password, esquema):
        self.root = root
        self.root.title("Generación de Data")
        self.root.geometry("1000x700")
        self.root.minsize(1000, 700)

        # Parámetros de conexión
        self.host = host
        self.puerto = puerto
        self.bd = bd
        self.usuario = usuario
        self.password = password
        self.esquema = esquema

        # Variables
        self.generator = None
        self.tabla_vars = {}  # {tabla: (BooleanVar, IntVar)}
        self.proceso_activo = False
        self.cantidad_base_default = 100  # Se sincronizará con config
        # Configuración editable desde UI (aplica a columnas sin patrón)
        self.int_min_var = tk.IntVar(value=1)
        self.int_max_var = tk.IntVar(value=2147483647)
        self.small_min_var = tk.IntVar(value=1)
        self.small_max_var = tk.IntVar(value=32767)
        self.big_min_var = tk.IntVar(value=1)
        self.big_max_var = tk.IntVar(value=9223372036854775807)
        self.text_len_var = tk.IntVar(value=50)
        self.null_prob_var = tk.DoubleVar(value=0.2)
        # Variables para multiplicadores FK
        self.fk_multiplicador_habilitado_var = tk.BooleanVar(value=True)
        self.fk_multiplicador_factor_var = tk.DoubleVar(value=1.0)

        # Colores
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
        """Configura la interfaz de usuario"""
        self.root.configure(bg=self.colors['bg_light'])

        # Header
        header = tk.Frame(self.root, bg=self.colors['primary'], height=80)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(header, text="Generación de data",
                font=('Segoe UI', 18, 'bold'),
                bg=self.colors['primary'], fg='white').pack(pady=10)

        info_text = f"Base de Datos: {self.bd} | Esquema: {self.esquema}"
        tk.Label(header, text=info_text,
                font=('Segoe UI', 10),
                bg=self.colors['primary'], fg=self.colors['bg_light']).pack()

        # Contenedor principal
        main_container = tk.Frame(self.root, bg=self.colors['bg_light'])
        main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Panel izquierdo: Configuración
        left_panel = tk.Frame(main_container, bg=self.colors['bg_card'], relief=tk.RAISED, bd=2)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        # Título del panel
        tk.Label(left_panel, text="Seleccionar Tablas a Poblar",
                font=('Segoe UI', 12, 'bold'),
                bg=self.colors['bg_card'], fg=self.colors['primary']).pack(pady=10)

        # Botones de selección masiva
        button_frame = tk.Frame(left_panel, bg=self.colors['bg_card'])
        button_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(button_frame, text="Seleccionar Todas",
                 command=self.seleccionar_todas,
                 bg=self.colors['success'], fg='white',
                 font=('Segoe UI', 9), relief=tk.FLAT, cursor='hand2').pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="Deseleccionar Todas",
                 command=self.deseleccionar_todas,
                 bg=self.colors['danger'], fg='white',
                 font=('Segoe UI', 9), relief=tk.FLAT, cursor='hand2').pack(side=tk.LEFT, padx=5)

        # Separador
        ttk.Separator(left_panel, orient='horizontal').pack(fill=tk.X, padx=10, pady=5)

        # Lista de tablas con scroll
        self.tabla_frame_container = tk.Frame(left_panel, bg=self.colors['bg_card'])
        self.tabla_frame_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

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

        # Habilitar scroll con rueda del ratón
        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)

        # Panel inferior: Botones de acción
        action_panel = tk.Frame(left_panel, bg=self.colors['bg_card'])
        action_panel.pack(fill=tk.X, padx=10, pady=10)

        ttk.Separator(action_panel, orient='horizontal').pack(fill=tk.X, pady=(0, 10))

        # Frame para limpieza
        cleanup_frame = tk.Frame(action_panel, bg=self.colors['bg_card'])
        cleanup_frame.pack(fill=tk.X, pady=5)

        self.limpiar_var = tk.BooleanVar(value=False)
        tk.Checkbutton(cleanup_frame, text="Limpiar tablas antes de insertar",
                      variable=self.limpiar_var,
                      bg=self.colors['bg_card'],
                      font=('Segoe UI', 9, 'bold'),
                      fg=self.colors['danger']).pack(anchor=tk.W)

        # Frame contenedor con scroll para configuraciones
        config_scroll_container = tk.Frame(action_panel, bg=self.colors['bg_card'])
        config_scroll_container.pack(fill=tk.BOTH, expand=True, pady=5)

        # Canvas y scrollbar para configuraciones
        config_canvas = tk.Canvas(config_scroll_container, bg=self.colors['bg_card'],
                                 highlightthickness=0, height=200)
        config_scrollbar = ttk.Scrollbar(config_scroll_container, orient="vertical",
                                        command=config_canvas.yview)
        config_inner_frame = tk.Frame(config_canvas, bg=self.colors['bg_card'])

        config_canvas.configure(yscrollcommand=config_scrollbar.set)
        config_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        config_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        config_canvas_window = config_canvas.create_window((0, 0), window=config_inner_frame, anchor="nw")

        def configure_config_scroll(event):
            config_canvas.configure(scrollregion=config_canvas.bbox("all"))
            config_canvas.itemconfig(config_canvas_window, width=event.width)

        config_inner_frame.bind("<Configure>", configure_config_scroll)
        config_canvas.bind("<Configure>", configure_config_scroll)

        # Habilitar scroll con rueda del ratón en configuraciones
        def on_config_mousewheel(event):
            config_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        config_canvas.bind_all("<MouseWheel>", on_config_mousewheel)

        # Configuración de generación por defecto (para columnas sin patrón detectado)
        config_frame = tk.LabelFrame(config_inner_frame,
                                     text="Config. por defecto (sin patrón)",
                                     bg=self.colors['bg_card'],
                                     fg=self.colors['primary'],
                                     font=('Segoe UI', 9, 'bold'))
        config_frame.pack(fill=tk.X, padx=2, pady=(0, 5))

        def add_cfg_row(parent, label, var, from_, to, step=1):
            row = tk.Frame(parent, bg=self.colors['bg_card'])
            row.pack(fill=tk.X, padx=4, pady=1)
            tk.Label(row, text=label, bg=self.colors['bg_card'],
                     fg=self.colors['text_dark'], font=('Segoe UI', 8)).pack(side=tk.LEFT)
            tk.Spinbox(row, from_=from_, to=to, increment=step, textvariable=var,
                       width=12, font=('Segoe UI', 8)).pack(side=tk.RIGHT)

        add_cfg_row(config_frame, "INTEGER min", self.int_min_var, -2147483648, 2147483647)
        add_cfg_row(config_frame, "INTEGER max", self.int_max_var, -2147483648, 2147483647)
        add_cfg_row(config_frame, "SMALLINT min", self.small_min_var, -32768, 32767)
        add_cfg_row(config_frame, "SMALLINT max", self.small_max_var, -32768, 32767)
        add_cfg_row(config_frame, "BIGINT min", self.big_min_var, -9223372036854775808, 9223372036854775807, step=1000)
        add_cfg_row(config_frame, "BIGINT max", self.big_max_var, -9223372036854775808, 9223372036854775807, step=1000)
        add_cfg_row(config_frame, "Long. texto fallback", self.text_len_var, 1, 5000, step=5)
        add_cfg_row(config_frame, "Prob. NULL (0-1)", self.null_prob_var, 0.0, 1.0, step=0.05)

        # Configuración de multiplicadores FK
        fk_frame = tk.LabelFrame(config_inner_frame,
                                 text="Multiplicadores FK (relaciones 1:N)",
                                 bg=self.colors['bg_card'],
                                 fg=self.colors['primary'],
                                 font=('Segoe UI', 9, 'bold'))
        fk_frame.pack(fill=tk.X, padx=2, pady=(0, 5))

        fk_check_row = tk.Frame(fk_frame, bg=self.colors['bg_card'])
        fk_check_row.pack(fill=tk.X, padx=4, pady=2)
        tk.Checkbutton(fk_check_row, text="Habilitar multiplicadores FK",
                      variable=self.fk_multiplicador_habilitado_var,
                      bg=self.colors['bg_card'],
                      font=('Segoe UI', 8)).pack(anchor=tk.W)

        add_cfg_row(fk_frame, "Factor multiplicador", self.fk_multiplicador_factor_var, 0.1, 10.0, step=0.1)

        # Botón principal
        self.btn_ejecutar = tk.Button(action_panel, text="GENERAR DATOS",
                                      command=self.ejecutar_generacion,
                                      bg=self.colors['success'], fg='white',
                                      font=('Segoe UI', 11, 'bold'),
                                      relief=tk.FLAT, cursor='hand2',
                                      height=2)
        self.btn_ejecutar.pack(fill=tk.X, pady=5)

        # Panel derecho: Consola
        right_panel = tk.Frame(main_container, bg=self.colors['bg_card'], relief=tk.RAISED, bd=2)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Header de consola con título y botón limpiar
        console_header = tk.Frame(right_panel, bg=self.colors['bg_card'])
        console_header.pack(fill=tk.X, pady=10, padx=10)

        tk.Label(console_header, text="Progreso de Generación",
                font=('Segoe UI', 12, 'bold'),
                bg=self.colors['bg_card'], fg=self.colors['primary']).pack(side=tk.LEFT)

        tk.Button(console_header, text="Limpiar Log",
                 command=self.limpiar_console,
                 bg=self.colors['warning'], fg='white',
                 font=('Segoe UI', 8, 'bold'),
                 relief=tk.FLAT, cursor='hand2',
                 padx=10, pady=3).pack(side=tk.RIGHT)

        # Consola (tamaño reducido)
        console_frame = tk.Frame(right_panel, bg='#1e1e1e', relief=tk.SOLID, bd=1)
        console_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        self.console = scrolledtext.ScrolledText(console_frame,
                                                 font=("Cascadia Code", 8),
                                                 bg="#1e1e1e", fg="#d4d4d4",
                                                 wrap=tk.WORD, relief=tk.FLAT,
                                                 padx=8, pady=8,
                                                 height=20)
        self.console.pack(fill=tk.BOTH, expand=True)

        # Tags para colores
        self.console.tag_config("info", foreground="#4fc1ff")
        self.console.tag_config("success", foreground="#73c991")
        self.console.tag_config("warning", foreground="#cca700")
        self.console.tag_config("error", foreground="#f48771")

    def log(self, mensaje, tag="info"):
        """Escribe mensaje en la consola"""
        self.console.insert(tk.END, mensaje + "\n", tag)
        self.console.see(tk.END)
        self.console.update()

    def limpiar_console(self):
        """Limpia el contenido de la consola"""
        self.console.delete('1.0', tk.END)
        self.log("="*60, "info")
        self.log("LOG LIMPIADO", "info")
        self.log("="*60 + "\n", "info")

    def inicializar_generador(self):
        """Inicializa el generador y analiza la base de datos"""
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
            # Sincronizar controles con la config cargada
            self._sincronizar_config_ui()
            # Obtener cantidad_base del config
            self.cantidad_base_default = self.generator.config.get('cantidad_base', 100)
            self.log(f"[OK] Cantidad base configurada: {self.cantidad_base_default} registros", "success")
            self.log("\nAnalizando estructura de la base de datos...", "info")

            # Analizar en hilo separado
            thread = threading.Thread(target=self._analizar_bd_thread, daemon=True)
            thread.start()

        except Exception as e:
            self.log(f"[ERROR] {str(e)}", "error")
            messagebox.showerror("Error", f"Error al inicializar: {e}")
            self.root.destroy()

    def _analizar_bd_thread(self):
        """Analiza la BD en un hilo separado"""
        try:
            import sys

            # Crear un wrapper para redirigir stdout a la consola GUI
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

            # Reemplazar stdout temporalmente
            old_stdout = sys.stdout
            sys.stdout = GUIOutput(self)

            try:
                self.generator.analizar_base_datos()
            finally:
                sys.stdout = old_stdout

            # Crear controles de tablas
            self.root.after(0, self.crear_controles_tablas)

        except Exception as e:
            self.root.after(0, lambda: self.log(f"[ERROR] {str(e)}", "error"))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Error en análisis: {e}"))

    def crear_controles_tablas(self):
        """Crea los controles para cada tabla"""
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
        """Crea un control para una tabla específica"""
        # Frame contenedor
        frame = tk.Frame(self.tabla_frame, bg='white', relief=tk.SOLID, bd=1)
        frame.pack(fill=tk.X, pady=3, padx=5)

        # Frame interno
        inner = tk.Frame(frame, bg='white')
        inner.pack(fill=tk.X, padx=8, pady=8)

        # Checkbox
        var_check = tk.BooleanVar(value=True)
        check = tk.Checkbutton(inner, variable=var_check, bg='white')
        check.pack(side=tk.LEFT)

        # Número y nombre de tabla
        nombre_frame = tk.Frame(inner, bg='white')
        nombre_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        tk.Label(nombre_frame, text=f"{numero}.",
                font=('Segoe UI', 9),
                bg='white', fg='#7f8c8d').pack(side=tk.LEFT)

        tk.Label(nombre_frame, text=tabla,
                font=('Segoe UI', 10, 'bold'),
                bg='white', fg=self.colors['primary']).pack(side=tk.LEFT, padx=5)

        # Mostrar info adicional
        info_text = self._get_tabla_info(tabla)
        if info_text:
            tk.Label(nombre_frame, text=info_text,
                    font=('Segoe UI', 8),
                    bg='white', fg='#95a5a6').pack(side=tk.LEFT, padx=5)

        # Spinbox para cantidad
        cantidad_frame = tk.Frame(inner, bg='white')
        cantidad_frame.pack(side=tk.RIGHT)

        tk.Label(cantidad_frame, text="Registros:",
                font=('Segoe UI', 9),
                bg='white').pack(side=tk.LEFT, padx=(0, 5))

        # Usar cantidad_base del config, con cálculo de multiplicador FK si aplica
        cantidad_inicial = self._calcular_cantidad_inicial(tabla)
        var_cantidad = tk.IntVar(value=cantidad_inicial)
        spinbox = tk.Spinbox(cantidad_frame, from_=1, to=100000,
                            textvariable=var_cantidad,
                            width=8, font=('Segoe UI', 9))
        spinbox.pack(side=tk.LEFT)

        # Guardar referencias
        self.tabla_vars[tabla] = (var_check, var_cantidad)

    def _calcular_cantidad_inicial(self, tabla):
        """Calcula la cantidad inicial de registros para una tabla"""
        # Prioridad 1: cantidad_por_tabla en config
        cantidad_config = self.generator.config.get('cantidad_por_tabla', {}).get(tabla)
        if cantidad_config is not None:
            return cantidad_config

        # Prioridad 2: aplicar multiplicador FK si está habilitado
        if (self.fk_multiplicador_habilitado_var.get() and
            tabla in self.generator.metadata['fks'] and
            self.generator.metadata['fks'][tabla]):
            num_fks = len(self.generator.metadata['fks'][tabla])
            factor = self.fk_multiplicador_factor_var.get()
            return int(self.cantidad_base_default * num_fks * factor)

        # Prioridad 3: cantidad_base
        return self.cantidad_base_default

    def _get_tabla_info(self, tabla):
        """Obtiene información adicional de la tabla"""
        info_parts = []

        # Contar FKs
        if tabla in self.generator.metadata['fks']:
            num_fks = len(self.generator.metadata['fks'][tabla])
            if num_fks > 0:
                info_parts.append(f"FK: {num_fks}")

        return " | ".join(info_parts) if info_parts else ""

    def seleccionar_todas(self):
        """Selecciona todas las tablas"""
        for var_check, var_cantidad in self.tabla_vars.values():
            var_check.set(True)

    def deseleccionar_todas(self):
        """Deselecciona todas las tablas"""
        for var_check, var_cantidad in self.tabla_vars.values():
            var_check.set(False)

    def ejecutar_generacion(self):
        """Ejecuta la generación de datos"""
        if self.proceso_activo:
            messagebox.showwarning("Advertencia", "Ya hay un proceso en ejecución")
            return

        # Obtener tablas seleccionadas
        tablas_seleccionadas = []
        for tabla, (var_check, var_cantidad) in self.tabla_vars.items():
            if var_check.get():
                cantidad = var_cantidad.get()
                tablas_seleccionadas.append((tabla, cantidad))

        # Actualizar configuración del generador con lo definido en la UI
        self._aplicar_config_desde_ui()

        if not tablas_seleccionadas:
            messagebox.showwarning("Advertencia", "Debes seleccionar al menos una tabla")
            return

        # Confirmar
        mensaje = f"¿Generar datos para {len(tablas_seleccionadas)} tabla(s)?"
        if self.limpiar_var.get():
            mensaje += "\n\n[ADVERTENCIA] Se limpiaran las tablas antes de insertar"

        if not messagebox.askyesno("Confirmar", mensaje):
            return

        # Deshabilitar botón
        self.btn_ejecutar.config(state=tk.DISABLED, text="GENERANDO...")
        self.proceso_activo = True

        # Limpiar consola
        self.console.delete('1.0', tk.END)

        # Ejecutar en hilo separado
        thread = threading.Thread(
            target=self._generar_datos_thread,
            args=(tablas_seleccionadas,),
            daemon=True
        )
        thread.start()

    def _sincronizar_config_ui(self):
        """Carga los valores actuales de config en los controles de la UI"""
        cfg = self.generator.config
        rangos = cfg.get('rangos_personalizados', {})
        texto = cfg.get('texto', {})
        nulls = cfg.get('generacion_nulls', {})
        fk_mult = cfg.get('multiplicadores_fk', {})

        self.int_min_var.set(rangos.get('integer', {}).get('min', self.int_min_var.get()))
        self.int_max_var.set(rangos.get('integer', {}).get('max', self.int_max_var.get()))
        self.small_min_var.set(rangos.get('smallint', {}).get('min', self.small_min_var.get()))
        self.small_max_var.set(rangos.get('smallint', {}).get('max', self.small_max_var.get()))
        self.big_min_var.set(rangos.get('bigint', {}).get('min', self.big_min_var.get()))
        self.big_max_var.set(rangos.get('bigint', {}).get('max', self.big_max_var.get()))
        self.text_len_var.set(texto.get('max_length_text', self.text_len_var.get()))
        self.null_prob_var.set(nulls.get('probabilidad', self.null_prob_var.get()))

        # Sincronizar multiplicadores FK
        self.fk_multiplicador_habilitado_var.set(fk_mult.get('habilitado', True))
        self.fk_multiplicador_factor_var.set(fk_mult.get('factor', 1.0))

    def _aplicar_config_desde_ui(self):
        """Aplica a self.generator.config los valores editados en la UI"""
        cfg = self.generator.config
        cfg.setdefault('rangos_personalizados', {})
        cfg['rangos_personalizados']['integer'] = {
            'min': self.int_min_var.get(),
            'max': self.int_max_var.get()
        }
        cfg['rangos_personalizados']['smallint'] = {
            'min': self.small_min_var.get(),
            'max': self.small_max_var.get()
        }
        cfg['rangos_personalizados']['bigint'] = {
            'min': self.big_min_var.get(),
            'max': self.big_max_var.get()
        }
        cfg.setdefault('texto', {})
        cfg['texto']['max_length_text'] = self.text_len_var.get()
        cfg.setdefault('generacion_nulls', {})
        cfg['generacion_nulls']['probabilidad'] = float(self.null_prob_var.get())

        # Aplicar multiplicadores FK
        cfg.setdefault('multiplicadores_fk', {})
        cfg['multiplicadores_fk']['habilitado'] = self.fk_multiplicador_habilitado_var.get()
        cfg['multiplicadores_fk']['factor'] = float(self.fk_multiplicador_factor_var.get())

    def _generar_datos_thread(self, tablas_seleccionadas):
        """Genera datos en un hilo separado"""
        try:
            import sys

            # Redirigir stdout para capturar mensajes del generador
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

            # Ordenar tablas según orden de carga (dependencias FK)
            orden_carga = self.generator.metadata['orden_carga']
            tablas_dict = {tabla: cantidad for tabla, cantidad in tablas_seleccionadas}
            tablas_ordenadas = [(t, tablas_dict[t]) for t in orden_carga if t in tablas_dict]

            self.log(f"Orden de carga (respetando FK): {[t for t, _ in tablas_ordenadas]}\n", "info")

            # Limpiar si está activado
            # NOTA: El GUI limpia SOLO las tablas seleccionadas (diferente a CLI que limpia todas)
            if self.limpiar_var.get():
                self.log("Limpiando SOLO tablas seleccionadas (no todas del esquema)...\n", "warning")
                # Limpiar en orden inverso (respetando dependencias FK)
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

            # Generar datos para cada tabla
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

            # Resumen final
            self.log("\n" + "="*60, "info")
            self.log("GENERACIÓN COMPLETADA", "success")
            self.log("="*60 + "\n", "info")
            self.log(f"Total de registros insertados: {total_insertados:,}", "success")

            # Mostrar mensaje
            self.root.after(0, lambda: messagebox.showinfo(
                "Completado",
                f"Generación completada exitosamente\n\n"
                f"Total de registros: {total_insertados:,}"
            ))

        except Exception as e:
            self.log(f"\n[ERROR] {str(e)}", "error")
            self.root.after(0, lambda: messagebox.showerror("Error", f"Error durante la generación: {e}"))

        finally:
            # Restaurar stdout
            import sys
            if 'old_stdout' in locals():
                sys.stdout = old_stdout

            # Rehabilitar botón
            self.root.after(0, lambda: self.btn_ejecutar.config(state=tk.NORMAL, text="GENERAR DATOS"))
            self.proceso_activo = False


def main():
    """Función principal"""
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
