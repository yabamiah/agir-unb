"""
Gerenciador de Workers Adaptativo - Módulo DANI
Otimiza o paralelismo baseado no tipo de tarefa e recursos disponíveis do sistema.
"""

import time
import psutil
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Dict

# Flags de disponibilidade de bibliotecas PDF (importadas do módulo principal ou definidas aqui)
try:
    import pymupdf as fitz
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False


class AdaptiveWorkerManager:
    """
    Gerenciador de workers adaptativo que otimiza o paralelismo baseado no tipo de tarefa
    e recursos disponíveis do sistema.
    """
    
    def __init__(self, logger):
        self.logger = logger
        self.system_info = self._get_system_info()
        self.worker_pools = {}
        self.performance_metrics = {}
        
    def _get_system_info(self) -> Dict:
        """Coleta informações do sistema para otimização."""
        try:
            cpu_count_physical = psutil.cpu_count(logical=False)
            cpu_count_logical = psutil.cpu_count(logical=True)
            memory_gb = psutil.virtual_memory().total / (1024**3)
            
            return {
                'cpu_physical': cpu_count_physical or 2,
                'cpu_logical': cpu_count_logical or 4,
                'memory_gb': memory_gb,
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory_percent': psutil.virtual_memory().percent
            }
        except Exception as e:
            self.logger.warning(f"Erro ao coletar info do sistema: {e}")
            return {
                'cpu_physical': 2,
                'cpu_logical': 4,
                'memory_gb': 8.0,
                'cpu_percent': 50.0,
                'memory_percent': 50.0
            }
    
    def get_optimal_workers(self, task_type: str, task_count: int = 1) -> int:
        """
        Calcula o número ótimo de workers baseado no tipo de tarefa e recursos.
        
        Args:
            task_type: Tipo de tarefa ('pdf_extraction', 'text_processing', 'file_io', 'network_io')
            task_count: Quantidade de tarefas a serem processadas
            
        Returns:
            Número ótimo de workers
        """
        base_workers = self.system_info['cpu_logical']
        
        if task_type == 'pdf_extraction':
            if PYMUPDF_AVAILABLE or PDFPLUMBER_AVAILABLE:
                optimal = min(base_workers * 2, task_count, 16)
            else:
                optimal = min(base_workers, task_count, 8)
                
        elif task_type == 'text_processing':
            optimal = min(base_workers, task_count, 12)
            
        elif task_type == 'file_io':
            optimal = min(base_workers * 3, task_count, 20)
            
        elif task_type == 'network_io':
            optimal = min(base_workers, task_count, 6)
            
        else:
            optimal = min(base_workers, task_count, 8)
        
        # Ajustar baseado na carga do sistema
        if self.system_info['cpu_percent'] > 80:
            optimal = max(1, optimal // 2)
        elif self.system_info['memory_percent'] > 85:
            optimal = max(1, optimal // 2)
            
        return max(1, optimal)
    
    def get_executor(self, task_type: str, task_count: int = 1, use_processes: bool = False):
        """
        Retorna o executor apropriado para o tipo de tarefa.
        
        Args:
            task_type: Tipo de tarefa
            task_count: Quantidade de tarefas
            use_processes: Se True, usa ProcessPoolExecutor para tarefas CPU-intensive
            
        Returns:
            ThreadPoolExecutor ou ProcessPoolExecutor
        """
        workers = self.get_optimal_workers(task_type, task_count)
        
        if use_processes and task_type in ['text_processing', 'pdf_extraction']:
            return ProcessPoolExecutor(max_workers=min(workers, 4))
        else:
            return ThreadPoolExecutor(max_workers=workers)
    
    def log_performance(self, task_type: str, duration: float, workers_used: int):
        """Registra métricas de performance para otimização futura."""
        if task_type not in self.performance_metrics:
            self.performance_metrics[task_type] = []
        
        self.performance_metrics[task_type].append({
            'duration': duration,
            'workers': workers_used,
            'timestamp': time.time()
        })
        
        # Manter apenas as últimas 100 métricas
        if len(self.performance_metrics[task_type]) > 100:
            self.performance_metrics[task_type] = self.performance_metrics[task_type][-100:]
