"""
CUDA Environment Fix Script
Configures CUDA paths and validates GPU acceleration after CUDA installation.
"""
import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def find_cuda_installation():
    """Find CUDA installation paths."""
    possible_paths = [
        r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA",
        r"C:\Program Files (x86)\NVIDIA GPU Computing Toolkit\CUDA",
        r"C:\tools\cuda",
        r"C:\cuda"
    ]
    
    cuda_versions = []
    for base_path in possible_paths:
        if os.path.exists(base_path):
            for item in os.listdir(base_path):
                version_path = os.path.join(base_path, item)
                if os.path.isdir(version_path) and item.startswith('v'):
                    cuda_versions.append(version_path)
    
    return cuda_versions

def setup_cuda_environment():
    """Setup CUDA environment variables."""
    logger.info("🔍 Searching for CUDA installation...")
    
    cuda_paths = find_cuda_installation()
    if not cuda_paths:
        logger.error("❌ No CUDA installation found!")
        return False
    
    # Use the latest version found
    cuda_path = max(cuda_paths)
    logger.info(f"✅ Found CUDA at: {cuda_path}")
    
    # Set environment variables
    os.environ['CUDA_PATH'] = cuda_path
    os.environ['CUDA_HOME'] = cuda_path
    
    # Add to PATH
    bin_path = os.path.join(cuda_path, 'bin')
    lib_path = os.path.join(cuda_path, 'lib', 'x64')
    libnvvp_path = os.path.join(cuda_path, 'libnvvp')
    
    current_path = os.environ.get('PATH', '')
    new_paths = [bin_path, lib_path, libnvvp_path]
    
    for path in new_paths:
        if os.path.exists(path) and path not in current_path:
            os.environ['PATH'] = path + os.pathsep + current_path
            logger.info(f"✅ Added to PATH: {path}")
    
    logger.info(f"✅ CUDA_PATH set to: {cuda_path}")
    return True

def verify_cuda_installation():
    """Verify CUDA is working."""
    try:
        result = subprocess.run(['nvcc', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"✅ NVCC working: {result.stdout.strip().split()[-1]}")
            return True
        else:
            logger.error("❌ NVCC not working")
            return False
    except FileNotFoundError:
        logger.error("❌ NVCC not found in PATH")
        return False

def test_cupy_with_cuda():
    """Test CuPy with CUDA."""
    try:
        import cupy as cp
        
        # Test basic GPU operation
        x = cp.array([1, 2, 3, 4, 5])
        y = cp.sum(x)
        result = cp.asnumpy(y)
        
        logger.info(f"✅ CuPy GPU test successful: {result}")
        
        # Test GPU memory info
        mempool = cp.get_default_memory_pool()
        logger.info(f"✅ GPU memory pool available: {mempool.total_bytes() / 1024**2:.1f} MB")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ CuPy test failed: {e}")
        return False

def reinstall_cupy_for_cuda():
    """Reinstall CuPy with correct CUDA version."""
    try:
        # Detect CUDA version
        result = subprocess.run(['nvcc', '--version'], capture_output=True, text=True)
        if 'release 11.' in result.stdout:
            cupy_package = 'cupy-cuda11x'
        elif 'release 12.' in result.stdout:
            cupy_package = 'cupy-cuda12x'
        else:
            cupy_package = 'cupy-cuda11x'  # Default fallback
        
        logger.info(f"🔄 Reinstalling {cupy_package}...")
        
        # Uninstall old CuPy
        subprocess.run([sys.executable, '-m', 'pip', 'uninstall', 'cupy', '-y'], 
                      capture_output=True)
        subprocess.run([sys.executable, '-m', 'pip', 'uninstall', 'cupy-cuda11x', '-y'], 
                      capture_output=True)
        subprocess.run([sys.executable, '-m', 'pip', 'uninstall', 'cupy-cuda12x', '-y'], 
                      capture_output=True)
        
        # Install correct version
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', cupy_package], 
                               capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"✅ {cupy_package} installed successfully")
            return True
        else:
            logger.error(f"❌ Failed to install {cupy_package}: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error reinstalling CuPy: {e}")
        return False

def main():
    """Main CUDA fix process."""
    logger.info("🚀 Starting CUDA Environment Fix...")
    logger.info("=" * 50)
    
    # Step 1: Setup CUDA environment
    if not setup_cuda_environment():
        logger.error("❌ Failed to setup CUDA environment")
        return False
    
    # Step 2: Verify CUDA installation
    if not verify_cuda_installation():
        logger.error("❌ CUDA verification failed")
        return False
    
    # Step 3: Reinstall CuPy with correct CUDA version
    if not reinstall_cupy_for_cuda():
        logger.error("❌ CuPy reinstallation failed")
        return False
    
    # Step 4: Test CuPy with CUDA
    if not test_cupy_with_cuda():
        logger.error("❌ CuPy CUDA test failed")
        return False
    
    logger.info("=" * 50)
    logger.info("🎉 CUDA Environment Fix Complete!")
    logger.info("🚀 GPU acceleration should now work properly")
    logger.info("💡 Restart your Python session to ensure all changes take effect")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎯 Next steps:")
        print("1. Restart your terminal/IDE")
        print("2. Run: python train_cfr.py")
        print("3. GPU acceleration should now work!")
    else:
        print("\n❌ CUDA fix failed. Check the logs above for details.")
