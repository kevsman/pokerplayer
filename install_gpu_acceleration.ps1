# PowerShell script to install GPU acceleration for Poker Bot
# Run this script as Administrator for best results

Write-Host "🎰 Poker Bot GPU Acceleration Installer 🎰" -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Green

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Host "⚠️  Warning: Not running as Administrator. Some operations may fail." -ForegroundColor Yellow
}

# Check for NVIDIA GPU
Write-Host "`n🔍 Checking for NVIDIA GPU..." -ForegroundColor Cyan
try {
    $nvidiaCheck = nvidia-smi 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ NVIDIA GPU detected!" -ForegroundColor Green
        nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader,nounits
    } else {
        Write-Host "❌ No NVIDIA GPU detected. Continuing with CPU-only installation." -ForegroundColor Yellow
    }
} catch {
    Write-Host "❌ nvidia-smi not found. Continuing with CPU-only installation." -ForegroundColor Yellow
}

# Check Python installation
Write-Host "`n🐍 Checking Python installation..." -ForegroundColor Cyan
try {
    $pythonVersion = python --version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Python found: $pythonVersion" -ForegroundColor Green
    } else {
        Write-Host "❌ Python not found. Please install Python first." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Python not found. Please install Python first." -ForegroundColor Red
    exit 1
}

# Check CUDA version if NVIDIA GPU is present
Write-Host "`n🔧 Checking CUDA installation..." -ForegroundColor Cyan
try {
    $cudaVersion = nvcc --version 2>$null | Select-String "release" | ForEach-Object { $_.Line }
    if ($cudaVersion) {
        Write-Host "✅ CUDA found: $cudaVersion" -ForegroundColor Green
        
        # Determine appropriate CuPy version based on CUDA version
        if ($cudaVersion -match "11\.") {
            $cupyPackage = "cupy-cuda11x"
        } elseif ($cudaVersion -match "12\.") {
            $cupyPackage = "cupy-cuda12x"
        } else {
            $cupyPackage = "cupy-cuda11x"  # Default fallback
        }
        
        Write-Host "📦 Will install: $cupyPackage" -ForegroundColor Cyan
    } else {
        Write-Host "❌ CUDA not found. GPU acceleration will not be available." -ForegroundColor Yellow
        $cupyPackage = $null
    }
} catch {
    Write-Host "❌ CUDA not found. GPU acceleration will not be available." -ForegroundColor Yellow
    $cupyPackage = $null
}

# Install required packages
Write-Host "`n📦 Installing Python packages..." -ForegroundColor Cyan

$packages = @(
    "numpy",
    "numba",
    "matplotlib",
    "scipy"
)

if ($cupyPackage) {
    $packages += $cupyPackage
}

foreach ($package in $packages) {
    Write-Host "Installing $package..." -ForegroundColor Yellow
    try {
        pip install $package --upgrade
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ $package installed successfully" -ForegroundColor Green
        } else {
            Write-Host "❌ Failed to install $package" -ForegroundColor Red
        }
    } catch {
        Write-Host "❌ Error installing $package" -ForegroundColor Red
    }
}

# Test the installation
Write-Host "`n🧪 Testing installation..." -ForegroundColor Cyan
$testScript = @"
import sys
try:
    import numpy as np
    print('✅ NumPy:', np.__version__)
except ImportError:
    print('❌ NumPy not available')

try:
    import numba
    print('✅ Numba:', numba.__version__)
    from numba import cuda
    if cuda.is_available():
        print('✅ Numba CUDA available')
    else:
        print('⚠️  Numba CUDA not available')
except ImportError:
    print('❌ Numba not available')

try:
    import cupy as cp
    print('✅ CuPy:', cp.__version__)
    print('✅ CUDA Runtime:', cp.cuda.runtime.runtimeGetVersion())
    # Test basic GPU operation
    x = cp.array([1, 2, 3, 4, 5])
    y = x * 2
    print('✅ GPU computation test passed')
except ImportError:
    print('⚠️  CuPy not available - CPU-only mode')
except Exception as e:
    print('❌ GPU test failed:', str(e))

print('🎉 Installation test complete!')
"@

$testScript | python

# Run the setup script
Write-Host "`n🚀 Running setup verification..." -ForegroundColor Cyan
if (Test-Path "setup_gpu_acceleration.py") {
    python setup_gpu_acceleration.py
} else {
    Write-Host "⚠️  setup_gpu_acceleration.py not found. Please run it manually later." -ForegroundColor Yellow
}

Write-Host "`n🎉 Installation complete!" -ForegroundColor Green
Write-Host "=" * 50 -ForegroundColor Green

Write-Host "`n📋 Next steps:" -ForegroundColor Cyan
Write-Host "1. Run: python gpu_integrated_trainer.py --benchmark" -ForegroundColor White
Write-Host "2. Run: python gpu_integrated_trainer.py --train 1000" -ForegroundColor White
Write-Host "3. Monitor GPU usage with: nvidia-smi" -ForegroundColor White

Write-Host "`n💡 Tips:" -ForegroundColor Cyan
Write-Host "- GPU acceleration provides 5-20x speedup for simulations" -ForegroundColor White
Write-Host "- Monitor GPU memory usage during training" -ForegroundColor White
Write-Host "- Adjust batch sizes based on available GPU memory" -ForegroundColor White

Read-Host "`nPress Enter to exit"
