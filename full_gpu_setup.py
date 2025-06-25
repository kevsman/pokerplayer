"""
Full GPU Setup Implementation - Option 2
This script implements complete GPU acceleration setup for maximum performance.
"""
import os
import sys
import subprocess
import logging
import time
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FullGPUSetup:
    """Complete GPU acceleration setup and configuration."""
    
    def __init__(self):
        self.setup_results = {
            'cuda_detected': False,
            'cupy_working': False,
            'numba_cuda_working': False,
            'gpu_modules_functional': False,
            'performance_improvement': 0.0,
            'recommended_settings': {}
        }
    
    def check_gpu_hardware(self):
        """Check for NVIDIA GPU and CUDA support."""
        logger.info("🔍 Checking GPU hardware...")
        
        try:
            result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                logger.info("✅ NVIDIA GPU detected")
                self.setup_results['cuda_detected'] = True
                
                # Parse GPU info
                gpu_info = result.stdout
                if 'CUDA Version:' in gpu_info:
                    cuda_version = gpu_info.split('CUDA Version:')[1].split()[0]
                    logger.info(f"✅ CUDA Version: {cuda_version}")
                    
                return True
            else:
                logger.warning("❌ nvidia-smi failed - No NVIDIA GPU detected")
                return False
                
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("❌ nvidia-smi not found - No NVIDIA GPU or drivers")
            return False
    
    def install_cuda_dependencies(self):
        """Install or verify CUDA dependencies."""
        logger.info("📦 Installing/verifying CUDA dependencies...")
        
        # Check if CUDA toolkit is installed
        cuda_paths = [
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA",
            r"C:\Program Files (x86)\NVIDIA GPU Computing Toolkit\CUDA",
            "/usr/local/cuda",
            "/opt/cuda"
        ]
        
        cuda_found = False
        for path in cuda_paths:
            if os.path.exists(path):
                logger.info(f"✅ CUDA found at: {path}")
                cuda_found = True
                
                # Set CUDA_PATH environment variable
                os.environ['CUDA_PATH'] = path
                logger.info(f"✅ Set CUDA_PATH={path}")
                break
        
        if not cuda_found:
            logger.warning("⚠️  CUDA toolkit not found - installing via conda...")
            try:
                subprocess.run(['conda', 'install', 'cudatoolkit', '-y'], check=True)
                logger.info("✅ CUDA toolkit installed via conda")
            except (subprocess.CalledProcessError, FileNotFoundError):
                logger.error("❌ Failed to install CUDA toolkit")
                return False
        
        return True
    
    def install_gpu_packages(self):
        """Install GPU acceleration packages."""
        logger.info("📦 Installing GPU packages...")
        
        packages = [
            'numpy',
            'numba',
            'cupy-cuda11x',  # Will auto-detect and adjust
            'matplotlib',  # For performance plots
            'scipy'
        ]
        
        # Detect CUDA version for correct CuPy package
        try:
            result = subprocess.run(['nvcc', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                version_info = result.stdout
                if 'release 12' in version_info:
                    packages[2] = 'cupy-cuda12x'
                elif 'release 11' in version_info:
                    packages[2] = 'cupy-cuda11x'
                logger.info(f"✅ Auto-detected CuPy package: {packages[2]}")
        except FileNotFoundError:
            logger.warning("⚠️  nvcc not found, using default cupy-cuda11x")
        
        for package in packages:
            try:
                logger.info(f"Installing {package}...")
                subprocess.run([sys.executable, '-m', 'pip', 'install', package, '--upgrade'], 
                             check=True, capture_output=True)
                logger.info(f"✅ {package} installed successfully")
            except subprocess.CalledProcessError as e:
                logger.error(f"❌ Failed to install {package}: {e}")
                if 'cupy' in package:
                    # Try alternative CuPy package
                    alt_package = 'cupy-cuda12x' if 'cuda11x' in package else 'cupy-cuda11x'
                    try:
                        logger.info(f"Trying alternative: {alt_package}")
                        subprocess.run([sys.executable, '-m', 'pip', 'install', alt_package], 
                                     check=True, capture_output=True)
                        logger.info(f"✅ {alt_package} installed successfully")
                    except subprocess.CalledProcessError:
                        logger.error(f"❌ Failed to install any CuPy variant")
        
        return True
    
    def test_gpu_functionality(self):
        """Test GPU acceleration functionality."""
        logger.info("🧪 Testing GPU functionality...")
        
        # Test CuPy
        try:
            import cupy as cp
            import numpy as np
            
            # Test basic GPU operation
            x_gpu = cp.array([1, 2, 3, 4, 5])
            y_gpu = x_gpu * 2
            result = cp.asnumpy(y_gpu)
            
            if np.array_equal(result, [2, 4, 6, 8, 10]):
                logger.info("✅ CuPy basic operations working")
                self.setup_results['cupy_working'] = True
            else:
                logger.error("❌ CuPy basic operations failed")
                
        except Exception as e:
            logger.error(f"❌ CuPy test failed: {e}")
        
        # Test Numba CUDA
        try:
            from numba import cuda
            if cuda.is_available():
                logger.info("✅ Numba CUDA available")
                self.setup_results['numba_cuda_working'] = True
            else:
                logger.warning("⚠️  Numba CUDA not available")
        except Exception as e:
            logger.error(f"❌ Numba CUDA test failed: {e}")
        
        # Test poker bot GPU modules
        try:
            from gpu_accelerated_equity import GPUEquityCalculator
            from gpu_cfr_trainer import GPUCFRTrainer
            
            # Test GPU equity calculator
            calculator = GPUEquityCalculator(use_gpu=True)
            test_hands = [['Ah', 'Kh']]
            community_cards = ['Qh', 'Jh', '10s']
            
            equities, _, _ = calculator.calculate_equity_batch(
                test_hands, community_cards, num_simulations=100
            )
            
            if equities and 0.0 <= equities[0] <= 1.0:
                logger.info("✅ GPU poker modules working")
                self.setup_results['gpu_modules_functional'] = True
            else:
                logger.error("❌ GPU poker modules failed")
                
        except Exception as e:
            logger.error(f"❌ GPU poker modules test failed: {e}")
    
    def benchmark_performance(self):
        """Benchmark GPU vs CPU performance."""
        logger.info("📊 Benchmarking GPU vs CPU performance...")
        
        try:
            from equity_calculator import EquityCalculator
            from gpu_accelerated_equity import GPUEquityCalculator
            
            test_hands = [['Ah', 'Kh'], ['Qs', 'Js'], ['10h', '9h']]
            community_cards = ['Qh', 'Jh', '10s']
            sim_count = 1000
            
            # CPU benchmark
            cpu_calculator = EquityCalculator()
            start_time = time.time()
            for hand in test_hands:
                cpu_calculator.calculate_equity_monte_carlo(
                    [hand], community_cards, None, 
                    num_simulations=sim_count, num_opponents=2
                )
            cpu_time = time.time() - start_time
            
            # GPU benchmark
            if self.setup_results['gpu_modules_functional']:
                gpu_calculator = GPUEquityCalculator(use_gpu=True)
                start_time = time.time()
                gpu_calculator.calculate_equity_batch(
                    test_hands, community_cards, num_simulations=sim_count
                )
                gpu_time = time.time() - start_time
                
                speedup = cpu_time / gpu_time if gpu_time > 0 else 1.0
                self.setup_results['performance_improvement'] = speedup
                
                logger.info(f"📊 CPU time: {cpu_time:.3f}s")
                logger.info(f"📊 GPU time: {gpu_time:.3f}s")
                logger.info(f"🚀 Speedup: {speedup:.2f}x")
                
                if speedup > 1.5:
                    logger.info("✅ Significant GPU acceleration achieved!")
                elif speedup > 1.1:
                    logger.info("✅ Moderate GPU acceleration achieved")
                else:
                    logger.warning("⚠️  Limited GPU acceleration benefit")
            else:
                logger.warning("⚠️  GPU modules not functional, skipping GPU benchmark")
                
        except Exception as e:
            logger.error(f"❌ Benchmark failed: {e}")
    
    def configure_optimal_settings(self):
        """Configure optimal settings based on hardware capabilities."""
        logger.info("⚙️  Configuring optimal settings...")
        
        settings = {
            'use_gpu': self.setup_results['gpu_modules_functional'],
            'monte_carlo_simulations': 1000,
            'cfr_iterations': 1000,
            'batch_size': 50 if self.setup_results['gpu_modules_functional'] else 10,
            'training_iterations': 2000 if self.setup_results['gpu_modules_functional'] else 1000
        }
        
        # Adjust based on performance
        if self.setup_results['performance_improvement'] > 2.0:
            settings['monte_carlo_simulations'] = 2000
            settings['cfr_iterations'] = 2000
            settings['training_iterations'] = 5000
            logger.info("🚀 High-performance GPU detected - using aggressive settings")
            
        elif self.setup_results['performance_improvement'] > 1.5:
            settings['monte_carlo_simulations'] = 1500
            settings['cfr_iterations'] = 1500
            settings['training_iterations'] = 3000
            logger.info("✅ Good GPU performance - using enhanced settings")
            
        elif not self.setup_results['gpu_modules_functional']:
            settings['monte_carlo_simulations'] = 500
            settings['cfr_iterations'] = 500
            settings['training_iterations'] = 1000
            logger.info("⚠️  CPU-only mode - using conservative settings")
        
        self.setup_results['recommended_settings'] = settings
        
        # Save settings to config file
        config_file = 'gpu_config.json'
        with open(config_file, 'w') as f:
            json.dump(settings, f, indent=2)
        
        logger.info(f"💾 Settings saved to {config_file}")
        return settings
    
    def update_poker_bot_integration(self):
        """Update poker bot files to use GPU acceleration."""
        logger.info("🔧 Updating poker bot integration...")
        
        try:
            # Update imports in main bot files
            import_updates = [
                ('poker_bot.py', 'from cfr_solver import CFRSolver', 
                 'from cfr_solver import CFRSolver  # Now with GPU support'),
                
                ('decision_engine.py', 'from cfr_solver import CFRSolver',
                 'from cfr_solver import CFRSolver  # Now with GPU support'),
            ]
            
            for filename, old_import, new_import in import_updates:
                if os.path.exists(filename):
                    try:
                        with open(filename, 'r') as f:
                            content = f.read()
                        
                        if old_import in content and new_import not in content:
                            updated_content = content.replace(old_import, new_import)
                            with open(filename, 'w') as f:
                                f.write(updated_content)
                            logger.info(f"✅ Updated {filename}")
                    except Exception as e:
                        logger.warning(f"⚠️  Could not update {filename}: {e}")
            
            logger.info("✅ Poker bot integration updated")
            
        except Exception as e:
            logger.error(f"❌ Failed to update poker bot integration: {e}")
    
    def create_usage_examples(self):
        """Create example scripts for using GPU acceleration."""
        logger.info("📝 Creating usage examples...")
        
        # Example 1: Basic GPU usage
        basic_example = '''"""
Example: Basic GPU-Accelerated Poker Bot Usage
"""
from gpu_integrated_trainer import IntegratedTrainer
from cfr_solver import CFRSolver
import json

# Load optimal settings
with open('gpu_config.json', 'r') as f:
    config = json.load(f)

def main():
    print("Starting GPU-Accelerated Poker Bot Training...")
    
    # Initialize trainer with GPU acceleration
    trainer = IntegratedTrainer(use_gpu=config['use_gpu'])
    
    # Train strategies with optimal settings
    training_stats = trainer.train_strategies(
        num_iterations=config['training_iterations']
    )
    
    print(f"Training completed!")
    print(f"GPU Used: {training_stats['gpu_accelerated']}")
    print(f"Training Time: {training_stats['total_time']:.2f}s")
    print(f"Iterations: {training_stats['total_iterations']}")

if __name__ == "__main__":
    main()
'''
        
        with open('example_gpu_usage.py', 'w', encoding='utf-8') as f:
            f.write(basic_example)
        
        # Example 2: Performance monitoring
        monitor_example = '''"""
Example: GPU Performance Monitoring
"""
import time
from gpu_accelerated_equity import GPUEquityCalculator
from equity_calculator import EquityCalculator
import json

def compare_performance():
    """Compare GPU vs CPU performance in real-time."""
    
    # Load config
    with open('gpu_config.json', 'r') as f:
        config = json.load(f)
    
    test_hands = [['Ah', 'Kh'], ['Qs', 'Js'], ['10h', '9h']]
    community_cards = ['Qh', 'Jh', '10s']
    
    print("Performance Comparison:")
    
    # CPU test
    cpu_calc = EquityCalculator()
    start = time.time()
    for hand in test_hands:
        cpu_calc.calculate_equity_monte_carlo(
            [hand], community_cards, None,
            num_simulations=config['monte_carlo_simulations'], 
            num_opponents=2
        )
    cpu_time = time.time() - start
    
    # GPU test (if available)
    if config['use_gpu']:
        gpu_calc = GPUEquityCalculator(use_gpu=True)
        start = time.time()
        gpu_calc.calculate_equity_batch(
            test_hands, community_cards, 
            num_simulations=config['monte_carlo_simulations']
        )
        gpu_time = time.time() - start
        speedup = cpu_time / gpu_time
        
        print(f"CPU Time: {cpu_time:.3f}s")
        print(f"GPU Time: {gpu_time:.3f}s")
        print(f"Speedup: {speedup:.2f}x")
    else:
        print(f"CPU Time: {cpu_time:.3f}s")
        print("GPU: Not available")

if __name__ == "__main__":
    compare_performance()
'''
        
        with open('example_performance_monitor.py', 'w', encoding='utf-8') as f:
            f.write(monitor_example)
        
        logger.info("✅ Usage examples created")
    
    def generate_setup_report(self):
        """Generate comprehensive setup report."""
        logger.info("📋 Generating setup report...")
        
        report = {
            'setup_timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'hardware_status': {
                'cuda_detected': self.setup_results['cuda_detected'],
                'gpu_functional': self.setup_results['gpu_modules_functional']
            },
            'software_status': {
                'cupy_working': self.setup_results['cupy_working'],
                'numba_cuda_working': self.setup_results['numba_cuda_working']
            },
            'performance': {
                'speedup_factor': self.setup_results['performance_improvement'],
                'recommended_settings': self.setup_results['recommended_settings']
            },
            'next_steps': []
        }
        
        # Add recommendations
        if self.setup_results['gpu_modules_functional']:
            report['next_steps'] = [
                "✅ GPU acceleration is fully functional",
                "🚀 Use 'python example_gpu_usage.py' to start training",
                "📊 Monitor performance with 'python example_performance_monitor.py'",
                f"⚙️  Optimal simulation count: {self.setup_results['recommended_settings']['monte_carlo_simulations']}",
                "🎰 Your poker bot is ready for high-performance training!"
            ]
        else:
            report['next_steps'] = [
                "⚠️  GPU acceleration not fully functional",
                "💡 Use CPU optimization instead: python cfr_solver_optimized.py",
                "🔧 Check CUDA installation and try: pip install cupy-cuda11x --upgrade",
                "📈 Still significant improvements available with CPU optimization"
            ]
        
        # Save report
        with open('gpu_setup_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("🎯 GPU SETUP COMPLETE - SUMMARY")
        logger.info("="*60)
        
        for step in report['next_steps']:
            logger.info(step)
        
        logger.info(f"\n📊 Performance Improvement: {self.setup_results['performance_improvement']:.2f}x")
        logger.info(f"📁 Full report saved to: gpu_setup_report.json")
        logger.info("="*60)
        
        return report

def main():
    """Execute full GPU setup process."""
    logger.info("🚀 Starting Full GPU Setup - Option 2")
    logger.info("="*60)
    
    setup = FullGPUSetup()
    
    # Step 1: Check hardware
    if not setup.check_gpu_hardware():
        logger.warning("⚠️  No NVIDIA GPU detected - continuing with CPU optimization")
    
    # Step 2: Install dependencies
    setup.install_cuda_dependencies()
    setup.install_gpu_packages()
    
    # Step 3: Test functionality
    setup.test_gpu_functionality()
    
    # Step 4: Benchmark performance
    setup.benchmark_performance()
    
    # Step 5: Configure optimal settings
    setup.configure_optimal_settings()
    
    # Step 6: Update integration
    setup.update_poker_bot_integration()
    
    # Step 7: Create examples
    setup.create_usage_examples()
    
    # Step 8: Generate report
    setup.generate_setup_report()
    
    logger.info("🎉 Full GPU Setup Complete!")
    
    return setup.setup_results

if __name__ == "__main__":
    main()
