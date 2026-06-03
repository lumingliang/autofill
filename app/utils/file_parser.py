"""
文件解析工具 - 支持 CSV/Excel 文件解析和自动编码检测
"""
import csv
import io
from typing import Any, Dict, List, Optional, Tuple

import chardet
from app.log import logger


def detect_encoding(content: bytes) -> Tuple[str, float]:
    """
    自动检测文件编码

    Args:
        content: 文件字节内容

    Returns:
        (编码名称, 置信度)
    """
    # 首先尝试检测
    result = chardet.detect(content)
    encoding = result.get('encoding', 'utf-8')
    confidence = result.get('confidence', 0.0)

    # 处理常见的中文编码别名
    encoding = encoding.lower() if encoding else 'utf-8'

    # 编码别名映射
    encoding_aliases = {
        'gb2312': 'gbk',  # GB2312 是 GBK 的子集，用 GBK 更兼容
        'gb18030': 'gb18030',
        'big5': 'big5',
        'utf-8': 'utf-8',
        'utf-8-sig': 'utf-8-sig',
        'ascii': 'utf-8',  # ASCII 是 UTF-8 的子集
    }

    # 标准化编码名称
    normalized_encoding = encoding_aliases.get(encoding, encoding)

    logger.info(
        "编码检测结果",
        raw_encoding=encoding,
        normalized_encoding=normalized_encoding,
        confidence=confidence,
    )

    return normalized_encoding, confidence


def decode_content(content: bytes, preferred_encoding: Optional[str] = None) -> tuple[str, str]:
    """
    解码文件内容，支持自动编码检测

    Args:
        content: 文件字节内容
        preferred_encoding: 优先尝试的编码（如果提供）

    Returns:
        (解码后的字符串, 实际使用的编码)
    """
    # 如果指定了优先编码，先尝试
    if preferred_encoding:
        try:
            decoded = content.decode(preferred_encoding)
            logger.info("使用指定编码成功解码", encoding=preferred_encoding)
            return decoded, preferred_encoding
        except UnicodeDecodeError:
            pass

    # 自动检测编码
    detected_encoding, confidence = detect_encoding(content)

    # 根据置信度调整编码尝试顺序
    # 高置信度(>0.7): 优先使用检测到的编码
    # 低置信度: 优先尝试UTF-8，然后才是检测到的编码
    if confidence > 0.7:
        encodings_to_try = [
            detected_encoding,
            'utf-8',
            'utf-8-sig',
            'gbk',
            'gb18030',
            'gb2312',
            'big5',
            'latin-1',
        ]
    else:
        encodings_to_try = [
            'utf-8',
            'utf-8-sig',
            detected_encoding,
            'gbk',
            'gb18030',
            'gb2312',
            'big5',
            'latin-1',
        ]

    for encoding in encodings_to_try:
        try:
            decoded = content.decode(encoding)
            logger.info("成功解码", encoding=encoding, confidence=confidence)
            return decoded, encoding
        except (UnicodeDecodeError, LookupError):
            continue

    # 如果都失败了，使用 UTF-8 并忽略错误
    logger.warning("所有编码尝试失败，使用 UTF-8 忽略错误模式")
    return content.decode('utf-8', errors='ignore'), 'utf-8'


def parse_csv_content(content: str) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    解析 CSV 内容

    Args:
        content: CSV 字符串内容

    Returns:
        (表头列表, 数据行列表)
    """
    if not content or not content.strip():
        return [], []

    # 处理 BOM
    if content.startswith('\ufeff'):
        content = content[1:]

    reader = csv.DictReader(io.StringIO(content.strip()))
    raw_headers = reader.fieldnames or []
    headers = [h.strip() for h in raw_headers]
    header_mapping = {raw: stripped for raw, stripped in zip(raw_headers, headers)}

    data = []
    for row in reader:
        data.append({header_mapping.get(k, k): v for k, v in row.items()})

    return headers, data


def parse_excel_content(content: bytes, sheet_index: int = 0) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    解析 Excel 内容

    Args:
        content: Excel 文件字节内容
        sheet_index: 工作表索引，默认第一个

    Returns:
        (表头列表, 数据行列表)
    """
    try:
        import openpyxl
    except ImportError:
        raise ImportError("请安装 openpyxl: pip install openpyxl")

    workbook = openpyxl.load_workbook(io.BytesIO(content), data_only=True)

    # 获取指定工作表
    sheet_names = workbook.sheetnames
    if not sheet_names:
        return [], []

    if sheet_index >= len(sheet_names):
        sheet_index = 0

    sheet = workbook[sheet_names[sheet_index]]

    # 读取数据
    rows = []
    for row in sheet.iter_rows(values_only=True):
        rows.append(row)

    if not rows:
        return [], []

    # 第一行作为表头
    headers = [str(cell).strip() if cell is not None else '' for cell in rows[0]]

    # 剩余行作为数据
    data = []
    for row_data in rows[1:]:
        row_dict = {}
        for i, header in enumerate(headers):
            if i < len(row_data):
                # 将单元格值转换为字符串
                cell_value = row_data[i]
                if cell_value is None:
                    row_dict[header] = ''
                elif isinstance(cell_value, (int, float)):
                    row_dict[header] = str(cell_value)
                else:
                    row_dict[header] = str(cell_value).strip()
            else:
                row_dict[header] = ''
        data.append(row_dict)

    return headers, data


def parse_excel_xls_content(content: bytes, sheet_index: int = 0) -> Tuple[List[str], List[Dict[str, str]]]:
    """
    解析旧版 Excel (.xls) 内容

    Args:
        content: Excel 文件字节内容
        sheet_index: 工作表索引，默认第一个

    Returns:
        (表头列表, 数据行列表)
    """
    try:
        import xlrd
    except ImportError:
        raise ImportError("请安装 xlrd: pip install xlrd")

    workbook = xlrd.open_workbook(file_contents=content)

    # 获取指定工作表
    if sheet_index >= workbook.nsheets:
        sheet_index = 0

    sheet = workbook.sheet_by_index(sheet_index)

    if sheet.nrows == 0:
        return [], []

    # 第一行作为表头
    headers = [str(sheet.cell_value(0, col)).strip() for col in range(sheet.ncols)]

    # 剩余行作为数据
    data = []
    for row_idx in range(1, sheet.nrows):
        row_dict = {}
        for col_idx, header in enumerate(headers):
            if col_idx < sheet.ncols:
                cell_value = sheet.cell_value(row_idx, col_idx)
                if cell_value is None:
                    row_dict[header] = ''
                elif isinstance(cell_value, (int, float)):
                    row_dict[header] = str(cell_value)
                else:
                    row_dict[header] = str(cell_value).strip()
            else:
                row_dict[header] = ''
        data.append(row_dict)

    return headers, data


def parse_file(
    content: bytes,
    filename: str,
    preferred_encoding: Optional[str] = None,
    sheet_index: int = 0
) -> Tuple[List[str], List[Dict[str, str]], str]:
    """
    自动识别文件类型并解析

    Args:
        content: 文件字节内容
        filename: 文件名（用于判断文件类型）
        preferred_encoding: 优先尝试的编码（CSV文件使用）
        sheet_index: Excel 工作表索引

    Returns:
        (表头列表, 数据行列表, 检测到的编码)
    """
    filename_lower = filename.lower()

    # 检测编码（仅用于日志记录，Excel不需要）
    detected_encoding = 'utf-8'

    if filename_lower.endswith('.csv'):
        # CSV 文件
        decoded_content, detected_encoding = decode_content(content, preferred_encoding)
        headers, data = parse_csv_content(decoded_content)
        return headers, data, detected_encoding

    elif filename_lower.endswith('.xlsx'):
        # Excel 2007+ 格式
        headers, data = parse_excel_content(content, sheet_index)
        return headers, data, 'utf-8'

    elif filename_lower.endswith('.xls'):
        # Excel 97-2003 格式
        headers, data = parse_excel_xls_content(content, sheet_index)
        return headers, data, 'utf-8'

    else:
        # 尝试作为 CSV 解析
        try:
            decoded_content, detected_encoding = decode_content(content, preferred_encoding)
            headers, data = parse_csv_content(decoded_content)
            return headers, data, detected_encoding
        except Exception as e:
            raise ValueError(f"不支持的文件格式: {filename}") from e


def convert_to_csv_string(headers: List[str], data: List[Dict[str, str]]) -> str:
    """
    将数据转换为 CSV 字符串

    Args:
        headers: 表头列表
        data: 数据行列表

    Returns:
        CSV 格式字符串
    """
    if not headers:
        return ''

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=headers)
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()
