import tkinter as tk
from tkinter import ttk, messagebox
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from data_prueba import SmartDataGenerator

class DataPruebaGUI:

    def __init__(self, root, host, puerto, bd, usuario, password, esquema):
        self.root     = root
        self.root.title(f"Generación de Data - {esquema} @ {bd}")
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
        self.columna_widgets         = {}
        self.proceso_activo          = False
        self.cantidad_base_default   = 100
        self.setup_ui()
        self.inicializar_generador()

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _add_spinrow(self, parent, label, var, **kw):
        f = ttk.Frame(parent)
        f.pack(fill=tk.X, pady=3, padx=5)
        ttk.Label(f, text=label, font=('Arial', 9)).pack(side=tk.LEFT)
        tk.Spinbox(f, textvariable=var, width=12, font=('Arial', 9), **kw).pack(side=tk.RIGHT)

    # ── UI Setup ──────────────────────────────────────────────────────────────
    def setup_ui(self):
        info_frame = ttk.Frame(self.root, padding="10")
        info_frame.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(info_frame, text=f"Base de datos: {self.bd}",
                  font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        ttk.Label(info_frame, text=f"Esquema: {self.esquema}",
                  font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)

        header_panel = ttk.Frame(self.root, padding="10")
        header_panel.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(header_panel, text="Seleccionar Tablas",
                  font=('Arial', 11, 'bold')).pack(side=tk.LEFT, padx=5)
        ttk.Button(header_panel, text="Ninguna",
                   command=self.deseleccionar_todas).pack(side=tk.RIGHT, padx=2)
        ttk.Button(header_panel, text="Todas",
                   command=self.seleccionar_todas).pack(side=tk.RIGHT, padx=2)

        ttk.Separator(self.root, orient='horizontal').pack(fill=tk.X, padx=10)

        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        canvas    = tk.Canvas(self.main_frame, bg='white')
        scrollbar = ttk.Scrollbar(self.main_frame, orient="vertical", command=canvas.yview)
        self.tabla_frame = ttk.Frame(canvas)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas_window = canvas.create_window((0, 0), window=self.tabla_frame, anchor="nw")

        def configure_scroll(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(canvas_window, width=event.width)
        self.tabla_frame.bind("<Configure>", configure_scroll)
        canvas.bind("<Configure>", configure_scroll)
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        action_frame = ttk.Frame(self.root, padding="10")
        action_frame.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Separator(action_frame, orient='horizontal').pack(fill=tk.X, pady=(0, 8))
        self.limpiar_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(action_frame, text="Limpiar tablas antes de insertar",
                        variable=self.limpiar_var).pack(anchor=tk.W, pady=(0, 5))
        self.btn_ejecutar = ttk.Button(action_frame, text="GENERAR DATOS",
                                       command=self.ejecutar_generacion)
        self.btn_ejecutar.pack(fill=tk.X)

    # ── Inicialización y análisis ─────────────────────────────────────────────
    def inicializar_generador(self):
        try:
            self.generator = SmartDataGenerator(
                self.host, self.puerto, self.bd,
                self.usuario, self.password, self.esquema
            )
            if not self.generator.conectar():
                messagebox.showerror("Error de Conexión", "No se pudo conectar a la base de datos")
                self.root.destroy()
                return
            self.cantidad_base_default = self.generator.config.get('cantidad_base', 100)
            threading.Thread(target=self._analizar_bd_thread, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Error al inicializar: {e}")
            self.root.destroy()

    def _analizar_bd_thread(self):
        try:
            self.generator.analizar_base_datos()
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Error en análisis: {e}"))
        else:
            self.root.after(0, self.crear_controles_tablas)

    def crear_controles_tablas(self):
        orden_carga = self.generator.metadata['orden_carga']
        for i, tabla in enumerate(orden_carga, 1):
            self.crear_control_tabla(i, tabla)

    # ── Controles de tabla ────────────────────────────────────────────────────
    def crear_control_tabla(self, numero, tabla):
        container_frame = ttk.Frame(self.tabla_frame, relief='solid', borderwidth=1)
        container_frame.pack(fill=tk.X, pady=2, padx=5)
        header_frame = ttk.Frame(container_frame)
        header_frame.pack(fill=tk.X, padx=8, pady=5)

        self.tabla_expanded[tabla] = tk.BooleanVar(value=False)
        expand_btn = ttk.Button(header_frame, text="▶", width=2,
                                command=lambda t=tabla, c=container_frame: self._toggle_columnas(t, c))
        expand_btn.pack(side=tk.LEFT, padx=(0, 5))

        var_check = tk.BooleanVar(value=True)
        ttk.Checkbutton(header_frame, variable=var_check).pack(side=tk.LEFT)

        nombre_frame = ttk.Frame(header_frame)
        nombre_frame.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        ttk.Label(nombre_frame, text=f"{numero}.",
                  font=('Arial', 9), foreground='gray').pack(side=tk.LEFT)
        ttk.Label(nombre_frame, text=tabla,
                  font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=5)
        info_text = self._get_tabla_info(tabla)
        if info_text:
            ttk.Label(nombre_frame, text=info_text,
                      font=('Arial', 8), foreground='gray').pack(side=tk.LEFT, padx=5)

        cantidad_frame = ttk.Frame(header_frame)
        cantidad_frame.pack(side=tk.RIGHT)
        ttk.Label(cantidad_frame, text="Registros:",
                  font=('Arial', 9)).pack(side=tk.LEFT, padx=(0, 5))
        var_cantidad = tk.IntVar(value=self._calcular_cantidad_inicial(tabla))
        tk.Spinbox(cantidad_frame, from_=1, to=100000, textvariable=var_cantidad,
                   width=8, font=('Arial', 9)).pack(side=tk.LEFT)

        columnas_frame = ttk.Frame(container_frame)
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
        for col_info in self.generator.metadata['columnas'][tabla]:
            self._crear_control_columna(columnas_frame, tabla, col_info)

    def _crear_control_columna(self, parent, tabla, col_info):
        col_container = ttk.Frame(parent)
        col_container.pack(fill=tk.X, padx=5, pady=1)
        col_header = ttk.Frame(col_container)
        col_header.pack(fill=tk.X, padx=8, pady=3)

        col_key      = f"{tabla}.{col_info['nombre']}"
        config_frame = ttk.Frame(col_container)

        expand_btn = ttk.Button(col_header, text="▶", width=2,
                                command=lambda k=col_key: self._toggle_config_columna(k))
        expand_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.columna_widgets[col_key] = (expand_btn, config_frame)

        ttk.Label(col_header, text=col_info['nombre'],
                  font=('Arial', 9, 'bold')).pack(side=tk.LEFT)

        tipo_display = col_info['udt_name'] or col_info['tipo_dato']
        if col_info.get('max_length'):
            tipo_display = f"{tipo_display}({col_info['max_length']})"
        ttk.Label(col_header, text=tipo_display,
                  font=('Arial', 8), foreground='gray').pack(side=tk.LEFT, padx=10)

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
            ttk.Label(col_header, text=' | '.join(indicadores),
                      font=('Arial', 8, 'bold'), foreground='gray').pack(side=tk.LEFT, padx=5)
        if col_key in self.columnas_personalizadas:
            ttk.Label(col_header, text="Personalizado",
                      font=('Arial', 8, 'bold')).pack(side=tk.LEFT, padx=10)

    def _toggle_config_columna(self, col_key):
        if col_key not in self.columna_widgets:
            return
        expand_btn, config_frame = self.columna_widgets[col_key]
        tabla, col_nombre = col_key.split('.', 1)
        col_info = next(
            (c for c in self.generator.metadata['columnas'].get(tabla, [])
             if c['nombre'] == col_nombre), None)
        if not col_info:
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
            pass

    # ── Panel de configuración de columna ─────────────────────────────────────
    def _crear_panel_config_columna(self, parent, tabla, col_info):
        col_nombre = col_info['nombre']
        col_tipo   = (col_info['udt_name'] or col_info['tipo_dato']).lower()
        col_key    = f"{tabla}.{col_nombre}"

        config_area = ttk.Frame(parent)
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
            ttk.Label(config_area, text=f"Tipo '{col_tipo}' no soportado",
                      font=('Arial', 9)).pack(pady=10)
            return

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
        self._add_spinrow(parent, "Min:",       config_vars['min'],
                          from_=-999999999, to=999999999, increment=0.01)
        self._add_spinrow(parent, "Max:",       config_vars['max'],
                          from_=-999999999, to=999999999, increment=0.01)
        self._add_spinrow(parent, "Decimales:", config_vars['decimales'], from_=0, to=10)

    def _crear_controles_text(self, parent, col_info, col_key, config_vars):
        config_actual = self.columnas_personalizadas.get(col_key, {}).get('config', {})
        texto_config  = self.generator.config.get('texto', {})
        max_len       = col_info.get('max_length') or texto_config.get('max_length_text', 50)
        config_vars['longitud'] = tk.IntVar(value=config_actual.get('longitud', max_len))
        self._add_spinrow(parent, "Longitud:", config_vars['longitud'], from_=1, to=5000)
        if self.generator and self.generator.faker:
            config_vars['usar_faker'] = tk.BooleanVar(value=config_actual.get('usar_faker', False))
            ttk.Checkbutton(parent, text="Usar Faker (texto realista)",
                            variable=config_vars['usar_faker']).pack(anchor=tk.W, pady=5, padx=5)

    def _crear_controles_date(self, parent, col_info, col_key, config_vars):
        config_actual = self.columnas_personalizadas.get(col_key, {}).get('config', {})
        for key, label, default in [('fecha_inicio', 'Desde:', '2020-01-01'),
                                    ('fecha_fin',    'Hasta:', '2025-12-31')]:
            f = ttk.Frame(parent)
            f.pack(fill=tk.X, pady=3, padx=5)
            ttk.Label(f, text=label, font=('Arial', 9)).pack(side=tk.LEFT)
            config_vars[key] = tk.StringVar(value=config_actual.get(key, default))
            tk.Entry(f, textvariable=config_vars[key], width=12,
                     font=('Arial', 9)).pack(side=tk.RIGHT)

    def _crear_controles_boolean(self, parent, col_info, col_key, config_vars):
        config_actual = self.columnas_personalizadas.get(col_key, {}).get('config', {})
        config_vars['prob_true'] = tk.DoubleVar(value=config_actual.get('prob_true', 0.5))
        self._add_spinrow(parent, "Prob. True:", config_vars['prob_true'],
                          from_=0.0, to=1.0, increment=0.05)
        ttk.Label(parent, text="(ej: 0.8 = 80% True)",
                  font=('Arial', 8), foreground='gray').pack(anchor=tk.W, pady=3, padx=5)

    def _refrescar_indicador_columna(self, tabla, col_nombre):
        if tabla not in self.tabla_vars:
            return
        _, _, _, columnas_frame = self.tabla_vars[tabla]
        if self.tabla_expanded[tabla].get():
            keys_to_remove = [k for k in self.columna_widgets if k.startswith(f"{tabla}.")]
            for k in keys_to_remove:
                del self.columna_widgets[k]
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
            mensaje += "\n\n[ADVERTENCIA] Se limpiarán las tablas antes de insertar"
        if not messagebox.askyesno("Confirmar", mensaje):
            return
        self.btn_ejecutar.config(state=tk.DISABLED, text="GENERANDO...")
        self.proceso_activo = True
        threading.Thread(target=self._generar_datos_thread,
                         args=(tablas_seleccionadas,), daemon=True).start()

    def _aplicar_config_desde_ui(self):
        self.generator.config['columnas_personalizadas'] = self.columnas_personalizadas.copy()

    def _generar_datos_thread(self, tablas_seleccionadas):
        try:
            orden_carga      = self.generator.metadata['orden_carga']
            tablas_dict      = dict(tablas_seleccionadas)
            tablas_ordenadas = [(t, tablas_dict[t]) for t in orden_carga if t in tablas_dict]

            if self.limpiar_var.get():
                for tabla, _ in reversed(tablas_ordenadas):
                    try:
                        self.generator.cursor.execute(
                            f'TRUNCATE TABLE {self.esquema}.{tabla} CASCADE')
                        self.generator.conn.commit()
                    except Exception as e:
                        self.generator.conn.rollback()

            errores = []
            total_insertados = 0
            for tabla, cantidad in tablas_ordenadas:
                try:
                    registros  = self.generator.generar_registros_tabla(tabla, cantidad)
                    insertados = self.generator.insertar_registros(tabla, registros)
                    total_insertados += insertados
                except Exception as e:
                    errores.append(f"{tabla}: {e}")

            resumen = f"Generación completada\n\nTotal de registros: {total_insertados:,}"
            if errores:
                resumen += f"\n\nErrores en {len(errores)} tabla(s):\n" + "\n".join(errores)
            self.root.after(0, lambda: messagebox.showinfo("Completado", resumen))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(
                "Error", f"Error durante la generación: {e}"))
        finally:
            self.root.after(0, lambda: self.btn_ejecutar.config(
                state=tk.NORMAL, text="GENERAR DATOS"))
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
