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
    }
}

def get_example_list() -> List[Dict[str, Any]]:
    return [
        {
            "id": k,
            "title": v["title"],
            "category": v["category"],
            "description": v["description"],
            "language": v["language"],
            "code": v["code"]
        }
        for k, v in EXAMPLES.items()
    ]
