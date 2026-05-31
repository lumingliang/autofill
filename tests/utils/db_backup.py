import os
import subprocess
import datetime
from typing import Optional

class DatabaseBackup:
    def __init__(self):
        self.backup_dir = os.path.join(os.path.dirname(__file__), "backups")
        self.backup_file: Optional[str] = None
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def backup(self, db_name: str = "autofill") -> str:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.backup_file = os.path.join(self.backup_dir, f"backup_{timestamp}.sql")
        
        print(f"📦 正在备份数据库 {db_name}...")
        
        try:
            result = subprocess.run([
                "mysqldump",
                "--single-transaction",
                "--quick",
                "--lock-tables=false",
                "-u", os.getenv("DB_USER", "root"),
                f"-p{os.getenv('DB_PASSWORD', '')}",
                db_name
            ], capture_output=True, text=True, check=True)
            
            with open(self.backup_file, "w", encoding="utf-8") as f:
                f.write(result.stdout)
            
            print(f"✓ 数据库备份成功: {self.backup_file}")
            return self.backup_file
            
        except subprocess.CalledProcessError as e:
            print(f"✗ 数据库备份失败: {e.stderr}")
            raise
    
    def restore(self, db_name: str = "autofill") -> bool:
        if not self.backup_file or not os.path.exists(self.backup_file):
            print("⚠ 没有可用的备份文件")
            return False
        
        print(f"📥 正在恢复数据库 {db_name}...")
        
        try:
            with open(self.backup_file, "r", encoding="utf-8") as f:
                dump_content = f.read()
            
            result = subprocess.run([
                "mysql",
                "-u", os.getenv("DB_USER", "root"),
                f"-p{os.getenv('DB_PASSWORD', '')}",
                "-e", f"DROP DATABASE IF EXISTS {db_name}; CREATE DATABASE {db_name}; USE {db_name};"
            ], capture_output=True, text=True, check=True)
            
            result = subprocess.run([
                "mysql",
                "-u", os.getenv("DB_USER", "root"),
                f"-p{os.getenv('DB_PASSWORD', '')}",
                db_name
            ], input=dump_content, capture_output=True, text=True, check=True)
            
            print(f"✓ 数据库恢复成功")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ 数据库恢复失败: {e.stderr}")
            return False
    
    def cleanup_old_backups(self, keep_count: int = 5):
        """清理旧备份文件，只保留最新的N个"""
        backups = sorted([
            os.path.join(self.backup_dir, f) 
            for f in os.listdir(self.backup_dir) 
            if f.startswith("backup_") and f.endswith(".sql")
        ], reverse=True)
        
        for old_backup in backups[keep_count:]:
            os.remove(old_backup)
            print(f"🗑️ 清理旧备份: {old_backup}")

db_backup = DatabaseBackup()
