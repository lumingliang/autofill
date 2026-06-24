#!/usr/bin/env python3
"""
解析类似 OpenAI Chat Completion 请求/响应的 JSON 文件。
仅保留工具定义和消息中的关键交互内容，并自动将 system prompt 按 Markdown 一级标题拆分。

输出内容：
- tools/：每个工具定义一个 JSON 文件
- messages/：每条消息一个目录
    - content.md
    - content.md 存在且 role 为 system 时，自动生成 sections/ 目录按一级标题拆分
    - reasoning_content.md（assistant 消息存在时）
    - tool_calls/：assistant 的每次调用一个 JSON 文件

不输出 metadata、索引、message.json 等辅助文件。
所有文本文件均保留原始换行。

用法：
    python3 split_json_chat.py /path/to/input.json /path/to/output_dir
"""

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote


def safe_filename(name: str, max_len: int = 80) -> str:
    """生成安全的文件名（保留中文、英文、数字，替换特殊字符）。"""
    name = unquote(name)
    name = re.sub(r'[\\/:*?"<>|\s]+', '_', name)
    name = name.strip('_')
    if not name:
        name = 'untitled'
    if len(name) > max_len:
        name = name[:max_len]
    return name


def write_text(path: Path, content: str):
    """写入文本，保留原始换行。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def write_json(path: Path, data, indent: int = 2):
    """写入严格合法的格式化 JSON。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=indent), encoding='utf-8')


def split_markdown_by_heading(text: str, output_dir: Path):
    """按 Markdown 一级标题拆分，保留原始换行。"""
    output_dir.mkdir(parents=True, exist_ok=True)

    lines = text.splitlines(keepends=True)
    sections = []
    current_title = '__intro__'
    current_lines = []

    for line in lines:
        m = re.match(r'^#\s+(.+?)\s*\n?$', line)
        if m:
            if current_lines:
                sections.append((current_title, ''.join(current_lines)))
            current_title = m.group(1).strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, ''.join(current_lines)))

    for i, (title, content) in enumerate(sections):
        if title == '__intro__':
            filename = '00_intro.md'
        else:
            filename = f"{i:02d}_{safe_filename(title)}.md"
        write_text(output_dir / filename, content)

    return len(sections)


def split_messages(messages: list, out_dir: Path):
    """仅保留消息关键交互内容。"""
    msg_dir = out_dir / 'messages'

    for i, msg in enumerate(messages):
        role = msg.get('role', 'unknown')
        folder_name = f"msg_{i:03d}_{role}"
        msg_subdir = msg_dir / folder_name

        # content：原样保留换行
        content = msg.get('content')
        if isinstance(content, str) and content:
            content_path = msg_subdir / 'content.md'
            write_text(content_path, content)

            # system prompt 自动按章节拆分
            if role == 'system':
                sections_dir = msg_subdir / 'sections'
                split_markdown_by_heading(content, sections_dir)
        elif content is not None and content != '':
            write_json(msg_subdir / 'content.json', content)

        # reasoning_content：原样保留换行
        reasoning = msg.get('reasoning_content')
        if isinstance(reasoning, str) and reasoning:
            write_text(msg_subdir / 'reasoning_content.md', reasoning)

        # assistant 的 tool_calls
        tool_calls = msg.get('tool_calls')
        if tool_calls:
            tc_dir = msg_subdir / 'tool_calls'
            for j, tc in enumerate(tool_calls):
                tc_id = tc.get('id') or tc.get('tool_call_id') or f"tc_{j}"
                tc_name = tc.get('function', {}).get('name', 'unknown')
                tc_file = tc_dir / f"tc_{j:03d}_{safe_filename(tc_name)}_{safe_filename(str(tc_id))[:30]}.json"
                write_json(tc_file, tc)


def split_tools(tools: list, out_dir: Path):
    """每个工具定义保存为严格合法 JSON，并额外生成 Markdown 文件展示换行后的 description。"""
    tools_dir = out_dir / 'tools'

    for i, tool in enumerate(tools):
        func = tool.get('function', {})
        name = func.get('name', f"tool_{i}")
        safe_name = safe_filename(name)
        base_path = tools_dir / f"tool_{i:03d}_{safe_name}"

        # 严格合法的 JSON
        write_json(base_path.with_suffix('.json'), tool)

        # Markdown 版本：description 等字段的 \n 展开为实际换行，便于阅读
        md_lines = [f"# {name}", ""]
        desc = func.get('description')
        if desc:
            md_lines.append(desc.replace('\\n', '\n'))
            md_lines.append("")

        params = func.get('parameters')
        if params:
            md_lines.append("## Parameters")
            md_lines.append("")
            md_lines.append(json.dumps(params, ensure_ascii=False, indent=2))
            md_lines.append("")

        write_text(base_path.with_suffix('.md'), '\n'.join(md_lines))


def main():
    if len(sys.argv) < 3:
        print(f"用法: {sys.argv[0]} <input.json> <output_dir>", file=sys.stderr)
        sys.exit(1)

    input_path = Path(sys.argv[1]).expanduser().resolve()
    output_dir = Path(sys.argv[2]).expanduser().resolve()

    if not input_path.exists():
        print(f"错误：输入文件不存在：{input_path}", file=sys.stderr)
        sys.exit(1)

    # 清空旧输出，避免残留辅助文件
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if not isinstance(data, dict):
        print("错误：顶层 JSON 必须是对象", file=sys.stderr)
        sys.exit(1)

    tools = data.get('tools', [])
    messages = data.get('messages', [])

    if tools:
        split_tools(tools, output_dir)

    if messages:
        split_messages(messages, output_dir)

    print(f"解析完成：{output_dir}")
    print(f"  tools: {len(tools)} 个")
    print(f"  messages: {len(messages)} 条")


if __name__ == '__main__':
    main()
