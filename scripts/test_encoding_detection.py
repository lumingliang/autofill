"""
测试文件编码检测和解析功能
"""
import os
import tempfile

from app.utils.file_parser import (
    detect_encoding,
    decode_content,
    parse_csv_content,
    parse_file,
    convert_to_csv_string,
)


def test_detect_encoding():
    """测试编码检测"""
    print("=" * 60)
    print("测试编码检测")
    print("=" * 60)

    test_cases = [
        ("UTF-8 中文", "utf-8", "你好，世界！Hello World!"),
        ("UTF-8-SIG 中文", "utf-8-sig", "你好，世界！"),
        ("GBK 中文", "gbk", "你好，世界！这是GBK编码测试"),
        ("GB2312 中文", "gb2312", "你好，世界！这是GB2312编码测试"),
        ("GB18030 中文", "gb18030", "你好，世界！这是GB18030编码测试"),
        ("BIG5 繁体中文", "big5", "你好，世界！這是繁體中文測試"),
    ]

    for name, encoding, text in test_cases:
        try:
            content = text.encode(encoding)
            detected, confidence = detect_encoding(content)
            decoded = decode_content(content)
            success = decoded == text
            print(f"\n{name}:")
            print(f"  原始编码: {encoding}")
            print(f"  检测编码: {detected}")
            print(f"  置信度: {confidence:.2%}")
            print(f"  解码成功: {'✓' if success else '✗'}")
            if not success:
                print(f"  解码结果: {decoded}")
        except Exception as e:
            print(f"\n{name}: 错误 - {e}")


def test_csv_parsing():
    """测试CSV解析"""
    print("\n" + "=" * 60)
    print("测试CSV解析")
    print("=" * 60)

    # 测试各种编码的CSV内容
    csv_content = "姓名,年龄,城市\n张三,25,北京\n李四,30,上海\n王五,28,广州"

    for encoding in ["utf-8", "utf-8-sig", "gbk", "gb2312"]:
        try:
            encoded = csv_content.encode(encoding)
            decoded = decode_content(encoded)
            headers, data = parse_csv_content(decoded)
            print(f"\n{encoding}:")
            print(f"  表头: {headers}")
            print(f"  数据行数: {len(data)}")
            print(f"  第一行: {data[0] if data else 'N/A'}")
        except Exception as e:
            print(f"\n{encoding}: 错误 - {e}")


def test_excel_parsing():
    """测试Excel解析"""
    print("\n" + "=" * 60)
    print("测试Excel解析")
    print("=" * 60)

    try:
        import openpyxl
    except ImportError:
        print("openpyxl 未安装，跳过Excel测试")
        return

    # 创建测试Excel文件
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        temp_path = f.name

    try:
        # 创建Excel文件
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "测试数据"

        # 写入表头
        headers = ["姓名", "年龄", "城市"]
        ws.append(headers)

        # 写入数据
        data = [
            ["张三", 25, "北京"],
            ["李四", 30, "上海"],
            ["王五", 28, "广州"],
            ["赵六", 35, "深圳"],
        ]
        for row in data:
            ws.append(row)

        wb.save(temp_path)
        wb.close()

        # 读取并解析
        with open(temp_path, "rb") as f:
            content = f.read()

        parsed_headers, parsed_data, encoding = parse_file(content, "test.xlsx")
        print(f"\nExcel解析结果:")
        print(f"  表头: {parsed_headers}")
        print(f"  数据行数: {len(parsed_data)}")
        print(f"  第一行: {parsed_data[0] if parsed_data else 'N/A'}")
        print(f"  编码: {encoding}")

    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_file_auto_detection():
    """测试文件自动识别"""
    print("\n" + "=" * 60)
    print("测试文件自动识别")
    print("=" * 60)

    # 测试CSV文件
    csv_content = "姓名,年龄\n张三,25\n李四,30"
    csv_bytes = csv_content.encode("utf-8")

    headers, data, encoding = parse_file(csv_bytes, "test.csv")
    print(f"\nCSV文件:")
    print(f"  表头: {headers}")
    print(f"  数据行数: {len(data)}")
    print(f"  检测编码: {encoding}")

    # 测试带BOM的UTF-8
    csv_bytes_bom = csv_content.encode("utf-8-sig")
    headers, data, encoding = parse_file(csv_bytes_bom, "test.csv")
    print(f"\nCSV文件(UTF-8-SIG):")
    print(f"  表头: {headers}")
    print(f"  数据行数: {len(data)}")
    print(f"  检测编码: {encoding}")

    # 测试GBK编码
    csv_bytes_gbk = csv_content.encode("gbk")
    headers, data, encoding = parse_file(csv_bytes_gbk, "test.csv")
    print(f"\nCSV文件(GBK):")
    print(f"  表头: {headers}")
    print(f"  数据行数: {len(data)}")
    print(f"  检测编码: {encoding}")


def test_convert_to_csv():
    """测试转换为CSV字符串"""
    print("\n" + "=" * 60)
    print("测试转换为CSV字符串")
    print("=" * 60)

    headers = ["姓名", "年龄", "城市"]
    data = [
        {"姓名": "张三", "年龄": "25", "城市": "北京"},
        {"姓名": "李四", "年龄": "30", "城市": "上海"},
    ]

    csv_string = convert_to_csv_string(headers, data)
    print("\n转换后的CSV内容:")
    print(csv_string)


if __name__ == "__main__":
    test_detect_encoding()
    test_csv_parsing()
    test_excel_parsing()
    test_file_auto_detection()
    test_convert_to_csv()
    print("\n" + "=" * 60)
    print("所有测试完成!")
    print("=" * 60)
