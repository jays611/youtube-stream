#!/usr/bin/env python3
"""
Detailed CPU usage checker
Run this to see exactly how CPU cores are being utilized
"""

import psutil
import time
import subprocess

def check_cpu_details():
    """Check detailed CPU usage"""
    print("=== Detailed CPU Analysis ===")
    
    # CPU info
    cpu_count = psutil.cpu_count()
    cpu_count_logical = psutil.cpu_count(logical=True)
    
    print(f"CPU Cores: {cpu_count} physical, {cpu_count_logical} logical")
    print(f"CPU Frequency: {psutil.cpu_freq()}")
    
    # Check if hyperthreading is enabled
    if cpu_count_logical > cpu_count:
        print("Hyperthreading: ENABLED")
    else:
        print("Hyperthreading: DISABLED")
    
    print("\n=== Real-time CPU Usage ===")
    print("Press Ctrl+C to stop\n")
    
    try:
        while True:
            # Overall CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Per-core CPU
            cpu_per_core = psutil.cpu_percent(interval=0, percpu=True)
            
            # Load average
            load_avg = psutil.getloadavg()
            
            print(f"Overall CPU: {cpu_percent:.1f}%")
            print(f"Load Average: {load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}")
            
            # Show per-core usage
            print("Per-core usage:")
            for i, core_usage in enumerate(cpu_per_core):
                status = "HIGH" if core_usage > 80 else "MED" if core_usage > 40 else "LOW"
                print(f"  Core {i:2d}: {core_usage:5.1f}% [{status}]")
            
            # Check for CPU-intensive processes
            print("\nTop CPU processes:")
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    if proc.info['cpu_percent'] and proc.info['cpu_percent'] > 5:
                        processes.append((proc.info['pid'], proc.info['name'], proc.info['cpu_percent']))
                except:
                    pass
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x[2], reverse=True)
            for pid, name, cpu in processes[:5]:
                print(f"  PID {pid}: {name} - {cpu:.1f}%")
            
            print("-" * 50)
            time.sleep(3)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped")

def check_pytorch_threading():
    """Check PyTorch threading configuration"""
    print("\n=== PyTorch Threading Check ===")
    
    try:
        result = subprocess.run([
            "/root/home_projects/audiocraft/my_venv/bin/python", "-c",
            "import torch; print(f'PyTorch threads: {torch.get_num_threads()}'); print(f'OpenMP threads: {torch.get_num_interop_threads()}')"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("Could not check PyTorch threading")
            
    except Exception as e:
        print(f"Error checking PyTorch: {e}")

def check_system_limits():
    """Check system resource limits"""
    print("\n=== System Limits ===")
    
    try:
        # Check ulimits
        result = subprocess.run(["ulimit", "-a"], capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print("Process limits:")
            for line in result.stdout.split('\n'):
                if 'processes' in line or 'threads' in line or 'cpu' in line:
                    print(f"  {line}")
    except:
        pass
    
    # Check CPU governor
    try:
        with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor', 'r') as f:
            governor = f.read().strip()
            print(f"CPU Governor: {governor}")
    except:
        print("Could not read CPU governor")

if __name__ == "__main__":
    check_cpu_details()
    check_pytorch_threading()
    check_system_limits()