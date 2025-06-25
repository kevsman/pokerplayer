"""
GPU Configuration Manager for Poker Bot
Handles dynamic GPU/CPU switching and optimal settings management.
"""
import json
import os
import logging
import time
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class GPUConfigManager:
    """Manages GPU acceleration configuration and automatic fallback."""
    
    def __init__(self, config_file: str = 'gpu_config.json'):
        self.config_file = config_file
        self.config = self.load_config()
        self.gpu_available = self._test_gpu_availability()
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            logger.info(f"✅ Loaded configuration from {self.config_file}")
            return config
        except FileNotFoundError:
            logger.info("📝 Creating default configuration...")
            return self._create_default_config()
        except json.JSONDecodeError:
            logger.error("❌ Invalid JSON in config file, using defaults")
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Create default configuration based on system capabilities."""
        config = {
            'use_gpu': True,
            'monte_carlo_simulations': 1000,
            'cfr_iterations': 1000,
            'batch_size': 50,
            'training_iterations': 2000,
            'auto_fallback': True,
            'performance_monitoring': True
        }
        self.save_config(config)
        return config
    
    def save_config(self, config: Optional[Dict[str, Any]] = None):
        """Save configuration to file."""
        if config is None:
            config = self.config
        
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"💾 Configuration saved to {self.config_file}")
        except Exception as e:
            logger.error(f"❌ Failed to save configuration: {e}")
    
    def _test_gpu_availability(self) -> bool:
        """Test if GPU acceleration is actually working."""
        try:
            from gpu_accelerated_equity import GPUEquityCalculator
            
            # Quick test
            calculator = GPUEquityCalculator(use_gpu=True)
            test_hands = [['Ah', 'Kh']]
            community_cards = ['Qh', 'Jh', '10s']
            
            equities, _, _ = calculator.calculate_equity_batch(
                test_hands, community_cards, num_simulations=10
            )
            
            if equities and 0.0 <= equities[0] <= 1.0:
                logger.info("✅ GPU acceleration confirmed working")
                return True
            else:
                logger.warning("⚠️  GPU test returned invalid results")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️  GPU not available: {e}")
            return False
    
    def get_optimal_settings(self, task: str = 'training') -> Dict[str, Any]:
        """Get optimal settings for specific task."""
        base_settings = self.config.copy()
        
        # Adjust based on GPU availability
        if not self.gpu_available and self.config.get('auto_fallback', True):
            logger.info("🔄 Auto-fallback to CPU optimization")
            base_settings.update({
                'use_gpu': False,
                'monte_carlo_simulations': 500,
                'cfr_iterations': 500,
                'batch_size': 10,
                'training_iterations': 1000
            })
        
        # Task-specific adjustments
        if task == 'real_time':
            # For real-time play, prioritize speed
            base_settings.update({
                'monte_carlo_simulations': min(base_settings['monte_carlo_simulations'], 200),
                'cfr_iterations': min(base_settings['cfr_iterations'], 100)
            })
        elif task == 'training':
            # For training, prioritize accuracy
            if self.gpu_available:
                base_settings.update({
                    'monte_carlo_simulations': max(base_settings['monte_carlo_simulations'], 1000),
                    'cfr_iterations': max(base_settings['cfr_iterations'], 1000)
                })
        elif task == 'analysis':
            # For analysis, maximum accuracy
            if self.gpu_available:
                base_settings.update({
                    'monte_carlo_simulations': 2000,
                    'cfr_iterations': 2000
                })
        
        return base_settings
    
    def create_solver(self, task: str = 'training'):
        """Create optimally configured CFR solver."""
        from cfr_solver import CFRSolver
        from hand_evaluator import HandEvaluator
        from equity_calculator import EquityCalculator
        from hand_abstraction import HandAbstraction
        
        settings = self.get_optimal_settings(task)
        
        hand_evaluator = HandEvaluator()
        equity_calculator = EquityCalculator()
        abstraction = HandAbstraction(hand_evaluator, equity_calculator)
        
        # Create solver with GPU support
        solver = CFRSolver(
            abstraction, 
            hand_evaluator, 
            equity_calculator,
            logger_instance=logger,
            use_gpu=settings['use_gpu']
        )
        
        logger.info(f"🧠 CFR Solver created for {task} with GPU: {settings['use_gpu']}")
        return solver, settings
    
    def create_trainer(self):
        """Create optimally configured trainer."""
        try:
            from gpu_integrated_trainer import IntegratedTrainer
            settings = self.get_optimal_settings('training')
            
            trainer = IntegratedTrainer(
                use_gpu=settings['use_gpu'],
                num_players=6
            )
            
            logger.info(f"🏋️ Trainer created with GPU: {settings['use_gpu']}")
            return trainer, settings
            
        except ImportError:
            logger.warning("⚠️  GPU trainer not available, using basic setup")
            return None, self.get_optimal_settings('training')
    
    def benchmark_current_setup(self) -> Dict[str, float]:
        """Benchmark current configuration."""
        logger.info("📊 Benchmarking current setup...")
        
        from equity_calculator import EquityCalculator
        
        test_hands = [['Ah', 'Kh'], ['Qs', 'Js']]
        community_cards = ['Qh', 'Jh', '10s']
        settings = self.get_optimal_settings()
        
        # CPU benchmark
        cpu_calculator = EquityCalculator()
        start_time = time.time()
        for hand in test_hands:
            cpu_calculator.calculate_equity_monte_carlo(
                [hand], community_cards, None,
                num_simulations=settings['monte_carlo_simulations'],
                num_opponents=2
            )
        cpu_time = time.time() - start_time
        
        # GPU benchmark (if available)
        gpu_time = cpu_time
        if self.gpu_available:
            try:
                from gpu_accelerated_equity import GPUEquityCalculator
                gpu_calculator = GPUEquityCalculator(use_gpu=True)
                
                start_time = time.time()
                gpu_calculator.calculate_equity_batch(
                    test_hands, community_cards,
                    num_simulations=settings['monte_carlo_simulations']
                )
                gpu_time = time.time() - start_time
            except Exception as e:
                logger.warning(f"⚠️  GPU benchmark failed: {e}")
        
        speedup = cpu_time / gpu_time if gpu_time > 0 else 1.0
        
        results = {
            'cpu_time': cpu_time,
            'gpu_time': gpu_time,
            'speedup': speedup,
            'simulations_per_second': (len(test_hands) * settings['monte_carlo_simulations']) / gpu_time
        }
        
        logger.info(f"📊 Benchmark Results:")
        logger.info(f"  CPU Time: {cpu_time:.3f}s")
        logger.info(f"  GPU Time: {gpu_time:.3f}s") 
        logger.info(f"  Speedup: {speedup:.2f}x")
        logger.info(f"  Throughput: {results['simulations_per_second']:.0f} sims/sec")
        
        return results
    
    def auto_optimize(self):
        """Automatically optimize settings based on current hardware."""
        logger.info("🔧 Auto-optimizing configuration...")
        
        benchmark = self.benchmark_current_setup()
        
        # Adjust settings based on performance
        new_config = self.config.copy()
        
        if benchmark['speedup'] > 2.0:
            # High-performance GPU
            new_config.update({
                'monte_carlo_simulations': 2000,
                'cfr_iterations': 2000,
                'training_iterations': 5000,
                'batch_size': 100
            })
            logger.info("🚀 High-performance GPU detected - aggressive settings")
            
        elif benchmark['speedup'] > 1.5:
            # Good GPU performance
            new_config.update({
                'monte_carlo_simulations': 1500,
                'cfr_iterations': 1500,
                'training_iterations': 3000,
                'batch_size': 75
            })
            logger.info("✅ Good GPU performance - enhanced settings")
            
        elif benchmark['speedup'] < 1.2:
            # Limited GPU benefit
            new_config.update({
                'use_gpu': False,
                'monte_carlo_simulations': 500,
                'cfr_iterations': 500,
                'training_iterations': 1000,
                'batch_size': 20
            })
            logger.info("⚠️  Limited GPU benefit - optimizing for CPU")
        
        # Update configuration
        self.config = new_config
        self.save_config()
        
        logger.info("✅ Configuration optimized automatically")
        return new_config

# Global configuration manager instance
_config_manager = None

def get_config_manager() -> GPUConfigManager:
    """Get global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = GPUConfigManager()
    return _config_manager

def create_optimized_solver(task: str = 'training'):
    """Create an optimally configured solver for the current system."""
    config_manager = get_config_manager()
    return config_manager.create_solver(task)

def create_optimized_trainer():
    """Create an optimally configured trainer for the current system."""
    config_manager = get_config_manager()
    return config_manager.create_trainer()

def benchmark_system():
    """Benchmark the current system and return performance metrics."""
    config_manager = get_config_manager()
    return config_manager.benchmark_current_setup()

if __name__ == "__main__":
    # Demo usage
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info("🎯 GPU Configuration Manager Demo")
    logger.info("=" * 50)
    
    # Initialize manager
    manager = GPUConfigManager()
    
    # Show current settings
    settings = manager.get_optimal_settings()
    logger.info(f"Current settings: {json.dumps(settings, indent=2)}")
    
    # Benchmark system
    results = manager.benchmark_current_setup()
    
    # Auto-optimize
    manager.auto_optimize()
    
    # Create optimized components
    solver, solver_settings = manager.create_solver('real_time')
    trainer, trainer_settings = manager.create_trainer()
    
    logger.info("✅ Demo completed!")
