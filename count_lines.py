import os
import re

def count_effective_lines(file_path):
    """统计有效代码行数（排除空行和注释）"""
    total = 0
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith('#'):
                    total += 1
    except Exception:
        pass
    return total

def count_dir(dir_path):
    """统计目录下所有Python文件的有效行数"""
    total = 0
    if not os.path.exists(dir_path):
        return 0
    for root, _, files in os.walk(dir_path):
        for f in files:
            if f.endswith('.py'):
                path = os.path.join(root, f)
                total += count_effective_lines(path)
    return total

def main():
    print('=' * 60)
    print('  CODE STATISTICS')
    print('=' * 60)
    print('')
    
    # 总后端代码
    app_lines = count_dir('app')
    print(f'Backend (app/)      : {app_lines:>6} lines')
    print('')
    
    # 细分
    parts = [
        ('app/api', 'API Layer'),
        ('app/controllers', 'Controllers'),
        ('app/services', 'Services'), 
        ('app/models', 'Models'),
        ('app/core', 'Core'),
        ('app/schemas', 'Schemas'),
    ]
    
    print('Breakdown:')
    print('-' * 40)
    for dirname, name in parts:
        lines = count_dir(dirname)
        print(f'  {name:15} : {lines:>6} lines')
    
    print('')
    print('=' * 60)
    
    # public 相关
    public_dirs = [
        'app/api/public',
        'app/services/autofill', 
        'app/schemas/public'
    ]
    public_total = 0
    for d in public_dirs:
        public_total += count_dir(d)
    print(f'Public API Related  : {public_total:>6} lines')
    print('')
    
    # 单个大文件统计
    big_files = [
        ('app/api/public/handlers/field_spec_handlers.py', 'Field Spec Handlers'),
        ('app/api/public/handlers/field_group_handlers.py', 'Field Group Handlers'),
        ('app/api/public/handlers/fill_data_handlers.py', 'Fill Data Handlers'),
        ('app/services/autofill/ai_fill_service.py', 'AI Fill Service'),
        ('app/controllers/autofill.py', 'Autofill Controller'),
    ]
    
    print('Top Large Files:')
    print('-' * 40)
    for path, name in big_files:
        lines = count_effective_lines(path)
        if lines > 0:
            print(f'  {name:25} : {lines:>5} lines')

if __name__ == '__main__':
    main()
