"""
Módulo centralizado para gestión de configuración
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """Gestor de configuración unificado"""

    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file
        self.config: Dict[str, Any] = {}

    def load(self) -> Dict[str, Any]:
        """Carga configuración desde archivo JSON"""
        if not self.config_file or not os.path.exists(self.config_file):
            return {}

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            return self.config
        except Exception as e:
            print(f"[WARN] Error cargando configuración: {e}")
            return {}

    def save(self) -> bool:
        """Guarda configuración a archivo JSON"""
        if not self.config_file:
            return False

        try:
            # Crear directorio si no existe
            Path(self.config_file).parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[ERROR] Error guardando configuración: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Obtiene valor de configuración"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """Establece valor de configuración"""
        self.config[key] = value

    def merge(self, updates: Dict[str, Any]):
        """Fusiona configuración con nuevos valores"""
        self._deep_merge(self.config, updates)

    def _deep_merge(self, base: Dict, updates: Dict):
        """Fusión recursiva de diccionarios"""
        for key, value in updates.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
