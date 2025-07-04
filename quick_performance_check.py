#!/usr/bin/env python3
"""
Quick performance check script
"""
import psutil
import time
import subprocess

def check_gpu_memory():
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits'], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            memory_info = result.stdout.strip().split('\n')[0].split(', ')
            used_mb = int(memory_info[0])
            total_mb = int(memory_info[1])
            used_gb = used_mb / 1024
            total_gb = total_mb / 1024
            usage_percent = (used_mb / total_mb) * 100
            return used_gb, total_gb, usage_percent
    except:
        pass
    return None, None, None

def check_system():
    print("🖥️  System Performance Check")
    print("=" * 40)
    
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"CPU Usage: {cpu_percent:.1f}%")
    
    # RAM
    memory = psutil.virtual_memory()
    ram_gb = memory.total / (1024**3)
    ram_used_gb = memory.used / (1024**3)
    ram_percent = memory.percent
    print(f"RAM Usage: {ram_used_gb:.1f}GB / {ram_gb:.1f}GB ({ram_percent:.1f}%)")
    
    # GPU
    gpu_used, gpu_total, gpu_percent = check_gpu_memory()
    if gpu_used is not None:
        print(f"GPU Memory: {gpu_used:.1f}GB / {gpu_total:.1f}GB ({gpu_percent:.1f}%)")
    else:
        print("GPU Memory: Unable to check")
    
    # Python processes
    python_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'cpu_percent']):
        try:
            if 'python' in proc.info['name'].lower():
                memory_mb = proc.info['memory_info'].rss / (1024 * 1024)
                python_processes.append((proc.info['pid'], proc.info['name'], memory_mb, proc.info['cpu_percent']))
        except:
            pass
    
    if python_processes:
        print(f"\nPython Processes ({len(python_processes)}):")
        for pid, name, memory_mb, cpu in python_processes:
            print(f"  PID {pid}: {name} - {memory_mb:.0f}MB RAM, {cpu:.1f}% CPU")

if __name__ == "__main__":
    check_system()
