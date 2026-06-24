"""
命令管理器 - 管理异步命令执行

全局单例，通过 asyncio.Semaphore 限制同时运行的子进程数量，防止进程暴增。
"""
import asyncio
import re
import shlex
import uuid
from datetime import datetime
from typing import Any, Dict, Optional


class CommandManager:
    """管理异步命令执行（全局单例 + 并发限流）"""

    def __init__(self, max_concurrent: int = 5):
        self._commands: Dict[str, Dict[str, Any]] = {}
        self._max_concurrent = max(1, max_concurrent)
        self._semaphore = asyncio.Semaphore(self._max_concurrent)

    def create_command(
        self,
        command: str,
        cwd: Optional[str] = None,
        blocking: bool = True,
        wait_ms: int = 0,
    ) -> str:
        """创建命令记录"""
        command_id = str(uuid.uuid4())
        self._commands[command_id] = {
            "id": command_id,
            "command": command,
            "cwd": cwd,
            "blocking": blocking,
            "wait_ms": wait_ms,
            "status": "created",
            "pid": None,
            "process": None,
            "output": "",
            "error": "",
            "exit_code": None,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "stopped_at": None,
        }
        return command_id

    def get_command(self, command_id: str) -> Optional[Dict[str, Any]]:
        """获取命令信息"""
        return self._commands.get(command_id)

    def update_command(self, command_id: str, **kwargs) -> None:
        """更新命令信息"""
        if command_id in self._commands:
            self._commands[command_id].update(kwargs)

    @property
    def max_concurrent(self) -> int:
        return self._max_concurrent

    @property
    def active_slots(self) -> int:
        """当前已被占用的并发槽位数。"""
        return self._max_concurrent - self._semaphore._value

    async def run_blocking(
        self,
        command_id: str,
        command: str,
        cwd: Optional[str] = None,
        timeout: Optional[int] = 300,
    ) -> Dict[str, Any]:
        """在 Semaphore 限流保护下同步阻塞执行命令。

        占用一个并发槽位直到命令结束。
        """
        work_dir = cwd if cwd else "."
        cmd_args = shlex.split(command)

        async with self._semaphore:
            self.update_command(
                command_id,
                status="running",
                started_at=datetime.now().isoformat(),
            )
            try:
                process = await asyncio.wait_for(
                    asyncio.create_subprocess_exec(
                        *cmd_args,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                        cwd=work_dir,
                    ),
                    timeout=10.0,
                )
            except asyncio.TimeoutError:
                return {
                    "status": "error",
                    "exit_code": None,
                    "error": "Timed out waiting to start command (too many commands running)",
                }

            self.update_command(command_id, pid=process.pid, process=process)

            stdout_data, stderr_data = await process.communicate()
            stdout_text = stdout_data.decode("utf-8", errors="replace") if stdout_data else ""
            stderr_text = stderr_data.decode("utf-8", errors="replace") if stderr_data else ""

            status = "completed" if process.returncode == 0 else "error"
            self.update_command(
                command_id,
                status=status,
                exit_code=process.returncode,
                output=stdout_text,
                error=stderr_text,
                completed_at=datetime.now().isoformat(),
            )
            return {
                "status": status,
                "exit_code": process.returncode,
                "output": stdout_text,
                "error": stderr_text,
            }

    async def start_command(
        self,
        command_id: str,
        command: str,
        cwd: Optional[str] = None,
        wait_ms: int = 0,
    ) -> int:
        """以非阻塞方式启动子进程并后台读取输出。

        通过 Semaphore 限制同时运行的进程数；启动成功后立即返回 pid，
        Semaphore 槽位由后台 _watch_process 任务释放。

        Args:
            wait_ms: 启动后等待的毫秒数，用于观察早期错误。

        Returns:
            进程 pid
        """
        work_dir = cwd if cwd else "."
        cmd_args = shlex.split(command)

        # 等待获取并发槽位（防止进程暴增）
        await self._semaphore.acquire()

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
            )

            self.update_command(
                command_id,
                status="running",
                pid=process.pid,
                process=process,
                started_at=datetime.now().isoformat(),
            )

            if wait_ms and wait_ms > 0:
                await asyncio.sleep(min(wait_ms / 1000.0, 1.0))

            # 后台任务持续读取输出，并在结束时释放 Semaphore 槽位
            asyncio.create_task(self._watch_process(command_id, process))
            return process.pid
        except Exception:
            # 启动失败时立即释放槽位
            self._semaphore.release()
            raise

    async def _watch_process(self, command_id: str, process: asyncio.subprocess.Process) -> None:
        """后台读取子进程输出并在结束时更新状态、释放并发槽位。"""
        try:
            stdout_data, stderr_data = await process.communicate()

            stdout_text = stdout_data.decode("utf-8", errors="replace") if stdout_data else ""
            stderr_text = stderr_data.decode("utf-8", errors="replace") if stderr_data else ""

            exit_code = process.returncode
            cmd = self.get_command(command_id)
            if cmd and cmd.get("status") == "stopped":
                final_status = "stopped"
            elif exit_code == 0:
                final_status = "completed"
            else:
                final_status = "error"

            self.update_command(
                command_id,
                status=final_status,
                exit_code=exit_code,
                output=stdout_text,
                error=stderr_text,
                completed_at=datetime.now().isoformat(),
            )
        finally:
            self._semaphore.release()

    async def stop_command(self, command_id: str) -> bool:
        """终止指定命令。先 terminate，不响应则 kill。"""
        cmd = self.get_command(command_id)
        if not cmd:
            return False

        process = cmd.get("process")
        if process is None:
            return False

        try:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()

            self.update_command(
                command_id,
                status="stopped",
                exit_code=process.returncode,
                stopped_at=datetime.now().isoformat(),
                completed_at=datetime.now().isoformat(),
            )
            return True
        except Exception:
            return False

    def get_output_slice(
        self,
        command_id: str,
        output_character_count: int = 2000,
        output_priority: str = "bottom",
        skip_character_count: int = 0,
        filter_regex: Optional[str] = None,
    ) -> Dict[str, Any]:
        """按要求截取命令输出。"""
        cmd = self.get_command(command_id)
        if not cmd:
            return {"error": "Command not found"}

        text = cmd.get("output", "") or ""
        error_text = cmd.get("error", "") or ""

        # 合并 stdout 和 stderr
        combined = text
        if error_text:
            combined += "\n" + error_text

        if filter_regex:
            try:
                lines = combined.splitlines()
                pattern = re.compile(filter_regex)
                combined = "\n".join(line for line in lines if pattern.search(line))
            except re.error:
                pass

        total = len(combined)
        if output_character_count <= 0:
            return {
                "text": "",
                "total_characters": total,
                "has_more": skip_character_count < total,
            }

        if output_priority == "top":
            start = skip_character_count
            end = start + output_character_count
            result = combined[start:end]
        elif output_priority == "bottom":
            end = max(0, total - skip_character_count)
            start = max(0, end - output_character_count)
            result = combined[start:end]
        else:  # split
            half = output_character_count // 2
            head = combined[skip_character_count : skip_character_count + half]
            tail_start = max(skip_character_count + half, total - half)
            tail = combined[tail_start:]
            result = head + ("\n...(some characters truncated)...\n" if head and tail else "") + tail

        return {
            "text": result,
            "total_characters": total,
            "has_more": skip_character_count + output_character_count < total,
        }


# 全局命令管理器实例
command_manager = CommandManager()
