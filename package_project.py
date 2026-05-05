#!/usr/bin/env python3
"""
项目打包脚本
打包整个项目，排除不必要的文件和目录

使用方法:
    python package_project.py

输出:
    autofill_project_<timestamp>.tar.gz
"""

import os
import tarfile
import sys
from datetime import datetime
from pathlib import Path


def read_exclude_patterns(exclude_file: str) -> list:
    """读取排除列表文件"""
    patterns = []
    if os.path.exists(exclude_file):
        with open(exclude_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释
                if line and not line.startswith('#'):
                    patterns.append(line)
    return patterns


def should_exclude(file_path: str, exclude_patterns: list, project_root: str) -> bool:
    """检查文件是否应该被排除"""
    # 转换为相对路径进行匹配
    rel_path = os.path.relpath(file_path, project_root)
    
    for pattern in exclude_patterns:
        # 处理目录模式（以 / 结尾）
        if pattern.endswith('/'):
            pattern = pattern.rstrip('/')
            # 检查路径的任何部分是否匹配
            path_parts = rel_path.split(os.sep)
            if pattern in path_parts:
                return True
            # 检查完整路径是否以 pattern 开头
            if rel_path.startswith(pattern + os.sep) or rel_path == pattern:
                return True
        else:
            # 处理文件模式
            # 检查文件名是否匹配
            if os.path.basename(rel_path) == pattern:
                return True
            # 检查通配符模式
            if '*' in pattern:
                import fnmatch
                if fnmatch.fnmatch(os.path.basename(rel_path), pattern):
                    return True
                if fnmatch.fnmatch(rel_path, pattern):
                    return True
            # 检查路径是否以 pattern 结尾
            if rel_path.endswith(pattern):
                return True
            # 检查路径的任何部分是否匹配
            path_parts = rel_path.split(os.sep)
            if pattern in path_parts:
                return True
    
    return False


def create_package(project_root: str, output_file: str, exclude_patterns: list):
    """创建项目打包文件"""
    print(f"开始打包项目...")
    print(f"项目目录: {project_root}")
    print(f"输出文件: {output_file}")
    print(f"排除规则数: {len(exclude_patterns)}")
    
    included_count = 0
    excluded_count = 0
    
    with tarfile.open(output_file, "w:gz") as tar:
        for root, dirs, files in os.walk(project_root):
            # 过滤掉应该被排除的目录（优化性能）
            dirs_to_remove = []
            for d in dirs:
                dir_path = os.path.join(root, d)
                if should_exclude(dir_path, exclude_patterns, project_root):
                    dirs_to_remove.append(d)
                    excluded_count += 1
                    print(f"  [排除目录] {os.path.relpath(dir_path, project_root)}")
            
            for d in dirs_to_remove:
                dirs.remove(d)
            
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_root)
                
                if should_exclude(file_path, exclude_patterns, project_root):
                    excluded_count += 1
                    if excluded_count <= 20:  # 只显示前20个排除的文件
                        print(f"  [排除文件] {rel_path}")
                    elif excluded_count == 21:
                        print(f"  ... 更多文件被排除 ...")
                else:
                    # 添加到 tar 包
                    arcname = os.path.join("autofill", rel_path)
                    tar.add(file_path, arcname=arcname)
                    included_count += 1
    
    print(f"\n打包完成!")
    print(f"  包含文件数: {included_count}")
    print(f"  排除文件/目录数: {excluded_count}")
    print(f"  输出文件: {output_file}")
    
    # 显示文件大小
    file_size = os.path.getsize(output_file)
    print(f"  文件大小: {file_size / 1024 / 1024:.2f} MB")


def main():
    """主函数"""
    # 获取项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = script_dir
    
    # 读取排除列表
    exclude_file = os.path.join(project_root, "exclude_list.txt")
    exclude_patterns = read_exclude_patterns(exclude_file)
    
    # 添加额外的排除项
    additional_excludes = [
        # 打包脚本本身
        "package_project.py",
        # 输出文件
        "autofill_project_*.tar.gz",
        # Python 缓存
        "__pycache__",
        "*.pyc",
        # 虚拟环境
        "venv",
        ".venv",
        "env",
        "ENV",
    ]
    exclude_patterns.extend(additional_excludes)
    
    # 生成输出文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(project_root, f"autofill_project_{timestamp}.tar.gz")
    
    # 检查是否在项目根目录
    if not os.path.exists(os.path.join(project_root, "requirements.txt")):
        print("错误: 请在项目根目录运行此脚本")
        sys.exit(1)
    
    # 创建打包
    create_package(project_root, output_file, exclude_patterns)
    
    print(f"\n提示: 可以使用以下命令解压:")
    print(f"  tar -xzf {os.path.basename(output_file)}")


if __name__ == "__main__":
    main()
