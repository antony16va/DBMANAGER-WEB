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
        self.root.geometry("1000x800")
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
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('Module.TButton', font=('Arial', 10, 'bold'), padding=10)
        style.configure('Execute.TButton', font=('Arial', 10, 'bold'), padding=8)
        # Style for top-right control buttons
        style.configure('Top.TButton', font=('Arial', 10), padding=6)
        
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        title_frame = ttk.Frame(main_container)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(title_frame, text="ARQUITECTURA DE BASE DE DATOS", 
             font=('Arial', 18, 'bold')).pack(side=tk.LEFT)

        # Right-side small control buttons grouped to avoid hugging the absolute edge
        right_buttons_frame = ttk.Frame(title_frame)
        right_buttons_frame.pack(side=tk.RIGHT, padx=8, pady=5)

        ttk.Button(right_buttons_frame, text="Historial", 
              command=self.show_history, style='Top.TButton', width=14).pack(side=tk.RIGHT, padx=5)
        ttk.Button(right_buttons_frame, text="Validar Requisitos", 
              command=self.check_requirements, style='Top.TButton', width=18).pack(side=tk.RIGHT, padx=5)
        
        content_frame = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        left_panel = ttk.Frame(content_frame)
        content_frame.add(left_panel, weight=2)
        
        modules_frame = ttk.LabelFrame(left_panel, text="   Modulos", padding=10)
        modules_frame.pack(fill=tk.BOTH, expand=True)
        
        self.modules = [
            {
                "id": 1,
                "name": "GENERAR DDL INICIAL",
                "script": str(self.modules_dir / "generar_ddl_inicial.py"),
                "type": "python",
                "icon": "*",
                "params": ["ruta_plantilla_excel", "ruta_salida_ddl_base"]
            },
            {
                "id": 2,
                "name": "VALIDAR NOMENCLATURA",
                "script": str(self.modules_dir / "validar_nomenclatura.py"),
                "type": "python",
                "icon": "*",
                "params": ["host", "puerto", "bd", "usuario", "password", "ruta_salida_ddl_completo"]
            },
            {
                "id": 3,
                "name": "DICCIONARIO DE DATOS",
                "script": str(self.modules_dir / "generar_diccionario.py"),
                "type": "python",
                "icon": "*",
                "params": ["host", "puerto", "bd", "usuario", "password", "esquema", "ruta_salida_rtf"]
            },
            {
                "id": 4,
                "name": "DATA DE PRUEBA",
                "script": str(self.modules_dir / "data_prueba.py"),
                "type": "python",
                "icon": "*",
                "params": ["host", "puerto", "bd", "usuario", "password", "esquema", "cantidad_registros"]
            },
            {
                "id": 5,
                "name": "DASHBOARD",
                "script": str(self.modules_dir / "dashboard" / "extraer_metadata_overview.py"),
                "type": "python",
                "icon": "*",
                "params": ["ruta_ddl_completo"]
            }
        ]
        self.module_buttons = []
        for module in self.modules:
            self.create_module_card(modules_frame, module)
        
        right_panel = ttk.Frame(content_frame)
        content_frame.add(right_panel, weight=3)
        
        config_frame = ttk.LabelFrame(right_panel, text="Configuracion del Modulo", padding=10)
        config_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.module_name_var = tk.StringVar(value="Parametros")
        ttk.Label(config_frame, textvariable=self.module_name_var, 
                 font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=(0, 10))
        
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
        
        self.param_widgets = {}
        
        btn_frame = ttk.Frame(config_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        # Use grid so buttons expand evenly and share the same style
        save_btn = ttk.Button(btn_frame, text=" Guardar Configuracion", 
                              command=self.save_module_config, style='Execute.TButton')
        exec_btn = ttk.Button(btn_frame, text=" Ejecutar Modulo", 
                              command=self.execute_current_module, style='Execute.TButton')
        stop_btn = ttk.Button(btn_frame, text=" Detener", 
                              command=self.stop_execution, style='Execute.TButton')

        save_btn.grid(row=0, column=0, sticky='ew', padx=5)
        exec_btn.grid(row=0, column=1, sticky='ew', padx=5)
        stop_btn.grid(row=0, column=2, sticky='ew', padx=5)

        for i in range(3):
            btn_frame.columnconfigure(i, weight=1)
        
        console_frame = ttk.LabelFrame(right_panel, text="Consola de Ejecucion", padding=5)
        console_frame.pack(fill=tk.BOTH, expand=True)
        
        console_btn_frame = ttk.Frame(console_frame)
        console_btn_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(console_btn_frame, text=" Limpiar", 
                  command=self.clear_console).pack(side=tk.LEFT, padx=5)
        ttk.Button(console_btn_frame, text=" Guardar Log", 
                  command=self.save_log).pack(side=tk.LEFT, padx=5)
        
        self.console_text = scrolledtext.ScrolledText(console_frame, font=("Consolas", 9), 
                                                      bg="#1e1e1e", fg="#d4d4d4", 
                                                      insertbackground="white", wrap=tk.WORD)
        self.console_text.pack(fill=tk.BOTH, expand=True)
        
        self.console_text.tag_config("info", foreground="#4ec9b0")
        self.console_text.tag_config("error", foreground="#f48771")
        self.console_text.tag_config("success", foreground="#b5cea8")
        self.console_text.tag_config("warning", foreground="#dcdcaa")
        self.console_text.tag_config("module", foreground="#569cd6")
        
    def create_module_card(self, parent, module):
        card = ttk.Frame(parent, relief=tk.RAISED, borderwidth=2)
        card.pack(fill=tk.X, pady=5, padx=5)
        
        header = ttk.Frame(card)
        header.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(header, text=f"{module['icon']} Modulo {module['id']}", 
                 font=('Arial', 10, 'bold')).pack(side=tk.LEFT)
        
        type_label = ttk.Label(header, text=f"[{module['type'].upper()}]", 
                              font=('Arial', 8), foreground='gray')
        type_label.pack(side=tk.RIGHT)
        
        ttk.Label(card, text=module['name'], font=('Arial', 11)).pack(anchor=tk.W, padx=10)
        
        btn = ttk.Button(card, text=" Configurar y Ejecutar", 
                        command=lambda m=module: self.select_module(m),
                        style='Module.TButton')
        btn.pack(fill=tk.X, padx=10, pady=(5, 10))
        
        self.module_buttons.append(btn)
        
    def select_module(self, module):
        self.selected_module = module
        self.module_name_var.set(f"{module['icon']} {module['name']}")
        
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        
        self.param_widgets.clear()
        
        ttk.Label(self.params_frame, text="Script cargado:", 
                 font=('Arial', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Label(self.params_frame, text=module['script']).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Separator(self.params_frame, orient='horizontal').grid(row=1, column=0, columnspan=3, 
                                                                   sticky='ew', pady=10)
        
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
            ttk.Label(self.params_frame, text=label_text, 
                     font=('Arial', 9)).grid(row=row, column=0, sticky=tk.W, pady=5, padx=(0, 10))
            
            if 'ruta' in param.lower():
                frame = ttk.Frame(self.params_frame)
                frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
                
                var = tk.StringVar()
                entry = ttk.Entry(frame, textvariable=var, width=50)
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                is_input = 'plantilla' in param.lower() or ('ddl' in param.lower() and 'salida' not in param.lower())
                btn = ttk.Button(frame, text="", width=3,
                               command=lambda v=var, p=param: self.browse_path(v, p))
                btn.pack(side=tk.LEFT, padx=(5, 0))
                
                self.param_widgets[param] = var
            elif param == 'password':
                var = tk.StringVar()
                entry = ttk.Entry(self.params_frame, textvariable=var, show="*", width=50)
                entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
                self.param_widgets[param] = var
            else:
                var = tk.StringVar()
                entry = ttk.Entry(self.params_frame, textvariable=var, width=50)
                entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
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
