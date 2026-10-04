import re
import difflib
from typing import Tuple, List, Dict, Any

class OutputNormalizer:
    """Normalizes output strings across programming languages to allow fair behavioral equivalence comparison."""

    @staticmethod
    def normalize_token(token: str) -> str:
        token = token.strip()
        # Normalize boolean representations
        if token.lower() in ["true", "false"]:
            return token.lower()

        # Normalize floating point numbers (e.g. 5.000 -> 5.0)
        try:
            if "." in token:
                f_val = float(token)
                # Keep up to 6 decimal places, strip trailing zeros
                formatted = f"{f_val:.6f}".rstrip("0").rstrip(".")
                return formatted
        except ValueError:
            pass

        return token

    @classmethod
    def normalize_output(cls, output: str) -> str:
        if not output:
            return ""

        # Normalize CRLF to LF
        cleaned = output.replace("\r\n", "\n").replace("\r", "\n")

        # Collapse multiline arrays like Node.js console.log([1, 2,\n 3, 4])
        # Find any [...] spanning multiple lines and replace newlines/extra spaces with single spaces
        def collapse_brackets(match):
            inner = match.group(1)
            # Remove internal newlines and collapse multiple spaces
            inner_clean = " ".join(inner.split())
            return f"[{inner_clean}]"

        cleaned = re.sub(r"\[([\s\S]*?)\]", collapse_brackets, cleaned)

        lines = cleaned.splitlines()
        normalized_lines: List[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue

            # Check if line is an array: [1, 2, 3]
            if stripped.startswith("[") and stripped.endswith("]"):
                inner = stripped[1:-1].strip()
                tokens = [cls.normalize_token(t) for t in re.split(r"[,\s]+", inner) if t]
                normalized_lines.append("[" + ", ".join(tokens) + "]")
            else:
                # Token-based normalization
                tokens = [cls.normalize_token(t) for t in stripped.split()]
                normalized_lines.append(" ".join(tokens))

        return "\n".join(normalized_lines)

    @classmethod
    def compare_outputs(cls, src_out: str, tgt_out: str) -> Tuple[bool, List[str]]:
        norm_src = cls.normalize_output(src_out)
        norm_tgt = cls.normalize_output(tgt_out)

        is_equal = (norm_src == norm_tgt)

        # Generate unified diff
        src_lines = norm_src.splitlines(keepends=True)
        tgt_lines = norm_tgt.splitlines(keepends=True)
        diff = list(difflib.unified_diff(
            src_lines, tgt_lines,
            fromfile="Source Output",
            tofile="Target Output",
            lineterm=""
        ))

        return is_equal, diff
