from typing import Dict, List, Optional, Tuple, Set, Any

class LibraryRegistry:
    """Universal deterministic mapping registry for Standard Libraries and External Packages across:
    - Python
    - JavaScript
    - Java
    - Go
    - C++
    """

    # Math library canonical mappings
    MATH_FUNCTIONS = {
        "sqrt": {"python": "math.sqrt", "java": "Math.sqrt", "javascript": "Math.sqrt", "go": "math.Sqrt", "cpp": "std::sqrt"},
        "pow": {"python": "math.pow", "java": "Math.pow", "javascript": "Math.pow", "go": "math.Pow", "cpp": "std::pow"},
        "floor": {"python": "math.floor", "java": "Math.floor", "javascript": "Math.floor", "go": "math.Floor", "cpp": "std::floor"},
        "ceil": {"python": "math.ceil", "java": "Math.ceil", "javascript": "Math.ceil", "go": "math.Ceil", "cpp": "std::ceil"},
        "abs": {"python": "abs", "java": "Math.abs", "javascript": "Math.abs", "go": "math.Abs", "cpp": "std::abs"},
        "sin": {"python": "math.sin", "java": "Math.sin", "javascript": "Math.sin", "go": "math.Sin", "cpp": "std::sin"},
        "cos": {"python": "math.cos", "java": "Math.cos", "javascript": "Math.cos", "go": "math.Cos", "cpp": "std::cos"},
        "tan": {"python": "math.tan", "java": "Math.tan", "javascript": "Math.tan", "go": "math.Tan", "cpp": "std::tan"},
        "log": {"python": "math.log", "java": "Math.log", "javascript": "Math.log", "go": "math.Log", "cpp": "std::log"},
        "exp": {"python": "math.exp", "java": "Math.exp", "javascript": "Math.exp", "go": "math.Exp", "cpp": "std::exp"},
        "round": {"python": "round", "java": "Math.round", "javascript": "Math.round", "go": "math.Round", "cpp": "std::round"},
    }

    MATH_CONSTANTS = {
        "pi": {"python": "math.pi", "java": "Math.PI", "javascript": "Math.PI", "go": "math.Pi", "cpp": "M_PI"},
        "e": {"python": "math.e", "java": "Math.E", "javascript": "Math.E", "go": "math.E", "cpp": "M_E"},
    }

    # Third-party / Data Packages (e.g. pandas <-> tablesaw <-> danfojs <-> gota <-> rapidcsv)
    DATAFRAME_MODULES = {
        "python": ["pandas"],
        "java": ["tech.tablesaw.api.Table", "tech.tablesaw.api.*"],
        "javascript": ["danfojs", "danfojs-node"],
        "go": ["github.com/go-gota/gota/dataframe"],
        "cpp": ["rapidcsv.h"]
    }

    DATAFRAME_IMPORTS = {
        "python": "import pandas as pd",
        "java": "import tech.tablesaw.api.Table;",
        "javascript": 'const dfd = require("danfojs-node");',
        "go": 'import "github.com/go-gota/gota/dataframe"',
        "cpp": '#include "rapidcsv.h"'
    }

    # Known standard imports needed when math functions are used
    MATH_IMPORTS = {
        "python": "import math",
        "java": None,  # java.lang.Math is auto-imported in Java
        "javascript": None,  # Math is a global object in JS
        "go": '"math"',
        "cpp": "#include <cmath>"
    }

    SUPPORTED_MODULES = {
        "math", "cmath", "pandas", "numpy", "collections",
        "java.lang.Math", "java.util.Math", "java.util.Arrays", "java.util.ArrayList",
        "java.util.List", "java.util.Map", "java.util.HashMap", "tech.tablesaw.api.Table",
        "danfojs", "danfojs-node", "fmt", "math"
    }

    @classmethod
    def is_supported_module(cls, module_name: str) -> bool:
        """Checks if a module or package import is supported."""
        clean = module_name.strip()
        if clean in cls.SUPPORTED_MODULES:
            return True
        for m in cls.SUPPORTED_MODULES:
            if clean.startswith(m) or m.startswith(clean):
                return True
        return False

    @classmethod
    def resolve_call(
        cls,
        func_name: str,
        args_strs: List[str],
        target_lang: str,
        imported_aliases: Optional[Dict[str, str]] = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """Resolves a function or method call to target language syntax and returns:
        (translated_call_code, required_header_or_import)

        Examples:
          "math.sqrt" with ["16"] in java -> ("Math.sqrt(16)", None)
          "math.sqrt" with ["16"] in go -> ("math.Sqrt(16)", '"math"')
          "pd.read_csv" with ['"data.csv"'] in java -> ('Table.read().csv("data.csv")', 'import tech.tablesaw.api.Table;')
        """
        aliases = imported_aliases or {}
        parts = func_name.split(".")
        joined_args = ", ".join(args_strs)

        # 1. Math Functions Resolution
        # Matches: math.sqrt, Math.sqrt, std::sqrt, or direct sqrt if imported
        if len(parts) == 2 and parts[0].lower() in ["math", "std"]:
            op = parts[1].lower()
            if op in cls.MATH_FUNCTIONS:
                mapping = cls.MATH_FUNCTIONS[op].get(target_lang)
                if mapping:
                    req_imp = cls.MATH_IMPORTS.get(target_lang)
                    return f"{mapping}({joined_args})", req_imp

        elif len(parts) == 1 and parts[0].lower() in cls.MATH_FUNCTIONS:
            # Standalone function like abs(x) or sqrt(x)
            op = parts[0].lower()
            mapping = cls.MATH_FUNCTIONS[op].get(target_lang)
            if mapping:
                req_imp = cls.MATH_IMPORTS.get(target_lang)
                return f"{mapping}({joined_args})", req_imp

        # 2. Third-Party DataFrame Mappings (pandas / pd)
        if len(parts) == 2:
            base, method = parts[0], parts[1]
            resolved_base = aliases.get(base, base)

            # NumPy Mappings (numpy / np)
            if (resolved_base in ["numpy", "np"] or base in ["np", "numpy"]):
                if method in ["array", "asarray"]:
                    arg = args_strs[0] if args_strs else "[]"
                    if target_lang == "python":
                        return f"np.array({arg})", "import numpy as np"
                    elif target_lang == "javascript":
                        return f"{arg}", None
                    elif target_lang == "java":
                        return f"{arg}", "import java.util.Arrays;"
                    elif target_lang == "go":
                        return f"{arg}", None
                    elif target_lang == "cpp":
                        return f"{arg}", None

                if method == "zeros":
                    sz = args_strs[0] if args_strs else "0"
                    if target_lang == "python":
                        return f"np.zeros({sz})", "import numpy as np"
                    elif target_lang == "javascript":
                        return f"new Array({sz}).fill(0)", None
                    elif target_lang == "java":
                        return f"new int[{sz}]", None
                    elif target_lang == "go":
                        return f"make([]int, {sz})", None
                    elif target_lang == "cpp":
                        return f"std::vector<int>({sz}, 0)", "#include <vector>"

                if method == "sum":
                    arg = args_strs[0] if args_strs else "arr"
                    if target_lang == "python":
                        return f"np.sum({arg})", "import numpy as np"
                    elif target_lang == "javascript":
                        return f"{arg}.reduce((a, b) => a + b, 0)", None
                    elif target_lang == "java":
                        return f"Arrays.stream({arg}).sum()", "import java.util.Arrays;"
                    elif target_lang == "go":
                        return f"sum({arg})", None
                    elif target_lang == "cpp":
                        return f"std::accumulate({arg}.begin(), {arg}.end(), 0)", "#include <numeric>"

                if method in ["max", "amax"]:
                    arg = args_strs[0] if args_strs else "arr"
                    if target_lang == "python":
                        return f"np.max({arg})", "import numpy as np"
                    elif target_lang == "javascript":
                        return f"Math.max(...{arg})", None
                    elif target_lang == "java":
                        return f"Arrays.stream({arg}).max().getAsInt()", "import java.util.Arrays;"

                if method in ["min", "amin"]:
                    arg = args_strs[0] if args_strs else "arr"
                    if target_lang == "python":
                        return f"np.min({arg})", "import numpy as np"
                    elif target_lang == "javascript":
                        return f"Math.min(...{arg})", None
                    elif target_lang == "java":
                        return f"Arrays.stream({arg}).min().getAsInt()", "import java.util.Arrays;"

            # DataFrame file reader: pd.read_csv(...)
            if (resolved_base in ["pandas", "pd"] or base in ["pd", "pandas"]) and method == "read_csv":
                req_imp = cls.DATAFRAME_IMPORTS.get(target_lang)
                if target_lang == "python":
                    return f"pd.read_csv({joined_args})", req_imp
                elif target_lang == "java":
                    return f"Table.read().csv({joined_args})", req_imp
                elif target_lang == "javascript":
                    return f"dfd.readCSV({joined_args})", req_imp
                elif target_lang == "go":
                    return f"dataframe.ReadCSV({joined_args})", req_imp
                elif target_lang == "cpp":
                    return f"rapidcsv::Document({joined_args})", req_imp

            # DataFrame instance methods: df.head(n), df.tail(n)
            if method in ["head", "first"]:
                n_arg = args_strs[0] if args_strs else "5"
                if target_lang == "python":
                    return f"{base}.head({n_arg})", None
                elif target_lang == "java":
                    return f"{base}.first({n_arg})", None
                elif target_lang == "javascript":
                    return f"{base}.head({n_arg})", None
                elif target_lang == "go":
                    return f"{base}.Subset(0, {n_arg})", None
                elif target_lang == "cpp":
                    return f"{base}.GetRow({n_arg})", None

            if method in ["tail", "last"]:
                n_arg = args_strs[0] if args_strs else "5"
                if target_lang == "python":
                    return f"{base}.tail({n_arg})", None
                elif target_lang == "java":
                    return f"{base}.last({n_arg})", None
                elif target_lang == "javascript":
                    return f"{base}.tail({n_arg})", None
                elif target_lang == "go":
                    return f"{base}.Subset({base}.Nrow() - {n_arg}, {base}.Nrow())", None

            # Collections/List methods: arr.append(x) -> list.add(x) / arr.push(x) / arr.push_back(x)
            if method in ["append", "add", "push"]:
                item_arg = args_strs[0] if args_strs else ""
                if target_lang == "python":
                    return f"{base}.append({item_arg})", None
                elif target_lang == "java":
                    return f"{base}.add({item_arg})", None
                elif target_lang == "javascript":
                    return f"{base}.push({item_arg})", None
                elif target_lang == "go":
                    return f"{base} = append({base}, {item_arg})", None
                elif target_lang == "cpp":
                    return f"{base}.push_back({item_arg})", None

            if method in ["pop", "remove_last"]:
                if target_lang == "python":
                    return f"{base}.pop()", None
                elif target_lang == "java":
                    return f"{base}.remove({base}.size() - 1)", None
                elif target_lang == "javascript":
                    return f"{base}.pop()", None
                elif target_lang == "cpp":
                    return f"{base}.pop_back()", None

        return None, None

    @classmethod
    def get_target_imports(cls, used_modules: Set[str], target_lang: str) -> List[str]:
        """Returns required import/include statements for the target language."""
        imports: List[str] = []

        if "math" in used_modules:
            imp = cls.MATH_IMPORTS.get(target_lang)
            if imp and imp not in imports:
                imports.append(imp)

        if "pandas" in used_modules or "dataframe" in used_modules:
            imp = cls.DATAFRAME_IMPORTS.get(target_lang)
            if imp and imp not in imports:
                imports.append(imp)

        return imports
