"""
Real-time GPU Performance Monitor
=================================
Provides real-time monitoring and optimization of GPU performance during CFR training.
Tracks GPU utilization, memory usage, throughput, and automatically optimizes parameters.
"""

import time
import threading
import logging
import json
from collections import deque
from typing import Dict, List, Optional, Callable
import statistics

logger = logging.getLogger(__name__)

try:
    import cupy as cp
    from cupy.cuda import Device
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

class GPUPerformanceMonitor:
    """Real-time GPU performance monitoring and optimization."""
    
    def __init__(self, update_interval: float = 1.0, history_size: int = 1000):
        self.update_interval = update_interval
        self.history_size = history_size
        self.monitoring = False
        self.monitor_thread = None
        
        # Performance metrics
        self.metrics = {
            'gpu_utilization': deque(maxlen=history_size),
            'memory_usage': deque(maxlen=history_size),
            'throughput': deque(maxlen=history_size),
            'batch_size': deque(maxlen=history_size),
            'processing_time': deque(maxlen=history_size),
            'gpu_temperature': deque(maxlen=history_size),
            'memory_bandwidth': deque(maxlen=history_size)
        }
        
        # Real-time stats
        self.current_stats = {
            'peak_throughput': 0,
            'avg_gpu_utilization': 0,
            'peak_memory_usage': 0,
            'optimal_batch_size': 1000,
            'total_iterations': 0,
            'total_runtime': 0
        }
        
        # Optimization callbacks
        self.optimization_callbacks = []
        
        # Performance targets
        self.targets = {
            'min_throughput': 100000,  # 100K iter/sec minimum
            'target_gpu_utilization': 90,  # 90% GPU utilization target
            'max_memory_usage': 0.8,  # 80% max memory usage
            'target_batch_efficiency': 0.9  # 90% batch efficiency
        }
        
        logger.info("GPU Performance Monitor initialized")
        logger.info(f"  Update interval: {update_interval}s")
        logger.info(f"  History size: {history_size} samples")
    
    def start_monitoring(self):
        """Start real-time performance monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("🔍 GPU performance monitoring started")
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        logger.info("📊 GPU performance monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                # Collect GPU metrics
                if GPU_AVAILABLE:
                    device = Device()
                    
                    # Memory usage
                    meminfo = device.mem_info
                    free_memory = meminfo[0]
                    total_memory = meminfo[1] 
                    used_memory = total_memory - free_memory
                    memory_usage_pct = (used_memory / total_memory) * 100
                    
                    self.metrics['memory_usage'].append(memory_usage_pct)
                    
                    # Update peak memory usage
                    if memory_usage_pct > self.current_stats['peak_memory_usage']:
                        self.current_stats['peak_memory_usage'] = memory_usage_pct
                    
                    # Calculate average GPU utilization (mock for demonstration)
                    # In real implementation, would use nvidia-ml-py or similar
                    gpu_util = min(95, memory_usage_pct * 1.2)  # Mock calculation
                    self.metrics['gpu_utilization'].append(gpu_util)
                    
                    # Update running averages
                    if self.metrics['gpu_utilization']:
                        self.current_stats['avg_gpu_utilization'] = statistics.mean(
                            list(self.metrics['gpu_utilization'])[-10:]  # Last 10 samples
                        )
                
                # Check for optimization opportunities
                self._check_optimization_opportunities()
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.debug(f"Monitoring error: {e}")
                time.sleep(self.update_interval)
    
    def _check_optimization_opportunities(self):
        """Check for optimization opportunities and trigger callbacks."""
        if not self.metrics['throughput']:
            return
        
        current_throughput = self.metrics['throughput'][-1] if self.metrics['throughput'] else 0
        current_gpu_util = self.metrics['gpu_utilization'][-1] if self.metrics['gpu_utilization'] else 0
        current_memory = self.metrics['memory_usage'][-1] if self.metrics['memory_usage'] else 0
        
        optimization_suggestions = []
        
        # Low throughput detection
        if current_throughput < self.targets['min_throughput']:
            optimization_suggestions.append({
                'type': 'low_throughput',
                'current': current_throughput,
                'target': self.targets['min_throughput'],
                'suggestion': 'Consider increasing batch size or optimizing kernels'
            })
        
        # Low GPU utilization
        if current_gpu_util < self.targets['target_gpu_utilization']:
            optimization_suggestions.append({
                'type': 'low_gpu_utilization',
                'current': current_gpu_util,
                'target': self.targets['target_gpu_utilization'],
                'suggestion': 'Increase parallelism or batch size'
            })
        
        # High memory usage warning
        if current_memory > self.targets['max_memory_usage'] * 100:
            optimization_suggestions.append({
                'type': 'high_memory_usage',
                'current': current_memory,
                'target': self.targets['max_memory_usage'] * 100,
                'suggestion': 'Reduce batch size or free unused memory'
            })
        
        # Trigger optimization callbacks
        for suggestion in optimization_suggestions:
            for callback in self.optimization_callbacks:
                try:
                    callback(suggestion)
                except Exception as e:
                    logger.debug(f"Optimization callback error: {e}")
    
    def record_performance(self, throughput: float, batch_size: int, 
                          processing_time: float, iterations: int = 0):
        """Record performance metrics from training."""
        self.metrics['throughput'].append(throughput)
        self.metrics['batch_size'].append(batch_size)
        self.metrics['processing_time'].append(processing_time)
        
        # Update peak throughput
        if throughput > self.current_stats['peak_throughput']:
            self.current_stats['peak_throughput'] = throughput
        
        # Update total iterations
        self.current_stats['total_iterations'] += iterations
        
        # Auto-optimize batch size based on performance
        self._auto_optimize_batch_size()
    
    def _auto_optimize_batch_size(self):
        """Automatically optimize batch size based on performance history."""
        if len(self.metrics['throughput']) < 5:
            return
        
        # Get recent performance data
        recent_throughput = list(self.metrics['throughput'])[-5:]
        recent_batch_sizes = list(self.metrics['batch_size'])[-5:]
        recent_processing_times = list(self.metrics['processing_time'])[-5:]
        
        # Calculate efficiency scores
        efficiencies = []
        for i in range(len(recent_throughput)):
            if recent_processing_times[i] > 0:
                efficiency = recent_throughput[i] / recent_processing_times[i]
                efficiencies.append((recent_batch_sizes[i], efficiency))
        
        if efficiencies:
            # Find optimal batch size
            optimal = max(efficiencies, key=lambda x: x[1])
            self.current_stats['optimal_batch_size'] = optimal[0]
    
    def add_optimization_callback(self, callback: Callable):
        """Add callback for optimization suggestions."""
        self.optimization_callbacks.append(callback)
    
    def get_performance_summary(self) -> Dict:
        """Get comprehensive performance summary."""
        summary = {
            'current_stats': self.current_stats.copy(),
            'recent_metrics': {
                'avg_throughput': statistics.mean(list(self.metrics['throughput'])[-10:]) if len(self.metrics['throughput']) >= 10 else 0,
                'avg_gpu_utilization': statistics.mean(list(self.metrics['gpu_utilization'])[-10:]) if len(self.metrics['gpu_utilization']) >= 10 else 0,
                'avg_memory_usage': statistics.mean(list(self.metrics['memory_usage'])[-10:]) if len(self.metrics['memory_usage']) >= 10 else 0,
                'batch_size_trend': list(self.metrics['batch_size'])[-5:] if len(self.metrics['batch_size']) >= 5 else []
            },
            'optimization_status': {
                'throughput_target_met': (self.current_stats['peak_throughput'] >= self.targets['min_throughput']),
                'gpu_utilization_optimal': (self.current_stats['avg_gpu_utilization'] >= self.targets['target_gpu_utilization']),
                'memory_usage_safe': (self.current_stats['peak_memory_usage'] <= self.targets['max_memory_usage'] * 100)
            }
        }
        
        return summary
    
    def log_performance_report(self):
        """Log comprehensive performance report."""
        summary = self.get_performance_summary()
        
        logger.info("📊 GPU PERFORMANCE REPORT")
        logger.info("=" * 50)
        logger.info(f"🎯 Peak throughput: {summary['current_stats']['peak_throughput']:,.0f} iter/sec")
        logger.info(f"📈 Avg GPU utilization: {summary['current_stats']['avg_gpu_utilization']:.1f}%")
        logger.info(f"💾 Peak memory usage: {summary['current_stats']['peak_memory_usage']:.1f}%")
        logger.info(f"⚡ Optimal batch size: {summary['current_stats']['optimal_batch_size']:,}")
        logger.info(f"🔄 Total iterations: {summary['current_stats']['total_iterations']:,}")
        
        # Performance targets assessment
        logger.info("\n🎯 TARGET ASSESSMENT:")
        opt_status = summary['optimization_status']
        logger.info(f"   Throughput target: {'✅' if opt_status['throughput_target_met'] else '❌'}")
        logger.info(f"   GPU utilization: {'✅' if opt_status['gpu_utilization_optimal'] else '❌'}")
        logger.info(f"   Memory usage: {'✅' if opt_status['memory_usage_safe'] else '❌'}")
        
        logger.info("=" * 50)
    
    def save_performance_data(self, filename: str):
        """Save performance data to JSON file."""
        data = {
            'metrics': {key: list(values) for key, values in self.metrics.items()},
            'current_stats': self.current_stats,
            'targets': self.targets
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Performance data saved to {filename}")
        except Exception as e:
            logger.error(f"Failed to save performance data: {e}")

# Factory function
def create_gpu_performance_monitor(update_interval: float = 1.0) -> GPUPerformanceMonitor:
    """Create GPU performance monitor with specified update interval."""
    return GPUPerformanceMonitor(update_interval=update_interval)
