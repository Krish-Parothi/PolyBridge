import pytest
from app.parsers.python_parser import PythonParser
from app.parsers.js_parser import JavaScriptParser
from app.parsers.java_parser import JavaParser
from app.parsers.go_parser import GoParser

from app.emitters.python_emitter import PythonEmitter
from app.emitters.js_emitter import JavaScriptEmitter
from app.emitters.java_emitter import JavaEmitter
from app.emitters.go_emitter import GoEmitter

from app.ir.type_infer import TypeInferrer
from app.sandbox.runner import CodeRunner

PARSERS = {
    "python": PythonParser(),
    "javascript": JavaScriptParser(),
    "java": JavaParser(),
    "go": GoParser()
}

EMITTERS = {
    "python": PythonEmitter(),
    "javascript": JavaScriptEmitter(),
    "java": JavaEmitter(),
    "go": GoEmitter()
}

def transpile(code: str, from_lang: str, to_lang: str) -> str:
    parser = PARSERS[from_lang]
    prog = parser.parse(code)
    inferrer = TypeInferrer()
    prog = inferrer.infer_program(prog)
    return EMITTERS[to_lang].emit(prog)

ALGORITHMS = {
    "bubble_sort": {
        "python": """def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                temp = arr[j]
                arr[j] = arr[j + 1]
                arr[j + 1] = temp
    return arr

a = [64, 34, 25, 12, 22, 11, 90]
res = bubble_sort(a)
print(res)
""",
        "javascript": """function bubble_sort(arr) {
    let n = arr.length;
    for (let i = 0; i < n; i = i + 1) {
        for (let j = 0; j < n - i - 1; j = j + 1) {
            if (arr[j] > arr[j + 1]) {
                let temp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = temp;
            }
        }
    }
    return arr;
}
let a = [64, 34, 25, 12, 22, 11, 90];
let res = bubble_sort(a);
console.log(res);
""",
        "java": """public class Solution {
    public static int[] bubble_sort(int[] arr) {
        int n = arr.length;
        for (int i = 0; i < n; i = i + 1) {
            for (int j = 0; j < n - i - 1; j = j + 1) {
                if (arr[j] > arr[j + 1]) {
                    int temp = arr[j];
                    arr[j] = arr[j + 1];
                    arr[j + 1] = temp;
                }
            }
        }
        return arr;
    }
    public static void main(String[] args) {
        int[] a = {64, 34, 25, 12, 22, 11, 90};
        int[] res = bubble_sort(a);
        System.out.println(res);
    }
}
""",
        "go": """package main
import "fmt"
func bubble_sort(arr []int) []int {
    n := len(arr)
    for i := 0; i < n; i = i + 1 {
        for j := 0; j < n - i - 1; j = j + 1 {
            if arr[j] > arr[j + 1] {
                temp := arr[j]
                arr[j] = arr[j + 1]
                arr[j + 1] = temp
            }
        }
    }
    return arr
}
func main() {
    a := []int{64, 34, 25, 12, 22, 11, 90}
    res := bubble_sort(a)
    fmt.Println(res)
}
"""
    },
    "fibonacci": {
        "python": """def fibonacci(n):
    if n <= 1:
        return n
    a = 0
    b = 1
    for i in range(2, n + 1):
        c = a + b
        a = b
        b = c
    return b

res = fibonacci(10)
print(res)
""",
        "javascript": """function fibonacci(n) {
    if (n <= 1) {
        return n;
    }
    let a = 0;
    let b = 1;
    for (let i = 2; i <= n; i = i + 1) {
        let c = a + b;
        a = b;
        b = c;
    }
    return b;
}
let res = fibonacci(10);
console.log(res);
""",
        "java": """public class Solution {
    public static int fibonacci(int n) {
        if (n <= 1) {
            return n;
        }
        int a = 0;
        int b = 1;
        for (int i = 2; i <= n; i = i + 1) {
            int c = a + b;
            a = b;
            b = c;
        }
        return b;
    }
    public static void main(String[] args) {
        int res = fibonacci(10);
        System.out.println(res);
    }
}
""",
        "go": """package main
import "fmt"
func fibonacci(n int) int {
    if n <= 1 {
        return n
    }
    a := 0
    b := 1
    for i := 2; i <= n; i = i + 1 {
        c := a + b
        a = b
        b = c
    }
    return b
}
func main() {
    res := fibonacci(10)
    fmt.Println(res)
}
"""
    },
    "binary_search": {
        "python": """def binary_search(arr, target):
    low = 0
    high = len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        else:
            if arr[mid] < target:
                low = mid + 1
            else:
                high = mid - 1
    return -1

nums = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91]
target = 23
idx = binary_search(nums, target)
print(idx)
""",
        "javascript": """function binary_search(arr, target) {
    let low = 0;
    let high = arr.length - 1;
    while (low <= high) {
        let mid = Math.floor((low + high) / 2);
        if (arr[mid] === target) {
            return mid;
        } else {
            if (arr[mid] < target) {
                low = mid + 1;
            } else {
                high = mid - 1;
            }
        }
    }
    return -1;
}
let nums = [2, 5, 8, 12, 16, 23, 38, 56, 72, 91];
let target = 23;
let idx = binary_search(nums, target);
console.log(idx);
""",
        "java": """public class Solution {
    public static int binary_search(int[] arr, int target) {
        int low = 0;
        int high = arr.length - 1;
        while (low <= high) {
            int mid = (low + high) / 2;
            if (arr[mid] == target) {
                return mid;
            } else {
                if (arr[mid] < target) {
                    low = mid + 1;
                } else {
                    high = mid - 1;
                }
            }
        }
        return -1;
    }
    public static void main(String[] args) {
        int[] nums = {2, 5, 8, 12, 16, 23, 38, 56, 72, 91};
        int target = 23;
        int idx = binary_search(nums, target);
        System.out.println(idx);
    }
}
""",
        "go": """package main
import "fmt"
func binary_search(arr []int, target int) int {
    low := 0
    high := len(arr) - 1
    for low <= high {
        mid := (low + high) / 2
        if arr[mid] == target {
            return mid
        } else {
            if arr[mid] < target {
                low = mid + 1
            } else {
                high = mid - 1
            }
        }
    }
    return -1
}
func main() {
    nums := []int{2, 5, 8, 12, 16, 23, 38, 56, 72, 91}
    target := 23
    idx := binary_search(nums, target)
    fmt.Println(idx)
}
"""
    }
}

LANGUAGES = ["python", "javascript", "java", "go"]

TEST_CASES = []
for algo_name, langs in ALGORITHMS.items():
    for src_lang in LANGUAGES:
        for tgt_lang in LANGUAGES:
            if src_lang != tgt_lang:
                TEST_CASES.append((algo_name, src_lang, tgt_lang))

@pytest.mark.parametrize("algo_name,src_lang,tgt_lang", TEST_CASES)
def test_transpile_algorithm_matrix(algo_name, src_lang, tgt_lang):
    src_code = ALGORITHMS[algo_name][src_lang]
    target_code = transpile(src_code, src_lang, tgt_lang)
    assert len(target_code.strip()) > 0
    
    # Target code should parse successfully with target parser
    target_ir = PARSERS[tgt_lang].parse(target_code)
    assert target_ir is not None
    assert len(target_ir.functions) > 0 or len(target_ir.global_statements) > 0
