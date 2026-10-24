from typing import Dict, Any, List

EXAMPLES: Dict[str, Dict[str, Any]] = {
    "bubble_sort": {
        "title": "Bubble Sort",
        "category": "Sorting",
        "description": "Iterative bubble sort algorithm sorting an array in ascending order.",
        "language": "python",
        "code": """def bubble_sort(arr):
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
"""
    },
    "binary_search": {
        "title": "Binary Search",
        "category": "Searching",
        "description": "Iterative binary search returning index of target or -1.",
        "language": "python",
        "code": """def binary_search(arr, target):
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
"""
    },
    "fibonacci": {
        "title": "Fibonacci Sequence",
        "category": "Mathematics",
        "description": "Iterative calculation of the nth Fibonacci number.",
        "language": "python",
        "code": """def fibonacci(n):
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
"""
    },
    "is_prime": {
        "title": "Prime Number Check",
        "category": "Mathematics",
        "description": "Iterative primality test checking divisibility up to sqrt(n).",
        "language": "python",
        "code": """def is_prime(n):
    if n <= 1:
        return False
    i = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i = i + 1
    return True

print(is_prime(29))
print(is_prime(30))
"""
    },
    "factorial": {
        "title": "Iterative Factorial",
        "category": "Mathematics",
        "description": "Calculates factorial of a positive integer iteratively.",
        "language": "python",
        "code": """def factorial(n):
    result = 1
    for i in range(1, n + 1):
        result = result * i
    return result

print(factorial(6))
"""
    },
    "linear_search": {
        "title": "Linear Search",
        "category": "Searching",
        "description": "Sequentially searches an array for target element.",
        "language": "python",
        "code": """def linear_search(arr, target):
    n = len(arr)
    for i in range(n):
        if arr[i] == target:
            return i
    return -1

items = [10, 20, 30, 40, 50]
print(linear_search(items, 30))
print(linear_search(items, 99))
"""
    },
    "math_operations": {
        "title": "Math Library Demo",
        "category": "Standard Library",
        "description": "Uses math functions (sqrt, pow, floor) mapped across languages.",
        "language": "python",
        "code": """import math

x = 16
root = math.sqrt(x)
power = math.pow(2, 8)
flr = math.floor(3.75)
print(root, power, flr)
"""
    },
    "dataframe_pandas": {
        "title": "Data Package (Pandas)",
        "category": "Packages",
        "description": "Demonstrates pandas dataframe operations mapped deterministically.",
        "language": "python",
        "code": """import pandas as pd

df = pd.read_csv("data.csv")
top = df.head(5)
print(top)
"""
    },
    "numpy_operations": {
        "title": "NumPy Array Operations",
        "category": "Packages",
        "description": "Demonstrates numpy arrays, zeros, sum, max, and min operations mapped deterministically.",
        "language": "python",
        "code": """import numpy as np

arr = np.array([10, 20, 30, 40, 50])
total = np.sum(arr)
max_val = np.max(arr)
min_val = np.min(arr)
print(total, max_val, min_val)
"""
    },
    "recursive_factorial": {
        "title": "Recursive Factorial",
        "category": "Recursion",
        "description": "Calculates factorial using pure functional recursion across languages.",
        "language": "python",
        "code": """def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

ans = factorial(5)
print(ans)
"""
    },
    "recursive_fibonacci": {
        "title": "Recursive Fibonacci",
        "category": "Recursion",
        "description": "Classic branching recursion calculating the nth Fibonacci number.",
        "language": "python",
        "code": """def fib(n):
    if n <= 0:
        return 0
    if n == 1:
        return 1
    return fib(n - 1) + fib(n - 2)

res = fib(7)
print(res)
"""
    },
    "gcd_euclid": {
        "title": "Euclidean GCD",
        "category": "Mathematics",
        "description": "Greatest Common Divisor using recursive Euclidean modulo reduction.",
        "language": "python",
        "code": """def gcd(a, b):
    if b == 0:
        return a
    return gcd(b, a % b)

ans = gcd(48, 18)
        print(ans)
"""
    },
    "selection_sort": {
        "title": "Selection Sort", "category": "Sorting",
        "description": "In-place selection sort with an explicit minimum index.", "language": "python",
        "code": """def selection_sort(arr):
    for i in range(len(arr)):
        smallest = i
        for j in range(i + 1, len(arr)):
            if arr[j] < arr[smallest]:
                smallest = j
        arr[i], arr[smallest] = arr[smallest], arr[i]
    return arr

print(selection_sort([64, 25, 12, 22, 11]))
"""
    },
    "insertion_sort": {
        "title": "Insertion Sort", "category": "Sorting",
        "description": "Stable insertion sort for small arrays.", "language": "python",
        "code": """def insertion_sort(arr):
    for i in range(1, len(arr)):
        value = arr[i]
        j = i - 1
        while j >= 0 and arr[j] > value:
            arr[j + 1] = arr[j]
            j = j - 1
        arr[j + 1] = value
    return arr

print(insertion_sort([12, 11, 13, 5, 6]))
"""
    },
    "merge_sort": {
        "title": "Merge Sort", "category": "Sorting",
        "description": "Recursive divide-and-conquer merge sort.", "language": "python",
        "code": """def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])
    result = []
    while left and right:
        if left[0] <= right[0]:
            result.append(left.pop(0))
        else:
            result.append(right.pop(0))
    return result + left + right

print(merge_sort([38, 27, 43, 3, 9, 82, 10]))
"""
    },
    "quick_sort": {
        "title": "Quick Sort", "category": "Sorting",
        "description": "Recursive quick sort using a pivot partition.", "language": "python",
        "code": """def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    lower = [value for value in arr if value < pivot]
    equal = [value for value in arr if value == pivot]
    higher = [value for value in arr if value > pivot]
    return quick_sort(lower) + equal + quick_sort(higher)

print(quick_sort([10, 7, 8, 9, 1, 5]))
"""
    },
    "palindrome_check": {
        "title": "Palindrome Check", "category": "Strings",
        "description": "Two-pointer palindrome check.", "language": "python",
        "code": """def is_palindrome(text):
    left = 0
    right = len(text) - 1
    while left < right:
        if text[left] != text[right]:
            return False
        left = left + 1
        right = right - 1
    return True

print(is_palindrome("level"))
print(is_palindrome("compiler"))
"""
    },
    "string_reverse": {
        "title": "String Reversal", "category": "Strings",
        "description": "Builds a reversed string without library-specific helpers.", "language": "python",
        "code": """def reverse_text(text):
    result = ""
    for i in range(len(text) - 1, -1, -1):
        result = result + text[i]
    return result

print(reverse_text("PolyBridge"))
"""
    },
    "matrix_operations": {
        "title": "Matrix Addition", "category": "Arrays",
        "description": "Element-wise addition of two two-dimensional arrays.", "language": "python",
        "code": """def add_matrices(left, right):
    result = []
    for i in range(len(left)):
        row = []
        for j in range(len(left[i])):
            row.append(left[i][j] + right[i][j])
        result.append(row)
    return result

print(add_matrices([[1, 2], [3, 4]], [[5, 6], [7, 8]]))
"""
    }
}

# Language-specific examples are intentionally kept as real source programs,
# not labels attached to Python text.  The UI filters these records by the
# selected source language, so a user never receives code for another parser.
LANGUAGE_VARIANTS: List[Dict[str, Any]] = [
    {
        "id": "bubble_sort_javascript", "algorithm_id": "bubble_sort", "title": "Bubble Sort",
        "category": "Sorting", "description": "Idiomatic ES6 bubble sort.", "language": "javascript",
        "code": """function bubble_sort(arr) {\n    for (let i = 0; i < arr.length; i++) {\n        for (let j = 0; j < arr.length - i - 1; j++) {\n            if (arr[j] > arr[j + 1]) {\n                const temp = arr[j];\n                arr[j] = arr[j + 1];\n                arr[j + 1] = temp;\n            }\n        }\n    }\n    return arr;\n}\n\nconsole.log(bubble_sort([5, 1, 4, 2, 8]));\n""",
    },
    {
        "id": "binary_search_javascript", "algorithm_id": "binary_search", "title": "Binary Search",
        "category": "Searching", "description": "Iterative ES6 binary search.", "language": "javascript",
        "code": """function binary_search(arr, target) {\n    let low = 0;\n    let high = arr.length - 1;\n    while (low <= high) {\n        const mid = Math.floor((low + high) / 2);\n        if (arr[mid] === target) return mid;\n        if (arr[mid] < target) low = mid + 1;\n        else high = mid - 1;\n    }\n    return -1;\n}\n\nconsole.log(binary_search([2, 5, 8, 12, 16], 12));\n""",
    },
    {
        "id": "fibonacci_javascript", "algorithm_id": "fibonacci", "title": "Fibonacci",
        "category": "Mathematics", "description": "Iterative ES6 Fibonacci sequence.", "language": "javascript",
        "code": """function fibonacci(n) {\n    let a = 0;\n    let b = 1;\n    for (let i = 0; i < n; i++) {\n        const next = a + b;\n        a = b;\n        b = next;\n    }\n    return a;\n}\n\nconsole.log(fibonacci(10));\n""",
    },
    {
        "id": "palindrome_javascript", "algorithm_id": "palindrome", "title": "Palindrome Check",
        "category": "Strings", "description": "Two-pointer palindrome check in ES6.", "language": "javascript",
        "code": """function is_palindrome(text) {\n    let left = 0;\n    let right = text.length - 1;\n    while (left < right) {\n        if (text[left] !== text[right]) return false;\n        left = left + 1;\n        right = right - 1;\n    }\n    return true;\n}\n\nconsole.log(is_palindrome(\"level\"));\n""",
    },
    {
        "id": "bubble_sort_java", "algorithm_id": "bubble_sort", "title": "Bubble Sort",
        "category": "Sorting", "description": "Java 17 bubble sort over an int array.", "language": "java",
        "code": """public class Solution {\n    public static int[] bubble_sort(int[] arr) {\n        for (int i = 0; i < arr.length; i++) {\n            for (int j = 0; j < arr.length - i - 1; j++) {\n                if (arr[j] > arr[j + 1]) {\n                    int temp = arr[j]; arr[j] = arr[j + 1]; arr[j + 1] = temp;\n                }\n            }\n        }\n        return arr;\n    }\n    public static void main(String[] args) {\n        int[] values = bubble_sort(new int[]{5, 1, 4, 2, 8});\n        for (int value : values) System.out.println(value);\n    }\n}\n""",
    },
    {
        "id": "binary_search_java", "algorithm_id": "binary_search", "title": "Binary Search",
        "category": "Searching", "description": "Java 17 iterative binary search.", "language": "java",
        "code": """public class Solution {\n    public static int binary_search(int[] arr, int target) {\n        int low = 0, high = arr.length - 1;\n        while (low <= high) {\n            int mid = (low + high) / 2;\n            if (arr[mid] == target) return mid;\n            if (arr[mid] < target) low = mid + 1; else high = mid - 1;\n        }\n        return -1;\n    }\n    public static void main(String[] args) {\n        System.out.println(binary_search(new int[]{2, 5, 8, 12, 16}, 12));\n    }\n}\n""",
    },
    {
        "id": "fibonacci_java", "algorithm_id": "fibonacci", "title": "Fibonacci",
        "category": "Mathematics", "description": "Java 17 iterative Fibonacci.", "language": "java",
        "code": """public class Solution {\n    public static int fibonacci(int n) {\n        int a = 0, b = 1;\n        for (int i = 0; i < n; i++) { int next = a + b; a = b; b = next; }\n        return a;\n    }\n    public static void main(String[] args) { System.out.println(fibonacci(10)); }\n}\n""",
    },
    {
        "id": "gcd_java", "algorithm_id": "gcd_euclid", "title": "Euclidean GCD",
        "category": "Mathematics", "description": "Java 17 Euclidean algorithm.", "language": "java",
        "code": """public class Solution {\n    public static int gcd(int a, int b) {\n        while (b != 0) { int next = a % b; a = b; b = next; }\n        return a;\n    }\n    public static void main(String[] args) { System.out.println(gcd(48, 18)); }\n}\n""",
    },
    {
        "id": "bubble_sort_go", "algorithm_id": "bubble_sort", "title": "Bubble Sort",
        "category": "Sorting", "description": "Go 1.21 bubble sort over a slice.", "language": "go",
        "code": """package main\n\nimport \"fmt\"\n\nfunc bubble_sort(values []int) []int {\n    for i := 0; i < len(values); i++ {\n        for j := 0; j < len(values)-i-1; j++ {\n            if values[j] > values[j+1] { values[j], values[j+1] = values[j+1], values[j] }\n        }\n    }\n    return values\n}\n\nfunc main() { fmt.Println(bubble_sort([]int{5, 1, 4, 2, 8})) }\n""",
    },
    {
        "id": "binary_search_go", "algorithm_id": "binary_search", "title": "Binary Search",
        "category": "Searching", "description": "Go 1.21 iterative binary search.", "language": "go",
        "code": """package main\n\nimport \"fmt\"\n\nfunc binary_search(values []int, target int) int {\n    low, high := 0, len(values)-1\n    for low <= high {\n        mid := (low + high) / 2\n        if values[mid] == target { return mid }\n        if values[mid] < target { low = mid + 1 } else { high = mid - 1 }\n    }\n    return -1\n}\n\nfunc main() { fmt.Println(binary_search([]int{2, 5, 8, 12, 16}, 12)) }\n""",
    },
    {
        "id": "fibonacci_go", "algorithm_id": "fibonacci", "title": "Fibonacci",
        "category": "Mathematics", "description": "Go 1.21 iterative Fibonacci.", "language": "go",
        "code": """package main\n\nimport \"fmt\"\n\nfunc fibonacci(n int) int {\n    a, b := 0, 1\n    for i := 0; i < n; i++ { a, b = b, a+b }\n    return a\n}\n\nfunc main() { fmt.Println(fibonacci(10)) }\n""",
    },
    {
        "id": "gcd_go", "algorithm_id": "gcd_euclid", "title": "Euclidean GCD",
        "category": "Mathematics", "description": "Go 1.21 iterative Euclidean algorithm.", "language": "go",
        "code": """package main\n\nimport \"fmt\"\n\nfunc gcd(a, b int) int {\n    for b != 0 { a, b = b, a%b }\n    return a\n}\n\nfunc main() { fmt.Println(gcd(48, 18)) }\n""",
    },
    {
        "id": "bubble_sort_cpp", "algorithm_id": "bubble_sort", "title": "Bubble Sort",
        "category": "Sorting", "description": "C++20 bubble sort using std::vector.", "language": "cpp",
        "code": """#include <iostream>\n#include <vector>\n\nstd::vector<int> bubble_sort(std::vector<int> values) {\n    for (int i = 0; i < values.size(); i++) {\n        for (int j = 0; j < values.size() - i - 1; j++) {\n            if (values[j] > values[j + 1]) std::swap(values[j], values[j + 1]);\n        }\n    }\n    return values;\n}\n\nint main() {\n    for (int value : bubble_sort({5, 1, 4, 2, 8})) std::cout << value << std::endl;\n}\n""",
    },
    {
        "id": "binary_search_cpp", "algorithm_id": "binary_search", "title": "Binary Search",
        "category": "Searching", "description": "C++20 binary search over std::vector.", "language": "cpp",
        "code": """#include <iostream>\n#include <vector>\n\nint binary_search(const std::vector<int>& values, int target) {\n    int low = 0, high = static_cast<int>(values.size()) - 1;\n    while (low <= high) {\n        int mid = (low + high) / 2;\n        if (values[mid] == target) return mid;\n        if (values[mid] < target) low = mid + 1; else high = mid - 1;\n    }\n    return -1;\n}\n\nint main() { std::cout << binary_search({2, 5, 8, 12, 16}, 12) << std::endl; }\n""",
    },
    {
        "id": "fibonacci_cpp", "algorithm_id": "fibonacci", "title": "Fibonacci",
        "category": "Mathematics", "description": "C++20 iterative Fibonacci.", "language": "cpp",
        "code": """#include <iostream>\n\nint fibonacci(int n) {\n    int a = 0, b = 1;\n    for (int i = 0; i < n; i++) { int next = a + b; a = b; b = next; }\n    return a;\n}\n\nint main() { std::cout << fibonacci(10) << std::endl; }\n""",
    },
    {
        "id": "gcd_cpp", "algorithm_id": "gcd_euclid", "title": "Euclidean GCD",
        "category": "Mathematics", "description": "C++20 Euclidean algorithm.", "language": "cpp",
        "code": """#include <iostream>\n\nint gcd(int a, int b) {\n    while (b != 0) { int next = a % b; a = b; b = next; }\n    return a;\n}\n\nint main() { std::cout << gcd(48, 18) << std::endl; }\n""",
    },
    {
        "id": "serial_sum_arduino", "algorithm_id": "array_sum", "title": "Serial Array Sum",
        "category": "Arduino", "description": "Hardware-independent Arduino Serial example.", "language": "arduino",
        "code": """int array_sum(int values[], int size) {\n    int total = 0;\n    for (int i = 0; i < size; i++) total += values[i];\n    return total;\n}\n\nvoid setup() {\n    Serial.begin(9600);\n    int values[] = {10, 20, 30};\n    Serial.println(array_sum(values, 3));\n}\n\nvoid loop() {}\n""",
    },
    {
        "id": "serial_fibonacci_arduino", "algorithm_id": "fibonacci", "title": "Serial Fibonacci",
        "category": "Arduino", "description": "Arduino sketch with deterministic Serial output.", "language": "arduino",
        "code": """int fibonacci(int n) {\n    int a = 0, b = 1;\n    for (int i = 0; i < n; i++) { int next = a + b; a = b; b = next; }\n    return a;\n}\n\nvoid setup() {\n    Serial.begin(9600);\n    Serial.println(fibonacci(10));\n}\n\nvoid loop() {}\n""",
    },
    {
        "id": "hdl_adder_verilog", "algorithm_id": "adder", "title": "Combinational Adder",
        "category": "Verilog / HDL", "description": "Verilog 2001 combinational RTL with a simulation testbench.", "language": "verilog",
        "code": """module adder(input wire [31:0] a, input wire [31:0] b, output reg [31:0] result);\n    always @(*) result = a + b;\nendmodule\n\nmodule adder_tb;\n    reg [31:0] a; reg [31:0] b; wire [31:0] result;\n    adder uut(.a(a), .b(b), .result(result));\n    initial begin a = 32'd10; b = 32'd20; #1; $display(\"%0d\", result); $finish; end\nendmodule\n""",
    },
    {
        "id": "hdl_comparator_verilog", "algorithm_id": "comparator", "title": "Comparator",
        "category": "Verilog / HDL", "description": "Verilog 2001 comparison circuit and testbench.", "language": "verilog",
        "code": """module comparator(input wire [31:0] a, input wire [31:0] b, output reg [31:0] result);\n    always @(*) begin if (a > b) result = 32'd1; else result = 32'd0; end\nendmodule\n\nmodule comparator_tb;\n    reg [31:0] a; reg [31:0] b; wire [31:0] result;\n    comparator uut(.a(a), .b(b), .result(result));\n    initial begin a = 32'd7; b = 32'd3; #1; $display(\"%0d\", result); $finish; end\nendmodule\n""",
    },
]

def get_example_list() -> List[Dict[str, Any]]:
    python_examples = [
        {
            "id": k,
            "algorithm_id": k,
            "title": v["title"],
            "category": v["category"],
            "description": v["description"],
            "language": v["language"],
            "code": v["code"]
        }
        for k, v in EXAMPLES.items()
    ]
    return python_examples + LANGUAGE_VARIANTS
