#!/usr/bin/env python3
"""
测试 seekdb Docker 部署连接
"""
import sys
sys.path.insert(0, '/Users/lu/code/code/py/autofill')

import pyseekdb
from app.log import logger

def test_seekdb_connection():
    """测试 seekdb 远程连接"""
    print("=" * 50)
    print("测试 seekdb Docker 部署连接")
    print("=" * 50)
    
    # 连接配置
    host = "127.0.0.1"
    port = 2881
    user = "root"
    password = "seekdb123456"
    database = "autofill"
    
    try:
        # 1. 测试 AdminClient 连接
        print("\n1. 测试 AdminClient 连接...")
        admin = pyseekdb.AdminClient(
            host=host,
            port=port,
            user=user,
            password=password
        )
        print("   ✓ AdminClient 连接成功")
        
        # 2. 列出所有数据库
        print("\n2. 列出所有数据库...")
        databases = admin.list_databases()
        print(f"   现有数据库: {[db.name for db in databases]}")
        
        # 3. 创建测试数据库
        print(f"\n3. 创建数据库 '{database}'...")
        try:
            admin.create_database(database)
            print(f"   ✓ 数据库 '{database}' 创建成功")
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"   ℹ 数据库 '{database}' 已存在")
            else:
                raise
        
        # 4. 测试 Client 连接
        print(f"\n4. 测试 Client 连接到数据库 '{database}'...")
        client = pyseekdb.Client(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        print("   ✓ Client 连接成功")
        
        # 5. 创建测试集合
        print("\n5. 创建测试集合...")
        collection_name = "test_collection"
        collection = client.get_or_create_collection(collection_name)
        print(f"   ✓ 集合 '{collection_name}' 创建/获取成功")
        
        # 6. 插入测试数据
        print("\n6. 插入测试数据...")
        collection.add(
            ids=["test_1", "test_2"],
            documents=["测试文档1", "测试文档2"],
            metadatas=[
                {"source": "test", "type": "doc1"},
                {"source": "test", "type": "doc2"}
            ]
        )
        print("   ✓ 测试数据插入成功")
        
        # 7. 查询数据
        print("\n7. 查询测试数据...")
        results = collection.get()
        print(f"   ✓ 查询成功，共 {len(results['ids'])} 条数据")
        print(f"     IDs: {results['ids']}")
        
        # 8. 清理测试数据
        print("\n8. 清理测试数据...")
        client.delete_collection(collection_name)
        print(f"   ✓ 集合 '{collection_name}' 已删除")
        
        print("\n" + "=" * 50)
        print("✓ 所有测试通过！seekdb Docker 部署成功")
        print("=" * 50)
        return True
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_seekdb_connection()
    sys.exit(0 if success else 1)
