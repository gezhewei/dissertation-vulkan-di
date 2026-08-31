#!/usr/bin/env python3
"""
NVIDIA RTX 3070 Laptop GPU 自动化基准测试脚本
在暗影精灵 7 上运行，收集第 5 章所需的实验数据
"""

import subprocess
import sys
import os
import json
import csv
from pathlib import Path
from datetime import datetime
import wmi

def get_system_info():
    """收集系统硬件和软件信息"""
    info = {}
    
    # GPU 信息
    c = wmi.WMI()
    for gpu in c.Win32_VideoController():
        if '3070' in gpu.Name or 'RTX' in gpu.Name:
            info['gpu_name'] = gpu.Name
            info['gpu_driver'] = gpu.DriverVersion
            # VRAM 通常在 AdapterRAM 字段（单位是字节）
            if gpu.AdapterRAM:
                info['gpu_vram_gb'] = round(gpu.AdapterRAM / (1024**3), 1)
            break
    
    # CPU 信息
    for cpu in c.Win32_Processor():
        info['cpu'] = cpu.Name
        info['cpu_cores'] = cpu.NumberOfCores
        break
    
    # 内存
    for cs in c.Win32_ComputerSystem():
        info['ram_gb'] = round(cs.TotalPhysicalMemory / (1024**3), 1)
        break
    
    # 操作系统
    for os_info in c.Win32_OperatingSystem():
        info['os'] = f"{os_info.Caption}, build {os_info.BuildNumber}"
        break
    
    return info

def run_experiment(config_name, args, output_dir):
    """运行单个实验配置"""
    print(f"\n{'='*60}")
    print(f"Running: {config_name}")
    print(f"Args: {args}")
    print(f"{'='*60}")
    
    csv_path = output_dir / f"{config_name}.csv"
    screenshot_path = output_dir / f"{config_name}.png"
    
    cmd = [
        str(RESTIR_EXE),
        f"--scene={SCENE_PATH}",
        "--benchmark",
        f"--warmup_frames={WARMUP_FRAMES}",
        f"--measure_frames={MEASURE_FRAMES}",
        f"--light_seed={LIGHT_SEED}",
        f"--camera_position={CAMERA_POS}",
        f"--camera_look_at={CAMERA_LOOKAT}",
        f"--frame_times_csv={csv_path}",
        f"--screenshot_frame={SCREENSHOT_FRAME}",
        f"--screenshot_path={screenshot_path}",
    ] + args
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120  # 2 分钟超时
        )
        
        if result.returncode != 0:
            print(f"ERROR: Process failed with code {result.returncode}")
            print(f"STDERR: {result.stderr}")
            return None
        
        # 解析输出获取平均帧时间
        for line in result.stdout.split('\n'):
            if 'Mean frame time:' in line:
                print(line)
                break
        
        return {
            'config': config_name,
            'csv_path': str(csv_path),
            'screenshot_path': str(screenshot_path),
            'stdout': result.stdout
        }
    
    except subprocess.TimeoutExpired:
        print(f"ERROR: Process timed out after 120 seconds")
        return None
    except Exception as e:
        print(f"ERROR: {e}")
        return None

def parse_csv_stats(csv_path):
    """从 CSV 文件解析帧时间统计"""
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        times = [float(row['time_ms']) for row in reader if row['frame'].isdigit()]
    
    if not times:
        return None
    
    mean_ms = sum(times) / len(times)
    fps = 1000.0 / mean_ms
    
    return {
        'mean_ms': round(mean_ms, 3),
        'fps': round(fps, 2),
        'samples': len(times)
    }

def main():
    # 配置
    global RESTIR_EXE, SCENE_PATH, WARMUP_FRAMES, MEASURE_FRAMES
    global LIGHT_SEED, CAMERA_POS, CAMERA_LOOKAT, SCREENSHOT_FRAME
    
    RESTIR_EXE = Path(r"E:\dis\build\vs2026\bin\Release\ReSTIR.exe")
    SCENE_PATH = r"E:\dis\scenes\Sponza\glTF\Sponza.gltf"
    WARMUP_FRAMES = 300
    MEASURE_FRAMES = 1000
    LIGHT_SEED = 42
    CAMERA_POS = "-5,2,0"
    CAMERA_LOOKAT = "5,3,0"
    SCREENSHOT_FRAME = 500
    
    # 输出目录
    output_dir = Path(r"E:\dis\benchmark_nvidia_results")
    output_dir.mkdir(exist_ok=True)
    
    print("="*60)
    print("NVIDIA RTX 3070 Laptop GPU Benchmark")
    print("="*60)
    
    # 收集系统信息
    print("\nCollecting system information...")
    sys_info = get_system_info()
    print(json.dumps(sys_info, indent=2, ensure_ascii=False))
    
    # 保存系统信息
    with open(output_dir / "system_info.json", 'w', encoding='utf-8') as f:
        json.dump(sys_info, f, indent=2, ensure_ascii=False)
    
    # 定义实验配置
    experiments = [
        # 消融实验（3 组，每组重复 3 次）
        ("initial_only", ["--temporal_reuse=false", "--spatial_iterations=0"]),
        ("temporal_only", ["--temporal_reuse=true", "--spatial_iterations=0"]),
        ("complete_biased", ["--temporal_reuse=true", "--spatial_iterations=1"]),
        
        # 可见性路径对比（2 组，每组重复 3 次）
        ("visibility_hardware", ["--visibility=hardware", "--temporal_reuse=true", "--spatial_iterations=1"]),
        ("visibility_software", ["--visibility=software", "--temporal_reuse=true", "--spatial_iterations=1"]),
    ]
    
    results = {}
    
    # 运行实验（每组重复 3 次）
    for config_name, args in experiments:
        runs = []
        for run_idx in range(3):
            run_name = f"{config_name}_run{run_idx+1}"
            print(f"\n[{config_name}] Run {run_idx+1}/3")
            
            result = run_experiment(run_name, args, output_dir)
            if result:
                stats = parse_csv_stats(result['csv_path'])
                if stats:
                    runs.append(stats)
                    print(f"  Mean: {stats['mean_ms']} ms, {stats['fps']} FPS")
        
        if runs:
            # 计算 3 次运行的平均
            avg_ms = sum(r['mean_ms'] for r in runs) / len(runs)
            avg_fps = sum(r['fps'] for r in runs) / len(runs)
            
            results[config_name] = {
                'runs': runs,
                'mean_ms': round(avg_ms, 3),
                'mean_fps': round(avg_fps, 2),
                'screenshot': str(output_dir / f"{config_name}_run1.png")
            }
            
            print(f"\n[{config_name}] Final: {results[config_name]['mean_ms']} ms, {results[config_name]['mean_fps']} FPS")
    
    # 保存汇总结果
    summary = {
        'timestamp': datetime.now().isoformat(),
        'system_info': sys_info,
        'experiments': results
    }
    
    with open(output_dir / "summary.json", 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # 打印表格格式的结果（方便复制到论文）
    print("\n" + "="*60)
    print("Results Summary (for paper)")
    print("="*60)
    
    print("\nTable 5.2: Core ReSTIR configurations")
    print(f"Initial only:        {results['initial_only']['mean_ms']:7.3f} ms, {results['initial_only']['mean_fps']:6.2f} FPS")
    print(f"Temporal only:       {results['temporal_only']['mean_ms']:7.3f} ms, {results['temporal_only']['mean_fps']:6.2f} FPS")
    print(f"Complete biased:     {results['complete_biased']['mean_ms']:7.3f} ms, {results['complete_biased']['mean_fps']:6.2f} FPS")
    
    print("\nTable 5.4: Visibility paths")
    print(f"Hardware RT:         {results['visibility_hardware']['mean_ms']:7.3f} ms, {results['visibility_hardware']['mean_fps']:6.2f} FPS")
    print(f"Compute AABB:        {results['visibility_software']['mean_ms']:7.3f} ms, {results['visibility_software']['mean_fps']:6.2f} FPS")
    
    print(f"\nAll results saved to: {output_dir}")
    print("Please send the entire 'benchmark_nvidia_results' folder back to me.")

if __name__ == "__main__":
    main()
