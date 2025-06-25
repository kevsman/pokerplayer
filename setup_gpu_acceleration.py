"""
GPU Acceleration Setup and Usage Guide for Poker Bot
This script helps you set up and test GPU acceleration for the poker bot.
"""
import subprocess
import sys
import os
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_gpu_availability():
    """Check if GPU and CUDA are available on the system."""
    logger.info("Checking GPU availability...")
    
    try:
        import subprocess
        result = subprocess.run(['nvidia-smi'], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            logger.info("NVIDIA GPU detected:")
            print(result.stdout)
            return True
        else:
            logger.warning("nvidia-smi command failed")
            return False
    except (subprocess.TimeoutExpired, FileNotFoundError):
        logger.warning("nvidia-smi not found or timeout - no NVIDIA GPU detected")
        return False

def install_gpu_dependencies():
    """Install required GPU dependencies."""
    logger.info("Installing GPU dependencies...")
    
    packages = [
        'cupy-cuda11x',  # For CUDA 11.x, adjust based on your CUDA version
        'numba',
        'numpy',
    ]
    
    for package in packages:
        try:
            logger.info(f"Installing {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
            logger.info(f"✓ {package} installed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"✗ Failed to install {package}: {e}")
            return False
    
    return True

def test_gpu_modules():
    """Test if GPU modules are working correctly."""
    logger.info("Testing GPU modules...")
    
    try:
        # Test CuPy
        import cupy as cp
        logger.info(f"✓ CuPy version {cp.__version__} loaded successfully")
        
        # Test basic GPU operation
        x_gpu = cp.array([1, 2, 3, 4, 5])
        y_gpu = x_gpu * 2
        logger.info(f"✓ Basic GPU computation test passed: {y_gpu}")
        
        # Test Numba
        from numba import cuda
        if cuda.is_available():
            logger.info("✓ Numba CUDA is available")
        else:
            logger.warning("⚠ Numba CUDA not available")
        
        return True
        
    except ImportError as e:
        logger.error(f"✗ GPU module import failed: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ GPU test failed: {e}")
        return False

def benchmark_performance():
    """Benchmark CPU vs GPU performance."""
    logger.info("Running performance benchmark...")
    
    try:
        from gpu_integrated_trainer import IntegratedTrainer
        
        # Test CPU performance
        logger.info("Benchmarking CPU performance...")
        cpu_trainer = IntegratedTrainer(use_gpu=False)
        cpu_results = cpu_trainer.benchmark_performance(iterations=50, simulations_per_iteration=1000)
        
        # Test GPU performance if available
        gpu_results = None
        try:
            logger.info("Benchmarking GPU performance...")
            gpu_trainer = IntegratedTrainer(use_gpu=True)
            if gpu_trainer.use_gpu:
                gpu_results = gpu_trainer.benchmark_performance(iterations=50, simulations_per_iteration=1000)
            else:
                logger.warning("GPU not available for benchmarking")
        except Exception as e:
            logger.error(f"GPU benchmark failed: {e}")
        
        # Compare results
        logger.info("\n=== BENCHMARK RESULTS ===")
        logger.info(f"CPU Performance:")
        for key, value in cpu_results.items():
            logger.info(f"  {key}: {value}")
        
        if gpu_results:
            logger.info(f"\nGPU Performance:")
            for key, value in gpu_results.items():
                logger.info(f"  {key}: {value}")
            
            speedup = gpu_results['simulations_per_second'] / cpu_results['simulations_per_second']
            logger.info(f"\n🚀 GPU Speedup: {speedup:.2f}x faster than CPU")
        
        return cpu_results, gpu_results
        
    except ImportError as e:
        logger.error(f"Could not import training modules: {e}")
        return None, None

def run_training_demo():
    """Run a demonstration of GPU-accelerated training."""
    logger.info("Running training demonstration...")
    
    try:
        from gpu_integrated_trainer import IntegratedTrainer
        
        trainer = IntegratedTrainer(use_gpu=True)
        system_info = trainer.get_system_info()
        
        logger.info("System Information:")
        for key, value in system_info.items():
            logger.info(f"  {key}: {value}")
        
        # Run short training session
        logger.info("Running short training demonstration (100 iterations)...")
        training_stats = trainer.train_strategies(num_iterations=100, save_interval=50)
        
        logger.info("Training completed successfully!")
        logger.info("Training Statistics:")
        for key, value in training_stats.items():
            logger.info(f"  {key}: {value}")
        
        return True
        
    except Exception as e:
        logger.error(f"Training demo failed: {e}")
        return False

def optimize_settings():
    """Automatically optimize simulation settings for the current system."""
    logger.info("Optimizing simulation settings...")
    
    try:
        from gpu_integrated_trainer import IntegratedTrainer
        
        trainer = IntegratedTrainer(use_gpu=True)
        optimal_count = trainer.optimize_simulation_counts()
        
        logger.info(f"Recommended simulation count: {optimal_count}")
        
        # Update CFR solver with optimal settings
        logger.info("Updating CFR solver with optimal settings...")
        
        # Read current CFR solver
        with open('cfr_solver.py', 'r') as f:
            content = f.read()
        
        # Update simulation counts (backup original first)
        import shutil
        shutil.copy('cfr_solver.py', 'cfr_solver.py.backup')
        
        # Replace simulation counts
        content = content.replace('num_simulations=500', f'num_simulations={optimal_count}')
        content = content.replace('iterations=500', f'iterations={max(200, optimal_count // 5)}')
        
        with open('cfr_solver.py', 'w') as f:
            f.write(content)
        
        logger.info("✓ CFR solver updated with optimal settings")
        logger.info("✓ Original file backed up as cfr_solver.py.backup")
        
        return optimal_count
        
    except Exception as e:
        logger.error(f"Settings optimization failed: {e}")
        return None

def main():
    """Main setup and testing function."""
    print("🎰 Poker Bot GPU Acceleration Setup 🎰")
    print("=" * 50)
    
    # Check GPU availability
    gpu_available = check_gpu_availability()
    
    if not gpu_available:
        print("\n⚠️  WARNING: No NVIDIA GPU detected!")
        print("The bot will work with CPU-only acceleration.")
        response = input("Continue with CPU-only setup? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Install dependencies
    print("\n📦 Installing Dependencies...")
    if gpu_available:
        success = install_gpu_dependencies()
        if not success:
            logger.error("Failed to install GPU dependencies")
            return
    
    # Test GPU modules
    if gpu_available:
        print("\n🧪 Testing GPU Modules...")
        gpu_working = test_gpu_modules()
        if not gpu_working:
            logger.error("GPU modules not working correctly")
            return
    
    # Run benchmark
    print("\n⚡ Running Performance Benchmark...")
    cpu_results, gpu_results = benchmark_performance()
    
    # Optimize settings
    print("\n⚙️  Optimizing Settings...")
    optimal_count = optimize_settings()
    
    # Run training demo
    print("\n🚀 Running Training Demo...")
    demo_success = run_training_demo()
    
    # Summary
    print("\n" + "=" * 50)
    print("🎉 SETUP COMPLETE!")
    print("=" * 50)
    
    if gpu_available and gpu_results:
        speedup = gpu_results['simulations_per_second'] / cpu_results['simulations_per_second']
        print(f"🚀 GPU Acceleration: {speedup:.2f}x faster than CPU")
    
    if optimal_count:
        print(f"⚙️  Optimal simulation count: {optimal_count}")
    
    print(f"✅ Training demo: {'Success' if demo_success else 'Failed'}")
    
    print("\n📋 Next Steps:")
    print("1. Run 'python gpu_integrated_trainer.py --benchmark' for detailed benchmarks")
    print("2. Run 'python gpu_integrated_trainer.py --train 1000' for full training")
    print("3. Use 'python train_cfr.py' with GPU acceleration enabled")
    print("4. Monitor GPU usage with 'nvidia-smi' during training")

if __name__ == "__main__":
    main()
