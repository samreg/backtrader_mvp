"""
Dynamic indicator loader

Loads indicator modules dynamically from visualization/indicators/
based on YAML configuration.
"""

import importlib.util
import sys
from pathlib import Path
from typing import Dict, Any, Type
from core.indicator_base import IndicatorBase


class IndicatorLoader:
    """
    Loads indicators dynamically from module files
    
    Usage:
        loader = IndicatorLoader()
        indicator = loader.load_indicator(
            name='ema_50',
            module_path='visualization/indicators/ema.py',
            params={'period': 50}
        )
    """
    
    def __init__(self, indicators_dir: str = "visualization/indicators"):
        """
        Initialize loader
        
        Args:
            indicators_dir: Directory containing indicator modules
        """
        self.indicators_dir = Path(indicators_dir)
        self._cache: Dict[str, Type[IndicatorBase]] = {}
    
    def load_indicator(
        self,
        name: str,
        module_file: str,
        params: Dict[str, Any],
        timeframe: str = ""
    ) -> IndicatorBase:
        """
        Load and instantiate an indicator
        
        Args:
            name: Indicator instance name
            module_file: Module filename (e.g., 'ema.py')
            params: Parameters dict
            timeframe: Timeframe for this indicator
        
        Returns:
            Instantiated indicator
        
        Raises:
            FileNotFoundError: If module file not found
            AttributeError: If module doesn't have Indicator class
            TypeError: If Indicator class doesn't inherit from IndicatorBase
        """
        # Get indicator class
        indicator_class = self._load_indicator_class(module_file)
        
        # Instantiate
        indicator = indicator_class(params)
        
        # Set metadata
        indicator.name = name
        indicator.timeframe = timeframe
        
        return indicator
    
    def _load_indicator_class(self, module_file: str) -> Type[IndicatorBase]:
        """
        Load indicator class from module file
        
        Args:
            module_file: Module filename
        
        Returns:
            Indicator class
        """
        # Check cache
        if module_file in self._cache:
            return self._cache[module_file]
        
        # Build full path
        module_path = self.indicators_dir / module_file
        
        if not module_path.exists():
            raise FileNotFoundError(
                f"Indicator module not found: {module_path}\n"
                f"Make sure {module_file} exists in {self.indicators_dir}/"
            )
        
        # Load module dynamically
        module_name = module_path.stem
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        
        if spec is None or spec.loader is None:
            raise ImportError(f"Failed to load module: {module_path}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        
        # Find indicator class
        # Convention: Module must have a class named "Indicator"
        if not hasattr(module, 'Indicator'):
            raise AttributeError(
                f"Module {module_file} must define a class named 'Indicator'\n"
                f"Example:\n"
                f"  class Indicator(IndicatorBase):\n"
                f"      def calculate(self, candles):\n"
                f"          ..."
            )
        
        indicator_class = module.Indicator
        
        # Verify it inherits from IndicatorBase
        if not issubclass(indicator_class, IndicatorBase):
            raise TypeError(
                f"Indicator class in {module_file} must inherit from IndicatorBase\n"
                f"Example:\n"
                f"  from core.indicator_base import IndicatorBase\n"
                f"  class Indicator(IndicatorBase):\n"
                f"      ..."
            )
        
        # Cache it
        self._cache[module_file] = indicator_class
        
        return indicator_class
    
    def clear_cache(self):
        """Clear cached indicator classes (useful for development/reload)"""
        self._cache.clear()
