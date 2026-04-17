"""Запуск вложенных .py-скриптов из одного exe (PyInstaller)."""
import io
import os
import runpy
import subprocess
import sys
from contextlib import redirect_stdout, redirect_stderr
from typing import List, Tuple


def subprocess_argv_for_script(script_path: str) -> List[str]:
    """Argv для отдельного процесса (режим разработки или вспомогательно)."""
    path = os.path.abspath(script_path)
    if getattr(sys, "frozen", False):
        return [sys.executable, "--run-script", path]
    return [sys.executable, path]


def run_stock_script(script_path: str, *, stdin_newline: bool = False) -> Tuple[int, str, str]:
    """
    Выполняет скрипт магазина. В frozen onefile-exe повторный запуск того же .exe
    открывает ещё одно окно (в Win11 часто как «вкладка» у того же приложения).
    Поэтому в сборке exe скрипт запускается здесь же через runpy (в потоке воркера).
    Возвращает (код_выхода, stdout, stderr) как текст.
    """
    script_path = os.path.abspath(script_path)
    if not os.path.isfile(script_path):
        return 1, "", f"Файл не найден: {script_path}"

    if getattr(sys, "frozen", False):
        script_dir = os.path.dirname(script_path) or os.getcwd()
        old_cwd = os.getcwd()
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        code = 0
        try:
            os.chdir(script_dir)
            with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
                try:
                    runpy.run_path(script_path, run_name="__main__")
                except SystemExit as e:
                    c = e.code
                    if c is None:
                        code = 0
                    elif isinstance(c, int):
                        code = c
                    else:
                        code = 1
        finally:
            try:
                os.chdir(old_cwd)
            except Exception:
                pass
        return code, stdout_buf.getvalue(), stderr_buf.getvalue()

    cwd = os.path.dirname(script_path) or None
    cmd = [sys.executable, script_path]
    # Добавляем таймаут 5 минут для выполнения скрипта
    timeout = 300  # 5 минут
    try:
        if stdin_newline:
            proc = subprocess.run(cmd, input="\n", text=True, capture_output=True, cwd=cwd, timeout=timeout)
        else:
            proc = subprocess.run(cmd, text=True, capture_output=True, cwd=cwd, timeout=timeout)
        return proc.returncode, proc.stdout or "", proc.stderr or ""
    except subprocess.TimeoutExpired:
        return 1, "", f"Таймаут: скрипт выполнялся более {timeout} секунд"
