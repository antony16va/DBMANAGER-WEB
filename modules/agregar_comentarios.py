import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from datetime import datetime
from typing import List, Tuple
import psycopg2

# ---------------------------------------------------------------------------
# SQL queries for each object type: (query, needs_schema_param)
# ---------------------------------------------------------------------------
_OBJECT_SQL: dict = {
    "Procedimientos": ("""
        SELECT p.proname, obj_description(p.oid, 'pg_proc')
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = %s AND p.prokind = 'p'
        ORDER BY p.proname""", True),
    "Funciones": ("""
        SELECT p.proname, obj_description(p.oid, 'pg_proc')
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        JOIN pg_type trig ON trig.typname = 'trigger'
        WHERE n.nspname = %s AND p.prokind = 'f'
          AND p.prorettype != trig.oid
        ORDER BY p.proname""", True),
    "Vistas": ("""
        SELECT c.relname, obj_description(c.oid)
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'v' AND n.nspname = %s
        ORDER BY c.relname""", True),
    "Triggers": ("""
        SELECT t.tgname, obj_description(t.oid, 'pg_trigger')
        FROM pg_trigger t
        JOIN pg_class c ON c.oid = t.tgrelid
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = %s AND NOT t.tgisinternal
        ORDER BY t.tgname""", True),
    "Funciones Trigger": ("""
        SELECT p.proname, obj_description(p.oid, 'pg_proc')
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        JOIN pg_type trig ON trig.typname = 'trigger'
        WHERE n.nspname = %s AND p.prorettype = trig.oid
        ORDER BY p.proname""", True),
    "Indices": ("""
        SELECT i.indexname,
               obj_description((n.nspname || '.' || i.indexname)::regclass::oid, 'pg_class')
        FROM pg_indexes i
        JOIN pg_namespace n ON n.nspname = i.schemaname
        LEFT JOIN pg_constraint c ON c.conname = i.indexname AND c.connamespace = n.oid
        WHERE i.schemaname = %s AND c.conname IS NULL
        ORDER BY i.indexname""", True),
    "Constraints": ("""
        SELECT con.conname, obj_description(con.oid, 'pg_constraint')
        FROM pg_constraint con
        JOIN pg_namespace n ON n.oid = con.connamespace AND n.nspname = %s
        ORDER BY con.conname""", True),
    "Types": ("""
        SELECT t.typname, obj_description(t.oid, 'pg_type')
        FROM pg_type t
        JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = %s AND t.typtype IN ('c', 'e', 'd', 'r')
          AND NOT EXISTS (SELECT 1 FROM pg_class c WHERE c.reltype = t.oid)
        ORDER BY t.typname""", True),
    "Foreign Servers": ("""
        SELECT fs.srvname, obj_description(fs.oid, 'pg_foreign_server')
        FROM pg_foreign_server fs
        ORDER BY fs.srvname""", False),
    "Tablas foraneas": ("""
        SELECT c.relname, obj_description(c.oid)
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'f' AND n.nspname = %s
        ORDER BY c.relname""", True),
    "Jobs": ("""
        SELECT jobname, obj_description(jobid::oid, 'pg_cron')
        FROM cron.job
        WHERE database = current_database()
        ORDER BY jobname""", False),
}

# Maps object type → SQL COMMENT ON keyword (for schema.name targets)
_COMMENT_TARGET: dict = {
    "Procedimientos":    "FUNCTION",
    "Funciones":         "FUNCTION",
    "Funciones Trigger": "FUNCTION",
    "Vistas":            "VIEW",
    "Indices":           "INDEX",
    "Types":             "TYPE",
    "Tablas foraneas":   "FOREIGN TABLE",
}


class ComentariosGUI:

    def __init__(self, host: str, port: str, database: str,
                 user: str, password: str, schema: str):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.schema = schema
        self.conn = None
        self.cursor = None
        self.tablas_nombres: List[str] = []
        self.tablas_con_comentarios: List[Tuple[str, str]] = []
        self.tabla_actual: str = None
        self.campos_actuales: List[Tuple[str, str, str]] = []
        self.tipo_objeto_actual: str = None
        self.objetos_actuales: List[Tuple[str, str]] = []
        self.widgets_comentarios: dict = {}
        self.modo_actual = "tablas"
        self.root = tk.Tk()
        self.root.title(f"Agregar Comentarios - {schema} @ {database}")
        self.root.geometry("1400x750")
        self.conectar_bd()
        self.crear_interfaz()
        self.cargar_tablas(init=True)

    # ── DB helpers ────────────────────────────────────────────────────────────

    def conectar_bd(self):
        try:
            self.conn = psycopg2.connect(
                host=self.host, port=self.port, database=self.database,
                user=self.user, password=self.password,
            )
            self.conn.autocommit = True
            self.cursor = self.conn.cursor()
            print(f"Conexión exitosa a {self.database}")
        except Exception as e:
            messagebox.showerror("Error de Conexión",
                f"No se pudo conectar a la base de datos:\n{e}")
            sys.exit(1)

    def _exec_comment(self, target: str, comentario: str):
        """Executes: COMMENT ON <target> IS <value|NULL>."""
        if comentario:
            self.cursor.execute(f"COMMENT ON {target} IS %s;", (comentario,))
        else:
            self.cursor.execute(f"COMMENT ON {target} IS NULL;")

    def _tabla_para_trigger(self, nombre: str) -> str:
        self.cursor.execute("""
            SELECT c.relname
            FROM pg_trigger t
            JOIN pg_class c ON c.oid = t.tgrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = %s AND t.tgname = %s
        """, (self.schema, nombre))
        row = self.cursor.fetchone()
        if not row:
            raise Exception(f"No se encontró la tabla para el trigger '{nombre}'")
        return row[0]

    def _tabla_para_constraint(self, nombre: str) -> str:
        self.cursor.execute("""
            SELECT c.relname
            FROM pg_constraint con
            JOIN pg_class c ON c.oid = con.conrelid
            JOIN pg_namespace n ON n.oid = con.connamespace
            WHERE n.nspname = %s AND con.conname = %s
        """, (self.schema, nombre))
        row = self.cursor.fetchone()
        if not row:
            raise Exception(f"No se encontró la tabla para el constraint '{nombre}'")
        return row[0]

    # ── Data loading ──────────────────────────────────────────────────────────

    def cargar_tablas(self, init: bool = False):
        """Loads table names + comments in one query.
        Pass init=True on startup to exit if the schema has no tables."""
        try:
            self.cursor.execute("""
                SELECT c.relname, obj_description(c.oid)
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE c.relkind = 'r' AND n.nspname = %s
                ORDER BY c.relname
            """, (self.schema,))
            rows = self.cursor.fetchall()
            if init and not rows:
                messagebox.showwarning("Sin Tablas",
                    f"No se encontraron tablas en el esquema '{self.schema}'")
                self.cerrar()
                return
            self.tablas_nombres = [r[0] for r in rows]
            self.tablas_con_comentarios = [(r[0], r[1] or '') for r in rows]
            self.combo_items['values'] = self.tablas_nombres
            print(f"Se cargaron {len(rows)} tablas")
        except Exception as e:
            if init:
                messagebox.showerror("Error", f"Error al cargar tablas:\n{e}")
                self.cerrar()
            else:
                print(f"Error al cargar tablas: {e}")

    def obtener_campos_tabla(self, tabla: str) -> List[Tuple[str, str, str]]:
        """Returns (column_name, data_type, comment) for every column of a table."""
        try:
            self.cursor.execute("""
                SELECT c.column_name,
                    CASE
                        WHEN c.udt_name IN ('date','timestamp','text','numeric','jsonb')
                            THEN c.udt_name
                        WHEN c.udt_name = 'int8'  THEN 'bigint'
                        WHEN c.udt_name = 'int4'  THEN 'integer'
                        WHEN c.udt_name = 'int2'  THEN 'smallint'
                        WHEN c.udt_name IN ('bpchar','varchar') THEN
                            'varchar(' || COALESCE(c.character_maximum_length, 255)::text || ')'
                        WHEN c.character_maximum_length IS NOT NULL THEN
                            c.udt_name || '(' || c.character_maximum_length || ')'
                        ELSE c.udt_name
                    END,
                    COALESCE(pgd.description, '')
                FROM information_schema.columns c
                JOIN pg_catalog.pg_class cl
                    ON cl.relname = c.table_name
                JOIN pg_catalog.pg_namespace n
                    ON n.oid = cl.relnamespace AND n.nspname = c.table_schema
                LEFT JOIN pg_catalog.pg_description pgd
                    ON pgd.objoid = cl.oid AND pgd.objsubid = c.ordinal_position
                WHERE c.table_schema = %s AND c.table_name = %s
                ORDER BY c.ordinal_position
            """, (self.schema, tabla))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error al obtener campos de {tabla}: {e}")
            return []

    def cargar_todos_objetos_tipo(self, tipo: str):
        """Loads and displays all objects of the given type."""
        if tipo == "Sinonimos":
            messagebox.showinfo("No Soportado",
                "PostgreSQL no tiene sinónimos nativos como Oracle")
            return
        entry = _OBJECT_SQL.get(tipo)
        if not entry:
            return
        sql, needs_schema = entry
        try:
            self.cursor.execute(sql, (self.schema,) if needs_schema else ())
            objetos_info = [(r[0], r[1] or '') for r in self.cursor.fetchall()]
        except Exception as e:
            messagebox.showerror("Error", f"Error al cargar {tipo.lower()}:\n{e}")
            return
        if not objetos_info:
            messagebox.showinfo("Sin Objetos",
                f"No se encontraron {tipo.lower()} en el esquema '{self.schema}'")
            return
        self.objetos_actuales = objetos_info
        self.limpiar_frame_campos()
        self._render_objetos_grid(tipo, f"({len(objetos_info)} objetos)", objetos_info)
        print(f"{tipo} cargados: {len(objetos_info)} objetos")

    # ── UI construction ───────────────────────────────────────────────────────

    def crear_interfaz(self):
        info_frame = ttk.Frame(self.root, padding="10")
        info_frame.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(info_frame, text=f"Base de datos: {self.database}",
                  font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        ttk.Label(info_frame, text=f"Esquema: {self.schema}",
                  font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)

        modo_frame = ttk.Frame(self.root, padding="10")
        modo_frame.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(modo_frame, text="Modo:",
                  font=('Arial', 11, 'bold')).pack(side=tk.LEFT, padx=5)
        self.modo_var = tk.StringVar(value="tablas")
        ttk.Radiobutton(modo_frame, text="Tablas", variable=self.modo_var,
                        value="tablas", command=self.cambiar_modo).pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(modo_frame, text="Otros Objetos", variable=self.modo_var,
                        value="objetos", command=self.cambiar_modo).pack(side=tk.LEFT, padx=10)

        self.tipo_objeto_frame = ttk.Frame(self.root, padding="10")
        self.tipo_objeto_frame.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(self.tipo_objeto_frame, text="Tipo de Objeto:",
                  font=('Arial', 11, 'bold')).pack(side=tk.LEFT, padx=5)
        self.tipo_objeto_var = tk.StringVar()
        self.combo_tipo_objeto = ttk.Combobox(
            self.tipo_objeto_frame, textvariable=self.tipo_objeto_var,
            state='readonly', width=30, font=('Arial', 10),
            values=["Procedimientos", "Funciones", "Vistas", "Triggers", "Funciones Trigger",
                    "Types", "Foreign Servers", "Tablas foraneas", "Sinonimos",
                    "Indices", "Constraints", "Jobs"])
        self.combo_tipo_objeto.pack(side=tk.LEFT, padx=5)
        self.combo_tipo_objeto.bind('<<ComboboxSelected>>', self.on_tipo_objeto_seleccionado)
        self.tipo_objeto_frame.pack_forget()

        self.selector_frame = ttk.Frame(self.root, padding="10")
        self.selector_frame.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(self.selector_frame, text="Seleccionar Tabla:",
                  font=('Arial', 11, 'bold')).pack(side=tk.LEFT, padx=5)
        self.item_var = tk.StringVar()
        self.combo_items = ttk.Combobox(self.selector_frame, textvariable=self.item_var,
                                        state='readonly', width=40, font=('Arial', 10))
        self.combo_items.pack(side=tk.LEFT, padx=5)
        self.combo_items.bind('<<ComboboxSelected>>', self.on_item_seleccionado)

        btn_frame = ttk.Frame(self.root, padding="10")
        btn_frame.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(btn_frame, text="Guardar Comentarios",
                   command=self.guardar_comentarios).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Recargar",
                   command=self.recargar_actual).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="SQL (Todos)",
                   command=lambda: self._generar_sql_script(False)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="SQL (Cambios)",
                   command=lambda: self._generar_sql_script(True)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cerrar",
                   command=self.cerrar).pack(side=tk.RIGHT, padx=5)

        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.canvas = tk.Canvas(self.main_frame, bg='white')
        self.scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical",
                                       command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.bind_all(
            "<MouseWheel>",
            lambda e: self.canvas.yview_scroll(int(-1 * (e.delta / 120)), "units"))
        self.crear_mensaje_inicial()

    def _render_objetos_grid(self, titulo: str, count_text: str,
                              items: List[Tuple[str, str]],
                              key_prefix: str = '', obj_label: str = 'Objeto'):
        """Renders a 2-column (name | comment) scrollable grid."""
        header_frame = ttk.Frame(self.scrollable_frame)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(header_frame, text=titulo, font=('Arial', 14, 'bold'),
                  foreground='#2c3e50').pack(side=tk.LEFT)
        ttk.Label(header_frame, text=count_text, font=('Arial', 10),
                  foreground='gray').pack(side=tk.LEFT, padx=10)

        grid_frame = ttk.Frame(self.scrollable_frame)
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        ttk.Label(grid_frame, text=obj_label, font=('Arial', 10, 'bold'),
                  width=40, anchor='w').grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Label(grid_frame, text="Comentario", font=('Arial', 10, 'bold'),
                  width=80, anchor='w').grid(row=0, column=1, padx=5, pady=5, sticky='w')
        ttk.Separator(grid_frame, orient='horizontal').grid(
            row=1, column=0, columnspan=2, sticky='ew', pady=5)

        for idx, (nombre, comentario) in enumerate(items, start=2):
            bg = '#e8f4f8' if idx % 2 == 0 else '#e8f5e9'
            key = f'{key_prefix}{nombre}'
            tk.Label(grid_frame, text=nombre, width=40, anchor='w',
                     font=('Arial', 9), bg=bg).grid(row=idx, column=0,
                                                    padx=5, pady=5, sticky='w')
            w = tk.Text(grid_frame, width=80, height=3, wrap=tk.WORD,
                        font=('Arial', 9), relief='solid', borderwidth=1, bg=bg)
            w.grid(row=idx, column=1, padx=5, pady=5, sticky='ew')
            if comentario:
                w.insert('1.0', comentario)
            self.widgets_comentarios[key] = w

    def limpiar_frame_campos(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.widgets_comentarios.clear()

    def crear_mensaje_inicial(self):
        texto = ("Seleccione un objeto del menú" if self.modo_actual == "tablas"
                 else "Seleccione un tipo de objeto para mostrar todos los objetos de ese tipo")
        ttk.Label(self.scrollable_frame, text=texto,
                  font=('Arial', 12), foreground='gray').pack(pady=50)

    def mostrar_comentarios_tablas(self):
        if not self.tablas_con_comentarios:
            self.crear_mensaje_inicial()
            return
        self._render_objetos_grid(
            "Comentarios de Tablas",
            f"({len(self.tablas_con_comentarios)} tablas)",
            self.tablas_con_comentarios,
            key_prefix='tabla_',
            obj_label='Tabla',
        )
        print(f"Comentarios de tablas mostrados: {len(self.tablas_con_comentarios)} tablas")

    def cargar_campos_tabla(self, tabla: str):
        campos_info = self.obtener_campos_tabla(tabla)
        if not campos_info:
            messagebox.showwarning("Sin Campos",
                f"No se encontraron campos en la tabla '{tabla}'")
            return
        self.tabla_actual = tabla
        self.campos_actuales = campos_info
        self.limpiar_frame_campos()

        header_frame = ttk.Frame(self.scrollable_frame)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        ttk.Label(header_frame, text=f"Tabla: {tabla}", font=('Arial', 14, 'bold'),
                  foreground='#2c3e50').pack(side=tk.LEFT)
        ttk.Label(header_frame, text=f"({len(campos_info)} campos)", font=('Arial', 10),
                  foreground='gray').pack(side=tk.LEFT, padx=10)

        grid_frame = ttk.Frame(self.scrollable_frame)
        grid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        for col, (text, width) in enumerate([("Campo", 30), ("Tipo de Dato", 25),
                                              ("Comentario", 70)]):
            ttk.Label(grid_frame, text=text, font=('Arial', 10, 'bold'),
                      width=width, anchor='w').grid(row=0, column=col,
                                                    padx=5, pady=5, sticky='w')
        ttk.Separator(grid_frame, orient='horizontal').grid(
            row=1, column=0, columnspan=3, sticky='ew', pady=5)

        for idx, (campo, tipo, comentario) in enumerate(campos_info, start=2):
            bg = '#e8f4f8' if idx % 2 == 0 else '#e8f5e9'
            tk.Label(grid_frame, text=campo, width=30, anchor='w',
                     font=('Arial', 9), bg=bg).grid(row=idx, column=0,
                                                    padx=5, pady=5, sticky='w')
            tk.Label(grid_frame, text=tipo, width=25, anchor='w', foreground='gray',
                     font=('Arial', 9), bg=bg).grid(row=idx, column=1,
                                                    padx=5, pady=5, sticky='w')
            entry = tk.Text(grid_frame, width=70, height=3, wrap=tk.WORD,
                            font=('Arial', 9), relief='solid', borderwidth=1, bg=bg)
            entry.grid(row=idx, column=2, padx=5, pady=5, sticky='ew')
            if comentario:
                entry.insert('1.0', comentario)
            self.widgets_comentarios[campo] = entry
        print(f"Tabla '{tabla}' cargada con {len(campos_info)} campos")

    # ── Event handlers ────────────────────────────────────────────────────────

    def cambiar_modo(self):
        self.modo_actual = self.modo_var.get()
        if self.modo_actual == "tablas":
            self.tipo_objeto_frame.pack_forget()
            self.selector_frame.pack(side=tk.TOP, fill=tk.X, before=self.main_frame)
            self.combo_items['values'] = self.tablas_nombres
            self.item_var.set('')
            self.limpiar_frame_campos()
            self.mostrar_comentarios_tablas()
        else:
            self.tipo_objeto_frame.pack(side=tk.TOP, fill=tk.X, before=self.selector_frame)
            self.selector_frame.pack_forget()
            self.tipo_objeto_var.set('')
            self.limpiar_frame_campos()
            self.crear_mensaje_inicial()

    def on_tipo_objeto_seleccionado(self, event):
        self.tipo_objeto_actual = self.tipo_objeto_var.get()
        self.cargar_todos_objetos_tipo(self.tipo_objeto_actual)

    def on_item_seleccionado(self, event):
        if self.modo_actual == "tablas":
            tabla = self.item_var.get()
            if tabla:
                self.cargar_campos_tabla(tabla)

    # ── Saving ────────────────────────────────────────────────────────────────

    def guardar_comentarios(self):
        if self.modo_actual == "tablas":
            self.guardar_comentarios_tabla()
        else:
            self.guardar_comentarios_objetos()

    def guardar_comentarios_tabla(self):
        try:
            # Table-level view (no specific table selected)
            if self.tablas_con_comentarios and not self.tabla_actual:
                count = 0
                for nombre_tabla, comentario_original in self.tablas_con_comentarios:
                    w = self.widgets_comentarios.get(f'tabla_{nombre_tabla}')
                    if not w:
                        continue
                    nuevo = w.get('1.0', tk.END).strip()
                    if nuevo != comentario_original:
                        self._exec_comment(f"TABLE {self.schema}.{nombre_tabla}", nuevo)
                        count += 1
                if count:
                    messagebox.showinfo("Éxito",
                        f"Se guardaron {count} comentarios de tablas")
                    self.cargar_tablas()
                    self.limpiar_frame_campos()
                    self.mostrar_comentarios_tablas()
                else:
                    messagebox.showinfo("Sin Cambios",
                        "No hay comentarios nuevos o modificados en las tablas")
                return

            # Field-level view (specific table selected)
            if not self.tabla_actual:
                messagebox.showwarning("Sin Tabla",
                    "Seleccione una tabla para guardar comentarios de campos")
                return
            count = 0
            for campo, _, comentario_original in self.campos_actuales:
                w = self.widgets_comentarios.get(campo)
                if not w:
                    continue
                nuevo = w.get('1.0', tk.END).strip()
                if nuevo != comentario_original:
                    self._exec_comment(
                        f"COLUMN {self.schema}.{self.tabla_actual}.{campo}", nuevo)
                    count += 1
            if count:
                messagebox.showinfo("Éxito",
                    f"Se guardaron {count} comentarios en la tabla '{self.tabla_actual}'")
                self.cargar_campos_tabla(self.tabla_actual)
            else:
                messagebox.showinfo("Sin Cambios",
                    f"No hay comentarios nuevos o modificados en la tabla '{self.tabla_actual}'")
        except Exception as e:
            messagebox.showerror("Error", f"Error al guardar comentarios:\n{e}")

    def guardar_comentarios_objetos(self):
        if not self.tipo_objeto_actual or not self.objetos_actuales:
            messagebox.showwarning("Sin Objetos", "Seleccione un tipo de objeto primero")
            return
        try:
            count = 0
            for nombre, comentario_original in self.objetos_actuales:
                w = self.widgets_comentarios.get(nombre)
                if not w:
                    continue
                nuevo = w.get('1.0', tk.END).strip()
                if nuevo != comentario_original:
                    self.aplicar_comentario_a_objeto(nombre, self.tipo_objeto_actual, nuevo)
                    count += 1
            if count:
                messagebox.showinfo("Éxito",
                    f"Se guardaron {count} comentarios en {self.tipo_objeto_actual.lower()}")
                self.cargar_todos_objetos_tipo(self.tipo_objeto_actual)
            else:
                messagebox.showinfo("Sin Cambios",
                    f"No hay comentarios nuevos o modificados en "
                    f"{self.tipo_objeto_actual.lower()}")
        except Exception as e:
            messagebox.showerror("Error",
                f"Error al guardar comentarios de {self.tipo_objeto_actual.lower()}:\n{e}")

    def aplicar_comentario_a_objeto(self, nombre: str, tipo: str, comentario: str):
        if tipo == "Jobs":
            messagebox.showwarning("No Soportado",
                "La edición de comentarios en Jobs no está soportada.\n"
                "Use la extensión pg_cron para gestionar jobs.")
            return
        if tipo == "Triggers":
            tabla = self._tabla_para_trigger(nombre)
            self._exec_comment(f"TRIGGER {nombre} ON {self.schema}.{tabla}", comentario)
        elif tipo == "Constraints":
            tabla = self._tabla_para_constraint(nombre)
            self._exec_comment(f"CONSTRAINT {nombre} ON {self.schema}.{tabla}", comentario)
        elif tipo == "Foreign Servers":
            self._exec_comment(f"SERVER {nombre}", comentario)
        elif tipo in _COMMENT_TARGET:
            self._exec_comment(f"{_COMMENT_TARGET[tipo]} {self.schema}.{nombre}", comentario)
        else:
            raise Exception(f"Tipo de objeto no soportado: {tipo}")
        print(f"Comentario actualizado: {tipo.lower()} {nombre}")

    # ── SQL generation ────────────────────────────────────────────────────────

    def _sql_valor(self, comentario: str) -> str:
        """Returns SQL string literal or NULL for a comment value."""
        return f"'{comentario.replace(chr(39), chr(39)*2)}'" if comentario else "NULL"

    def _generar_sql_para_objeto(self, nombre: str, comentario: str, tipo: str) -> str:
        val = self._sql_valor(comentario)
        try:
            if tipo == "Triggers":
                tabla = self._tabla_para_trigger(nombre)
                return (f"COMMENT ON TRIGGER {nombre} ON "
                        f"{self.schema}.{tabla} IS {val};")
            if tipo == "Constraints":
                tabla = self._tabla_para_constraint(nombre)
                return (f"COMMENT ON CONSTRAINT {nombre} ON "
                        f"{self.schema}.{tabla} IS {val};")
            if tipo == "Foreign Servers":
                return f"COMMENT ON SERVER {nombre} IS {val};"
            if tipo == "Jobs":
                return f"-- Jobs: comentarios no soportados ('{nombre}')"
            if tipo in _COMMENT_TARGET:
                return (f"COMMENT ON {_COMMENT_TARGET[tipo]} "
                        f"{self.schema}.{nombre} IS {val};")
        except Exception as e:
            return f"-- Error generando SQL para {nombre}: {e}"
        return ""

    def _generar_sql_script(self, solo_cambios: bool):
        """Generates and shows a SQL script with all or only modified comments."""
        titulo = "SOLO CAMBIOS" if solo_cambios else "TODOS LOS COMENTARIOS"
        sql_lines = [
            f"-- Script de comentarios - {titulo}",
            f"-- Base de datos: {self.database}",
            f"-- Esquema: {self.schema}",
            f"-- Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]
        cambios_count = 0

        if self.modo_actual == "tablas":
            if self.tabla_actual:
                sql_lines += [f"-- Comentarios campos: {self.tabla_actual}", ""]
                for campo, _, comentario_orig in self.campos_actuales:
                    w = self.widgets_comentarios.get(campo)
                    if not w:
                        continue
                    comentario = w.get('1.0', tk.END).strip()
                    if solo_cambios and comentario == comentario_orig:
                        continue
                    cambios_count += 1
                    sql_lines.append(
                        f"COMMENT ON COLUMN {self.schema}.{self.tabla_actual}.{campo}"
                        f" IS {self._sql_valor(comentario)};")
            else:
                sql_lines += ["-- Comentarios tablas", ""]
                for nombre_tabla, comentario_orig in self.tablas_con_comentarios:
                    w = self.widgets_comentarios.get(f'tabla_{nombre_tabla}')
                    if not w:
                        continue
                    comentario = w.get('1.0', tk.END).strip()
                    if solo_cambios and comentario == comentario_orig:
                        continue
                    cambios_count += 1
                    sql_lines.append(
                        f"COMMENT ON TABLE {self.schema}.{nombre_tabla}"
                        f" IS {self._sql_valor(comentario)};")
        else:
            if not self.tipo_objeto_actual or not self.objetos_actuales:
                messagebox.showwarning("Sin Objetos", "Seleccione un tipo de objeto primero")
                return
            sql_lines += [f"-- Comentarios {self.tipo_objeto_actual}", ""]
            for nombre, comentario_orig in self.objetos_actuales:
                w = self.widgets_comentarios.get(nombre)
                if not w:
                    continue
                comentario = w.get('1.0', tk.END).strip()
                if solo_cambios and comentario == comentario_orig:
                    continue
                cambios_count += 1
                cmd = self._generar_sql_para_objeto(
                    nombre, comentario, self.tipo_objeto_actual)
                if cmd:
                    sql_lines.append(cmd)

        if solo_cambios and cambios_count == 0:
            messagebox.showinfo("Sin Cambios",
                "No hay comentarios modificados para generar SQL")
            return

        sql_lines.append("")
        if solo_cambios:
            sql_lines.append(f"-- Total de cambios: {cambios_count}")
        sql_lines.append("-- Fin del script")
        self._mostrar_ventana_sql("\n".join(sql_lines))

    def _mostrar_ventana_sql(self, sql_content: str):
        win = tk.Toplevel(self.root)
        win.title("Script SQL de Comentarios")
        win.geometry("900x600")

        btn_frame = ttk.Frame(win, padding=10)
        btn_frame.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(btn_frame, text="Script SQL Generado:",
                  font=('Arial', 11, 'bold')).pack(side=tk.LEFT, padx=5)

        def copiar():
            win.clipboard_clear()
            win.clipboard_append(sql_content)
            messagebox.showinfo("Copiado", "El script SQL ha sido copiado al portapapeles")

        def guardar():
            archivo = filedialog.asksaveasfilename(
                defaultextension=".sql",
                filetypes=[("SQL files", "*.sql"), ("All files", "*.*")],
                title="Guardar script SQL",
            )
            if archivo:
                try:
                    with open(archivo, 'w', encoding='utf-8') as f:
                        f.write(sql_content)
                    messagebox.showinfo("Éxito", f"Script guardado en:\n{archivo}")
                except Exception as e:
                    messagebox.showerror("Error", f"Error al guardar el archivo:\n{e}")

        ttk.Button(btn_frame, text="Copiar", command=copiar).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Guardar", command=guardar).pack(side=tk.RIGHT, padx=5)

        text_frame = ttk.Frame(win)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        sql_text = scrolledtext.ScrolledText(text_frame, font=("Courier New", 10), wrap=tk.WORD)
        sql_text.pack(fill=tk.BOTH, expand=True)
        sql_text.insert('1.0', sql_content)

    # ── Misc ──────────────────────────────────────────────────────────────────

    def recargar_actual(self):
        if self.modo_actual == "tablas":
            if self.tabla_actual:
                self.cargar_campos_tabla(self.tabla_actual)
            else:
                self.cargar_tablas()
                self.limpiar_frame_campos()
                self.mostrar_comentarios_tablas()
        else:
            if not self.tipo_objeto_actual:
                messagebox.showwarning("Sin Tipo", "Seleccione un tipo de objeto primero")
                return
            self.cargar_todos_objetos_tipo(self.tipo_objeto_actual)
            messagebox.showinfo("Recargado",
                f"{self.tipo_objeto_actual} recargados correctamente")

    def cerrar(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        self.root.quit()
        self.root.destroy()

    def ejecutar(self):
        try:
            self.root.protocol("WM_DELETE_WINDOW", self.cerrar)
            self.root.mainloop()
        except Exception as e:
            if "application has been destroyed" not in str(e):
                raise


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    if len(sys.argv) != 7:
        print("Uso: python agregar_comentarios.py "
              "<host> <puerto> <bd> <usuario> <password> <esquema>")
        sys.exit(1)

    host, puerto, bd, usuario, password, esquema = sys.argv[1:]
    print(f"Iniciando interfaz de comentarios — {bd}@{host}:{puerto} (esquema: {esquema})")
    try:
        app = ComentariosGUI(host, puerto, bd, usuario, password, esquema)
        app.ejecutar()
        print("Aplicacion cerrada correctamente")
    except Exception as e:
        print(f"\nError fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
