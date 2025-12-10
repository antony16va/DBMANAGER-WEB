import sys
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import psycopg2
from typing import Dict, List, Tuple

class ComentariosGUI:

    def __init__(self, host: str, port: str, database: str, user: str, password: str, schema: str):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.schema = schema
        self.conn = None
        self.cursor = None

        # Para tablas
        self.tablas_nombres = []
        self.tablas_con_comentarios = []  # Lista de (nombre_tabla, comentario_actual)
        self.tabla_actual = None
        self.campos_actuales = []

        # Para otros objetos
        self.objetos_nombres = {}  # {tipo: [lista de nombres]}
        self.tipo_objeto_actual = None
        self.objetos_actuales = []  # Lista de (nombre, comentario_actual)

        self.widgets_comentarios = {}  # {identificador: Text widget}
        self.modo_actual = "tablas"  # "tablas" o "objetos"

        self.root = tk.Tk()
        self.root.title(f"Agregar Comentarios - {schema} @ {database}")
        self.root.geometry("1400x750")

        self.conectar_bd()
        self.crear_interfaz()
        self.cargar_lista_tablas()
        self.cargar_comentarios_tablas()  # Cargar comentarios de tablas al inicio



    def conectar_bd(self):

        """Conecta a la base de datos PostgreSQL"""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self.conn.autocommit = True
            self.cursor = self.conn.cursor()
            print(f"Conexión exitosa a {self.database}")
        except Exception as e:
            messagebox.showerror("Error de Conexión", f"No se pudo conectar a la base de datos:\n{e}")
            sys.exit(1)

    def crear_interfaz(self):
        """Crea la interfaz gráfica principal"""
        # Frame superior con información
        info_frame = ttk.Frame(self.root, padding="10")
        info_frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(info_frame, text=f"Base de datos: {self.database}", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        ttk.Label(info_frame, text=f"Esquema: {self.schema}", font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)

        # Frame para selección de modo (Tablas u Otros Objetos)
        modo_frame = ttk.Frame(self.root, padding="10")
        modo_frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(modo_frame, text="Modo:", font=('Arial', 11, 'bold')).pack(side=tk.LEFT, padx=5)

        self.modo_var = tk.StringVar(value="tablas")
        ttk.Radiobutton(modo_frame, text="Tablas", variable=self.modo_var,
                       value="tablas", command=self.cambiar_modo).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(modo_frame, text="Otros Objetos",
                       variable=self.modo_var, value="objetos", command=self.cambiar_modo).pack(side=tk.LEFT, padx=10)

        # Frame para selección de tipo de objeto (solo visible en modo objetos)
        self.tipo_objeto_frame = ttk.Frame(self.root, padding="10")
        self.tipo_objeto_frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(self.tipo_objeto_frame, text="Tipo de Objeto:", font=('Arial', 11, 'bold')).pack(side=tk.LEFT, padx=5)

        self.tipo_objeto_var = tk.StringVar()
        self.combo_tipo_objeto = ttk.Combobox(self.tipo_objeto_frame, textvariable=self.tipo_objeto_var,
                                              state='readonly', width=30, font=('Arial', 10),
                                              values=["Procedimientos", "Funciones", "Vistas", "Triggers", "Funciones Trigger","Types", "Foreign Servers","Tablas foraneas","Sinonimos","Indices","Constraints","Jobs"])
        self.combo_tipo_objeto.pack(side=tk.LEFT, padx=5)
        self.combo_tipo_objeto.bind('<<ComboboxSelected>>', self.on_tipo_objeto_seleccionado)

        # Ocultar inicialmente el frame de tipo de objeto
        self.tipo_objeto_frame.pack_forget()

        # Frame para selección de tabla (solo visible en modo tablas)
        self.selector_frame = ttk.Frame(self.root, padding="10")
        self.selector_frame.pack(side=tk.TOP, fill=tk.X)

        self.selector_label = ttk.Label(self.selector_frame, text="Seleccionar Tabla:", font=('Arial', 11, 'bold'))
        self.selector_label.pack(side=tk.LEFT, padx=5)

        self.item_var = tk.StringVar()
        self.combo_items = ttk.Combobox(self.selector_frame, textvariable=self.item_var,
                                         state='readonly', width=40, font=('Arial', 10))
        self.combo_items.pack(side=tk.LEFT, padx=5)
        self.combo_items.bind('<<ComboboxSelected>>', self.on_item_seleccionado)

        ttk.Label(self.selector_frame, text="", width=10).pack(side=tk.LEFT)  # Espaciador

        # Frame para botones de acción
        btn_frame = ttk.Frame(self.root, padding="10")
        btn_frame.pack(side=tk.TOP, fill=tk.X)

        self.btn_guardar = ttk.Button(btn_frame, text="💾 Guardar Comentarios",
                                       command=self.guardar_comentarios)
        self.btn_guardar.pack(side=tk.LEFT, padx=5)

        self.btn_recargar = ttk.Button(btn_frame, text="🔄 Recargar",
                                        command=self.recargar_actual)
        self.btn_recargar.pack(side=tk.LEFT, padx=5)

        ttk.Button(btn_frame, text="Cerrar", command=self.cerrar).pack(side=tk.RIGHT, padx=5)

        # Frame principal para los campos (con scroll)
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Crear canvas y scrollbar
        self.canvas = tk.Canvas(self.main_frame, bg='white')
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Habilitar scroll con rueda del mouse
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Mensaje inicial
        self.crear_mensaje_inicial()

    def cambiar_modo(self):
        """Cambia entre modo tablas y modo objetos"""
        self.modo_actual = self.modo_var.get()

        if self.modo_actual == "tablas":
            # Ocultar frame de tipo de objeto
            self.tipo_objeto_frame.pack_forget()
            # Mostrar frame de selector de tabla
            self.selector_frame.pack(side=tk.TOP, fill=tk.X, before=self.main_frame)
            # Cargar tablas en el combobox
            self.combo_items['values'] = self.tablas_nombres
            self.item_var.set('')
            # Limpiar y mostrar comentarios de tablas
            self.limpiar_frame_campos()
            self.mostrar_comentarios_tablas()
        else:
            # Mostrar frame de tipo de objeto
            self.tipo_objeto_frame.pack(side=tk.TOP, fill=tk.X, before=self.selector_frame)
            # Ocultar frame de selector de tabla
            self.selector_frame.pack_forget()
            # Limpiar selección
            self.tipo_objeto_var.set('')
            # Limpiar el contenido actual
            self.limpiar_frame_campos()
            self.crear_mensaje_inicial()

    def on_tipo_objeto_seleccionado(self, event):
        """Cuando se selecciona un tipo de objeto"""
        tipo = self.tipo_objeto_var.get()
        self.tipo_objeto_actual = tipo

        # Cargar y mostrar todos los objetos del tipo seleccionado
        self.cargar_todos_objetos_tipo(tipo)

    def on_item_seleccionado(self, event):
        """Cuando se selecciona un item (solo para tablas)"""
        if self.modo_actual == "tablas":
            tabla = self.item_var.get()
            if tabla:
                self.cargar_campos_tabla(tabla)

    def crear_mensaje_inicial(self):
        """Crea un mensaje inicial pidiendo seleccionar una tabla"""
        if self.modo_actual == "tablas":
            texto = "Seleccione un objeto del menú"
        else:
            texto = "Seleccione un tipo de objeto para mostrar todos los objetos de ese tipo"

        mensaje_label = ttk.Label(self.scrollable_frame,
                                  text=texto,
                                  font=('Arial', 12),
                                  foreground='gray')
        mensaje_label.pack(pady=50)

    def cargar_lista_tablas(self):
        """Carga la lista de tablas en el combobox"""
        try:
            sql = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
            self.cursor.execute(sql, (self.schema,))
            self.tablas_nombres = [row[0] for row in self.cursor.fetchall()]

            if not self.tablas_nombres:
                messagebox.showwarning("Sin Tablas", f"No se encontraron tablas en el esquema '{self.schema}'")
                self.cerrar()
                return

            print(f"Se encontraron {len(self.tablas_nombres)} tablas")

            # Configurar el combobox con las tablas
            self.combo_items['values'] = self.tablas_nombres

        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar tablas:\n{e}")
            self.cerrar()

    def cargar_comentarios_tablas(self):
        """Carga los comentarios de todas las tablas"""
        try:
            sql = """
            SELECT
                c.relname AS tabla,
                obj_description(c.oid) AS comentario
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE c.relkind = 'r'
              AND n.nspname = %s
            ORDER BY tabla
            """
            self.cursor.execute(sql, (self.schema,))
            self.tablas_con_comentarios = [(row[0], row[1] or '') for row in self.cursor.fetchall()]
            print(f"Se cargaron comentarios de {len(self.tablas_con_comentarios)} tablas")
        except Exception as e:
            print(f"Error al cargar comentarios de tablas: {e}")
            self.tablas_con_comentarios = []

    def mostrar_comentarios_tablas(self):
        """Muestra los comentarios de las tablas en la interfaz"""
        if not self.tablas_con_comentarios:
            self.crear_mensaje_inicial()
            return

        # Header con información
        header_frame = ttk.Frame(self.scrollable_frame)
        header_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(header_frame, text="Comentarios de Tablas",
                 font=('Arial', 14, 'bold'),
                 foreground='#2c3e50').pack(side=tk.LEFT)

        ttk.Label(header_frame, text=f"({len(self.tablas_con_comentarios)} tablas)",
                 font=('Arial', 10),
                 foreground='gray').pack(side=tk.LEFT, padx=10)

        # Grid con tablas
        grid_frame = ttk.Frame(self.scrollable_frame)
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Headers del grid
        ttk.Label(grid_frame, text="Tabla", font=('Arial', 10, 'bold'),
                 width=40, anchor='w').grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Label(grid_frame, text="Comentario", font=('Arial', 10, 'bold'),
                 width=80, anchor='w').grid(row=0, column=1, padx=5, pady=5, sticky='w')

        # Agregar separador
        ttk.Separator(grid_frame, orient='horizontal').grid(row=1, column=0, columnspan=2,
                                                            sticky='ew', pady=5)

        # Crear campos editables para cada tabla
        for idx, (nombre_tabla, comentario_actual) in enumerate(self.tablas_con_comentarios, start=2):
            # Nombre de la tabla
            ttk.Label(grid_frame, text=nombre_tabla, width=40, anchor='w',
                     font=('Arial', 9)).grid(row=idx, column=0, padx=5, pady=5, sticky='w')

            # Text widget para comentario
            text_widget = tk.Text(grid_frame, width=80, height=3, wrap=tk.WORD,
                                 font=('Arial', 9), relief='solid', borderwidth=1)
            text_widget.grid(row=idx, column=1, padx=5, pady=5, sticky='ew')

            # Insertar comentario actual si existe
            if comentario_actual:
                text_widget.insert('1.0', comentario_actual)

            # Guardar referencia al widget con prefijo para diferenciar de campos
            self.widgets_comentarios[f'tabla_{nombre_tabla}'] = text_widget

        print(f"Comentarios de tablas mostrados: {len(self.tablas_con_comentarios)} tablas")

    def cargar_todos_objetos_tipo(self, tipo: str):
        """Carga y muestra todos los objetos de un tipo específico"""
        try:
            if tipo == "Procedimientos":
                sql = """
                SELECT p.proname, obj_description(p.oid, 'pg_proc')
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = %s AND p.prokind = 'p'
                ORDER BY p.proname
                """
            elif tipo == "Funciones":
                sql = """
                SELECT p.proname, obj_description(p.oid, 'pg_proc')
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = %s AND p.prokind = 'f'
                  AND p.prorettype != (SELECT oid FROM pg_type WHERE typname = 'trigger')
                ORDER BY p.proname
                """
            elif tipo == "Vistas":
                sql = """
                SELECT c.relname, obj_description(c.oid)
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind = 'v' AND n.nspname = %s
                ORDER BY c.relname
                """
            elif tipo == "Triggers":
                sql = """
                SELECT t.tgname, obj_description(t.oid, 'pg_trigger')
                FROM pg_trigger t
                JOIN pg_class c ON c.oid = t.tgrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = %s AND NOT t.tgisinternal
                ORDER BY t.tgname
                """
            elif tipo == "Funciones Trigger":
                sql = """
                SELECT p.proname, obj_description(p.oid, 'pg_proc')
                FROM pg_proc p
                JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE n.nspname = %s
                  AND p.prorettype = (SELECT oid FROM pg_type WHERE typname = 'trigger')
                ORDER BY p.proname
                """
            elif tipo == "Indices":
                sql = """
                SELECT
                    i.indexname AS indice,
                    obj_description(
                        (n.nspname || '.' || i.indexname)::regclass::oid,
                        'pg_class'
                    ) AS comentario
                FROM pg_indexes i
                JOIN pg_namespace n ON n.nspname = i.schemaname
                LEFT JOIN pg_constraint c ON c.conname = i.indexname AND c.connamespace = n.oid
                WHERE i.schemaname = %s
                AND c.conname IS NULL  -- Excluir índices creados por constraints (PK, UNIQUE, etc)
                ORDER BY indice
                """
            elif tipo == "Constraints":
                sql = """
                SELECT conname,
                obj_description(oid, 'pg_constraint') AS descripcion
                FROM pg_constraint
                WHERE connamespace = (SELECT oid FROM pg_namespace WHERE nspname = %s)
                ORDER BY conname
                """
            elif tipo == "Types":
                sql = """
                SELECT
                    t.typname AS type,
                    obj_description(t.oid, 'pg_type') AS comentario
                FROM pg_type t
                JOIN pg_namespace n ON n.oid = t.typnamespace
                WHERE n.nspname = %s
                  AND t.typtype IN ('c', 'e', 'd', 'r')
                  AND NOT EXISTS (
                      SELECT 1 FROM pg_class c WHERE c.reltype = t.oid
                  )
                ORDER BY t.typname
                """
            elif tipo == "Foreign Servers":
                sql = """
                SELECT
                    fs.srvname AS foreign_server,
                    obj_description(fs.oid, 'pg_foreign_server') AS comentario
                FROM pg_foreign_server fs
                ORDER BY fs.srvname
                """
            elif tipo == "Tablas foraneas":
                sql = """
                SELECT
                    c.relname AS tabla_foranea,
                    obj_description(c.oid) AS comentario
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind = 'f' AND n.nspname = %s
                ORDER BY c.relname
                """
            elif tipo == "Sinonimos":
                # PostgreSQL no tiene sinónimos nativos, retornar vacío
                messagebox.showinfo("No Soportado", "PostgreSQL no tiene sinónimos nativos como Oracle")
                return
            elif tipo == "Jobs":
                sql = """
                SELECT
                    jobname AS job,
                    obj_description(jobid::oid, 'pg_cron') AS comentario
                FROM cron.job
                WHERE database = current_database()
                ORDER BY jobname
                """
            else:
                return

            # Ejecutar la consulta (algunos tipos no requieren parámetro de schema)
            if tipo in ["Foreign Servers", "Jobs"]:
                self.cursor.execute(sql)
            elif tipo == "Sinonimos":
                return  # Ya retornó antes
            else:
                self.cursor.execute(sql, (self.schema,))

            objetos_info = [(row[0], row[1] or '') for row in self.cursor.fetchall()]

            if not objetos_info:
                messagebox.showinfo("Sin Objetos", f"No se encontraron {tipo.lower()} en el esquema '{self.schema}'")
                return

            self.objetos_actuales = objetos_info

            # Limpiar el frame anterior
            self.limpiar_frame_campos()

            # Header con información del tipo
            header_frame = ttk.Frame(self.scrollable_frame)
            header_frame.pack(fill=tk.X, padx=10, pady=10)

            ttk.Label(header_frame, text=f"{tipo}",
                     font=('Arial', 14, 'bold'),
                     foreground='#2c3e50').pack(side=tk.LEFT)

            ttk.Label(header_frame, text=f"({len(objetos_info)} objetos)",
                     font=('Arial', 10),
                     foreground='gray').pack(side=tk.LEFT, padx=10)

            # Grid con objetos
            grid_frame = ttk.Frame(self.scrollable_frame)
            grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            # Headers del grid
            ttk.Label(grid_frame, text="Objeto", font=('Arial', 10, 'bold'),
                     width=40, anchor='w').grid(row=0, column=0, padx=5, pady=5, sticky='w')
            ttk.Label(grid_frame, text="Comentario", font=('Arial', 10, 'bold'),
                     width=80, anchor='w').grid(row=0, column=1, padx=5, pady=5, sticky='w')

            # Agregar separador
            ttk.Separator(grid_frame, orient='horizontal').grid(row=1, column=0, columnspan=2,
                                                                sticky='ew', pady=5)

            # Crear campos editables para cada objeto
            for idx, (nombre_objeto, comentario_actual) in enumerate(objetos_info, start=2):
                # Nombre del objeto
                ttk.Label(grid_frame, text=nombre_objeto, width=40, anchor='w',
                         font=('Arial', 9)).grid(row=idx, column=0, padx=5, pady=5, sticky='w')

                # Text widget para comentario
                text_widget = tk.Text(grid_frame, width=80, height=3, wrap=tk.WORD,
                                     font=('Arial', 9), relief='solid', borderwidth=1)
                text_widget.grid(row=idx, column=1, padx=5, pady=5, sticky='ew')

                # Insertar comentario actual si existe
                if comentario_actual:
                    text_widget.insert('1.0', comentario_actual)

                # Guardar referencia al widget
                self.widgets_comentarios[nombre_objeto] = text_widget

            print(f"{tipo} cargados: {len(objetos_info)} objetos")

        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar {tipo.lower()}:\n{e}")

    def limpiar_frame_campos(self):
        """Limpia el contenido del frame de campos"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.widgets_comentarios.clear()

    def cargar_campos_tabla(self, tabla: str):
        """Carga y muestra los campos de una tabla específica"""
        # Obtener campos de la tabla
        campos_info = self.obtener_campos_tabla(tabla)

        if not campos_info:
            messagebox.showwarning("Sin Campos", f"No se encontraron campos en la tabla '{tabla}'")
            return

        self.tabla_actual = tabla
        self.campos_actuales = campos_info

        # Limpiar el frame anterior
        self.limpiar_frame_campos()

        # Header con el nombre de la tabla
        header_frame = ttk.Frame(self.scrollable_frame)
        header_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(header_frame, text=f"Tabla: {tabla}",
                 font=('Arial', 14, 'bold'),
                 foreground='#2c3e50').pack(side=tk.LEFT)

        ttk.Label(header_frame, text=f"({len(campos_info)} campos)",
                 font=('Arial', 10),
                 foreground='gray').pack(side=tk.LEFT, padx=10)

        # Grid con campos
        grid_frame = ttk.Frame(self.scrollable_frame)
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Headers del grid
        ttk.Label(grid_frame, text="Campo", font=('Arial', 10, 'bold'),
                 width=30, anchor='w').grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Label(grid_frame, text="Tipo de Dato", font=('Arial', 10, 'bold'),
                 width=25, anchor='w').grid(row=0, column=1, padx=5, pady=5, sticky='w')
        ttk.Label(grid_frame, text="Comentario", font=('Arial', 10, 'bold'),
                 width=70, anchor='w').grid(row=0, column=2, padx=5, pady=5, sticky='w')

        # Agregar separador
        ttk.Separator(grid_frame, orient='horizontal').grid(row=1, column=0, columnspan=3,
                                                            sticky='ew', pady=5)

        # Crear campos editables
        for idx, (campo, tipo, comentario_actual) in enumerate(campos_info, start=2):
            # Nombre del campo
            ttk.Label(grid_frame, text=campo, width=30, anchor='w',
                     font=('Arial', 9)).grid(row=idx, column=0, padx=5, pady=5, sticky='w')

            # Tipo de dato
            ttk.Label(grid_frame, text=tipo, width=25, anchor='w',
                     foreground='gray', font=('Arial', 9)).grid(row=idx, column=1, padx=5, pady=5, sticky='w')

            # Text widget para comentario (multilinea con altura fija)
            text_widget = tk.Text(grid_frame, width=70, height=3, wrap=tk.WORD,
                                 font=('Arial', 9), relief='solid', borderwidth=1)
            text_widget.grid(row=idx, column=2, padx=5, pady=5, sticky='ew')

            # Insertar comentario actual si existe
            if comentario_actual:
                text_widget.insert('1.0', comentario_actual)

            # Guardar referencia al widget
            self.widgets_comentarios[campo] = text_widget

        print(f"Tabla '{tabla}' cargada con {len(campos_info)} campos")


    def obtener_campos_tabla(self, tabla: str) -> List[Tuple[str, str, str]]:
        """Obtiene información de campos de una tabla"""
        sql = """

        SELECT

            c.column_name,

            CASE

                WHEN c.udt_name = 'date' THEN 'date'

                WHEN c.udt_name = 'timestamp' THEN 'timestamp'

                WHEN c.udt_name = 'int8' THEN 'bigint'

                WHEN c.udt_name = 'int4' THEN 'integer'

                WHEN c.udt_name = 'int2' THEN 'smallint'

                WHEN c.udt_name = 'text' THEN 'text'

                WHEN c.udt_name = 'numeric' THEN 'numeric'

                WHEN c.udt_name = 'jsonb' THEN 'jsonb'

                WHEN c.udt_name IN ('bpchar', 'varchar') THEN

                    'varchar(' || COALESCE(c.character_maximum_length, 255)::text || ')'

                WHEN c.character_maximum_length IS NOT NULL THEN

                    c.udt_name || '(' || c.character_maximum_length || ')'

                ELSE c.udt_name

            END AS tipo_dato,

            COALESCE(pgd.description, '') AS comentario

        FROM information_schema.columns c

        LEFT JOIN pg_catalog.pg_description pgd ON (

            pgd.objoid = (

                SELECT c_table.oid

                FROM pg_catalog.pg_class c_table

                WHERE c_table.relname = c.table_name

                  AND c_table.relnamespace = (

                      SELECT n.oid

                      FROM pg_catalog.pg_namespace n

                      WHERE n.nspname = c.table_schema

                  )

            )

            AND pgd.objsubid = c.ordinal_position

        )

        WHERE c.table_schema = %s

          AND c.table_name = %s

        ORDER BY c.ordinal_position;

        """



        try:

            self.cursor.execute(sql, (self.schema, tabla))

            return [(row[0], row[1], row[2]) for row in self.cursor.fetchall()]

        except Exception as e:

            print(f"Error al obtener campos de {tabla}: {e}")

            return []



    def guardar_comentarios(self):
        """Guarda los comentarios según el modo actual"""
        if self.modo_actual == "tablas":
            self.guardar_comentarios_tabla()
        else:
            self.guardar_comentarios_objetos()

    def guardar_comentarios_tabla(self):
        """Guarda los comentarios de las tablas y campos"""
        try:
            total_modificados = 0

            # Guardar comentarios de las tablas
            if self.tablas_con_comentarios and not self.tabla_actual:
                for nombre_tabla, comentario_original in self.tablas_con_comentarios:
                    widget = self.widgets_comentarios.get(f'tabla_{nombre_tabla}')
                    if not widget:
                        continue

                    # Obtener el nuevo comentario del widget
                    nuevo_comentario = widget.get('1.0', tk.END).strip()

                    # Solo actualizar si cambió
                    if nuevo_comentario != comentario_original:
                        self.aplicar_comentario_tabla(nombre_tabla, nuevo_comentario)
                        total_modificados += 1

                if total_modificados > 0:
                    messagebox.showinfo("Éxito", f"Se guardaron {total_modificados} comentarios de tablas")
                    # Recargar comentarios de tablas
                    self.cargar_comentarios_tablas()
                    self.limpiar_frame_campos()
                    self.mostrar_comentarios_tablas()
                else:
                    messagebox.showinfo("Sin Cambios", "No hay comentarios nuevos o modificados en las tablas")
                return

            # Guardar comentarios de campos de una tabla específica
            if not self.tabla_actual:
                messagebox.showwarning("Sin Tabla", "Seleccione una tabla para guardar comentarios de campos")
                return

            campos_modificados = 0
            for campo, tipo, comentario_original in self.campos_actuales:
                widget = self.widgets_comentarios.get(campo)
                if not widget:
                    continue

                # Obtener el nuevo comentario del widget
                nuevo_comentario = widget.get('1.0', tk.END).strip()

                # Solo actualizar si cambió
                if nuevo_comentario != comentario_original:
                    self.aplicar_comentario_campo(self.tabla_actual, campo, nuevo_comentario)
                    campos_modificados += 1

            if campos_modificados > 0:
                messagebox.showinfo("Éxito", f"Se guardaron {campos_modificados} comentarios en la tabla '{self.tabla_actual}'")
                # Recargar la tabla actual para mostrar los cambios
                self.cargar_campos_tabla(self.tabla_actual)
            else:
                messagebox.showinfo("Sin Cambios", f"No hay comentarios nuevos o modificados en la tabla '{self.tabla_actual}'")

        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar comentarios:\n{e}")

    def guardar_comentarios_objetos(self):
        """Guarda los comentarios de todos los objetos del tipo actual"""
        if not self.tipo_objeto_actual or not self.objetos_actuales:
            messagebox.showwarning("Sin Objetos", "Seleccione un tipo de objeto primero")
            return

        try:
            objetos_modificados = 0

            for nombre_objeto, comentario_original in self.objetos_actuales:
                widget = self.widgets_comentarios.get(nombre_objeto)
                if not widget:
                    continue

                # Obtener el nuevo comentario del widget
                nuevo_comentario = widget.get('1.0', tk.END).strip()

                # Solo actualizar si cambió
                if nuevo_comentario != comentario_original:
                    self.aplicar_comentario_a_objeto(nombre_objeto, self.tipo_objeto_actual, nuevo_comentario)
                    objetos_modificados += 1

            if objetos_modificados > 0:
                messagebox.showinfo("Éxito", f"Se guardaron {objetos_modificados} comentarios en {self.tipo_objeto_actual.lower()}")
                # Recargar el tipo actual para mostrar los cambios
                self.cargar_todos_objetos_tipo(self.tipo_objeto_actual)
            else:
                messagebox.showinfo("Sin Cambios", f"No hay comentarios nuevos o modificados en {self.tipo_objeto_actual.lower()}")

        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar comentarios de {self.tipo_objeto_actual.lower()}:\n{e}")



    def aplicar_comentario_tabla(self, tabla: str, comentario: str):
        """Aplica un comentario a una tabla"""
        try:
            if comentario:
                sql = f"COMMENT ON TABLE {self.schema}.{tabla} IS %s;"
                self.cursor.execute(sql, (comentario,))
            else:
                sql = f"COMMENT ON TABLE {self.schema}.{tabla} IS NULL;"
                self.cursor.execute(sql)

            print(f"Comentario actualizado: tabla {tabla}")

        except Exception as e:
            print(f"Error al actualizar comentario de tabla {tabla}: {e}")
            raise

    def aplicar_comentario_campo(self, tabla: str, campo: str, comentario: str):
        """Aplica un comentario a un campo específico de una tabla"""
        try:
            if comentario:
                sql = f"COMMENT ON COLUMN {self.schema}.{tabla}.{campo} IS %s;"
                self.cursor.execute(sql, (comentario,))
            else:
                sql = f"COMMENT ON COLUMN {self.schema}.{tabla}.{campo} IS NULL;"
                self.cursor.execute(sql)

            print(f"Comentario actualizado: {tabla}.{campo}")

        except Exception as e:
            print(f"Error al actualizar comentario de {tabla}.{campo}: {e}")
            raise

    def aplicar_comentario_a_objeto(self, nombre: str, tipo: str, comentario: str):
        """Aplica un comentario a un objeto (procedimiento, función, vista, trigger)"""
        try:
            if tipo == "Procedimientos":
                tipo_sql = "FUNCTION"  # En PostgreSQL los procedimientos se comentan como FUNCTION
            elif tipo == "Funciones":
                tipo_sql = "FUNCTION"
            elif tipo == "Vistas":
                tipo_sql = "VIEW"
            elif tipo == "Triggers":
                # Los triggers requieren especificar la tabla, buscarla primero
                sql_tabla = """
                SELECT c.relname
                FROM pg_trigger t
                JOIN pg_class c ON c.oid = t.tgrelid
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = %s AND t.tgname = %s
                """
                self.cursor.execute(sql_tabla, (self.schema, nombre))
                result = self.cursor.fetchone()
                if not result:
                    raise Exception(f"No se encontró la tabla para el trigger '{nombre}'")
                tabla_trigger = result[0]

                if comentario:
                    sql = f"COMMENT ON TRIGGER {nombre} ON {self.schema}.{tabla_trigger} IS %s;"
                    self.cursor.execute(sql, (comentario,))
                else:
                    sql = f"COMMENT ON TRIGGER {nombre} ON {self.schema}.{tabla_trigger} IS NULL;"
                    self.cursor.execute(sql)

                print(f"Comentario actualizado: trigger {nombre}")
                return

            elif tipo == "Funciones Trigger":
                tipo_sql = "FUNCTION"
            elif tipo == "Indices":
                tipo_sql = "INDEX"
            elif tipo == "Constraints":
                tipo_sql = "CONSTRAINT"
                # Los constraints necesitan el nombre de la tabla
                sql_tabla = """
                SELECT c.relname
                FROM pg_constraint con
                JOIN pg_class c ON c.oid = con.conrelid
                JOIN pg_namespace n ON n.oid = con.connamespace
                WHERE n.nspname = %s AND con.conname = %s
                """
                self.cursor.execute(sql_tabla, (self.schema, nombre))
                result = self.cursor.fetchone()
                if not result:
                    raise Exception(f"No se encontró la tabla para el constraint '{nombre}'")
                tabla_constraint = result[0]

                if comentario:
                    sql = f"COMMENT ON CONSTRAINT {nombre} ON {self.schema}.{tabla_constraint} IS %s;"
                    self.cursor.execute(sql, (comentario,))
                else:
                    sql = f"COMMENT ON CONSTRAINT {nombre} ON {self.schema}.{tabla_constraint} IS NULL;"
                    self.cursor.execute(sql)

                print(f"Comentario actualizado: constraint {nombre}")
                return
            elif tipo == "Types":
                tipo_sql = "TYPE"
            elif tipo == "Foreign Servers":
                # Foreign servers no usan esquema
                if comentario:
                    sql = f"COMMENT ON SERVER {nombre} IS %s;"
                    self.cursor.execute(sql, (comentario,))
                else:
                    sql = f"COMMENT ON SERVER {nombre} IS NULL;"
                    self.cursor.execute(sql)
                print(f"Comentario actualizado: foreign server {nombre}")
                return
            elif tipo == "Tablas foraneas":
                tipo_sql = "FOREIGN TABLE"
            elif tipo == "Jobs":
                # Jobs requieren manejo especial con pg_cron
                messagebox.showwarning("No Soportado", "La edición de comentarios en Jobs no está soportada directamente.\nUse la extensión pg_cron para gestionar jobs.")
                return
            else:
                raise Exception(f"Tipo de objeto no soportado: {tipo}")

            # Para procedimientos, funciones, vistas, índices, types, tablas foráneas
            if comentario:
                sql = f"COMMENT ON {tipo_sql} {self.schema}.{nombre} IS %s;"
                self.cursor.execute(sql, (comentario,))
            else:
                sql = f"COMMENT ON {tipo_sql} {self.schema}.{nombre} IS NULL;"
                self.cursor.execute(sql)

            print(f"Comentario actualizado: {tipo_sql.lower()} {nombre}")

        except Exception as e:
            print(f"Error al actualizar comentario de {nombre}: {e}")
            raise

    def recargar_actual(self):
        """Recarga el elemento actual según el modo"""
        if self.modo_actual == "tablas":
            if self.tabla_actual:
                # Si hay una tabla seleccionada, recargar sus campos
                self.cargar_campos_tabla(self.tabla_actual)
                messagebox.showinfo("Recargado", f"La tabla '{self.tabla_actual}' se ha recargado correctamente")
            else:
                # Si no hay tabla seleccionada, recargar comentarios de tablas
                self.cargar_comentarios_tablas()
                self.limpiar_frame_campos()
                self.mostrar_comentarios_tablas()
                messagebox.showinfo("Recargado", "Los comentarios de las tablas se han recargado correctamente")
        else:
            if not self.tipo_objeto_actual:
                messagebox.showwarning("Sin Tipo", "Seleccione un tipo de objeto primero")
                return
            self.cargar_todos_objetos_tipo(self.tipo_objeto_actual)
            messagebox.showinfo("Recargado", f"{self.tipo_objeto_actual} recargados correctamente")



    def cerrar(self):

        """Cierra la conexión y la ventana"""

        if self.cursor:

            self.cursor.close()

        if self.conn:

            self.conn.close()

        self.root.quit()

        self.root.destroy()



    def ejecutar(self):

        """Ejecuta el loop principal de la GUI"""

        try:

            self.root.protocol("WM_DELETE_WINDOW", self.cerrar)

            self.root.mainloop()

        except Exception as e:

            # Si la ventana ya fue destruida, ignorar el error

            if "application has been destroyed" not in str(e):

                raise



def main():

    # Configurar codificación UTF-8 para la consola

    import builtins

    try:

        sys.stdout.reconfigure(encoding='utf-8')

        sys.stderr.reconfigure(encoding='utf-8')

    except:

        # Fallback: envolver print para evitar errores de codificación

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



    if len(sys.argv) != 7:

        print("Error: Se requieren 6 parametros")

        print("Uso: python agregar_comentarios.py <host> <puerto> <bd> <usuario> <password> <esquema>")

        sys.exit(1)



    host = sys.argv[1]

    puerto = sys.argv[2]

    bd = sys.argv[3]

    usuario = sys.argv[4]

    password = sys.argv[5]

    esquema = sys.argv[6]



    print(f"Iniciando interfaz de comentarios...")

    print(f"Host: {host}")

    print(f"Puerto: {puerto}")

    print(f"Base de datos: {bd}")

    print(f"Usuario: {usuario}")

    print(f"Esquema: {esquema}")



    try:

        app = ComentariosGUI(host, puerto, bd, usuario, password, esquema)

        app.ejecutar()

        print("\nAplicacion cerrada correctamente")

    except Exception as e:

        print(f"\nError fatal: {e}")

        import traceback

        traceback.print_exc()

        sys.exit(1)





if __name__ == "__main__":

    main()

