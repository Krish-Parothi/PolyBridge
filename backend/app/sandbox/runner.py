import subprocess
import tempfile
import os
import shutil
import time
from typing import Dict, Any, Optional

class ExecutionResult:
    def __init__(self, stdout: str, stderr: str, exit_code: int, duration_ms: float, error: Optional[str] = None):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.duration_ms = duration_ms
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "duration_ms": round(self.duration_ms, 2),
            "error": self.error
        }

class CodeRunner:
    """Executes source or translated code in an isolated subprocess with timeout."""

    TIMEOUT_SECONDS = 6

    @classmethod
    def run_code(cls, code: str, language: str, stdin_data: str = "") -> ExecutionResult:
        lang = language.lower()
        if lang == "python":
            return cls._run_python(code, stdin_data)
        elif lang in ["javascript", "js", "nodejs"]:
            return cls._run_javascript(code, stdin_data)
        elif lang == "java":
            return cls._run_java(code, stdin_data)
        elif lang in ["go", "golang"]:
            return cls._run_go(code, stdin_data)
        else:
            return ExecutionResult("", f"Unsupported runtime: {language}", -1, 0, "Unsupported runtime")

    @classmethod
    def _run_python(cls, code: str, stdin_data: str) -> ExecutionResult:
        start_time = time.perf_counter()
        try:
            res = subprocess.run(
                ["python", "-c", code],
                input=stdin_data,
                text=True,
                capture_output=True,
                timeout=cls.TIMEOUT_SECONDS
            )
            duration = (time.perf_counter() - start_time) * 1000
            return ExecutionResult(res.stdout, res.stderr, res.returncode, duration)
        except subprocess.TimeoutExpired:
            return ExecutionResult("", f"Execution timed out ({cls.TIMEOUT_SECONDS}s limit exceeded)", -1, cls.TIMEOUT_SECONDS * 1000, "Timeout")
        except Exception as e:
            return ExecutionResult("", str(e), -1, 0, str(e))

    @classmethod
    def _run_javascript(cls, code: str, stdin_data: str) -> ExecutionResult:
        start_time = time.perf_counter()
        try:
            res = subprocess.run(
                ["node", "-e", code],
                input=stdin_data,
                text=True,
                capture_output=True,
                timeout=cls.TIMEOUT_SECONDS
            )
            duration = (time.perf_counter() - start_time) * 1000
            return ExecutionResult(res.stdout, res.stderr, res.returncode, duration)
        except subprocess.TimeoutExpired:
            return ExecutionResult("", f"Execution timed out ({cls.TIMEOUT_SECONDS}s limit exceeded)", -1, cls.TIMEOUT_SECONDS * 1000, "Timeout")
        except Exception as e:
            return ExecutionResult("", str(e), -1, 0, str(e))

    @classmethod
    def _run_java(cls, code: str, stdin_data: str) -> ExecutionResult:
        start_time = time.perf_counter()
        temp_dir = tempfile.mkdtemp(prefix="pb_java_")
        try:
            java_file = os.path.join(temp_dir, "Solution.java")
            with open(java_file, "w", encoding="utf-8") as f:
                f.write(code)

            # Compile
            compile_res = subprocess.run(
                ["javac", "Solution.java"],
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=cls.TIMEOUT_SECONDS
            )
            if compile_res.returncode != 0:
                duration = (time.perf_counter() - start_time) * 1000
                return ExecutionResult("", compile_res.stderr, compile_res.returncode, duration, "Compilation Error")

            # Run
            run_res = subprocess.run(
                ["java", "Solution"],
                cwd=temp_dir,
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=cls.TIMEOUT_SECONDS
            )
            duration = (time.perf_counter() - start_time) * 1000
            return ExecutionResult(run_res.stdout, run_res.stderr, run_res.returncode, duration)
        except subprocess.TimeoutExpired:
            return ExecutionResult("", f"Execution timed out ({cls.TIMEOUT_SECONDS}s limit exceeded)", -1, cls.TIMEOUT_SECONDS * 1000, "Timeout")
        except Exception as e:
            return ExecutionResult("", str(e), -1, 0, str(e))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def _run_go(cls, code: str, stdin_data: str) -> ExecutionResult:
        start_time = time.perf_counter()
        # Check if go command exists
        if not shutil.which("go"):
            return ExecutionResult(
                "",
                "Go compiler ('go') not found in PATH on this system. Please install Go to execute Go programs locally.",
                1,
                0,
                "Go compiler not found"
            )

        temp_dir = tempfile.mkdtemp(prefix="pb_go_")
        try:
            go_file = os.path.join(temp_dir, "main.go")
            with open(go_file, "w", encoding="utf-8") as f:
                f.write(code)

            run_res = subprocess.run(
                ["go", "run", "main.go"],
                cwd=temp_dir,
                input=stdin_data,
                capture_output=True,
                text=True,
                timeout=cls.TIMEOUT_SECONDS
            )
            duration = (time.perf_counter() - start_time) * 1000
            return ExecutionResult(run_res.stdout, run_res.stderr, run_res.returncode, duration)
        except subprocess.TimeoutExpired:
            return ExecutionResult("", f"Execution timed out ({cls.TIMEOUT_SECONDS}s limit exceeded)", -1, cls.TIMEOUT_SECONDS * 1000, "Timeout")
        except Exception as e:
            return ExecutionResult("", str(e), -1, 0, str(e))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
