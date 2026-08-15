"""
Job Generator — creates task chunks for all standard CoCompute job types.
"""

import math
import json
import logging
from typing import List, Dict, Any

from shared.sdk.registry import TaskRegistry

logger = logging.getLogger(__name__)


def generate_prime_job(start_range: int = 1, end_range: int = 100000, chunks: int = 10) -> list:
    total_numbers = end_range - start_range
    chunk_size = math.ceil(total_numbers / chunks) if total_numbers else 1
    tasks = []
    current_start = start_range

    script = """
import sys, json

def is_prime(n):
    if n <= 1: return False
    if n <= 3: return True
    if n % 2 == 0 or n % 3 == 0: return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0: return False
        i += 6
    return True

start = int(sys.argv[1])
end = int(sys.argv[2])
primes = [n for n in range(start, end) if is_prime(n)]
print(json.dumps({"primes_found": len(primes), "primes": primes[:100]}))
""".strip()

    for i in range(chunks):
        current_end = min(current_start + chunk_size, end_range)
        tasks.append({
            "chunk_index": i,
            "payload": {
                "type": "python",
                "script": script,
                "args": [str(current_start), str(current_end)]
            }
        })
        current_start = current_end
    return tasks


def generate_matrix_multiply_job(rows_a: int = 50, cols_a: int = 50, cols_b: int = 50, chunks: int = 5) -> list:
    import random
    random.seed(42)
    matrix_a = [[random.randint(1, 10) for _ in range(cols_a)] for _ in range(rows_a)]
    matrix_b = [[random.randint(1, 10) for _ in range(cols_b)] for _ in range(cols_a)]

    chunk_size = math.ceil(rows_a / chunks) if rows_a else 1
    tasks = []

    script = """
import sys, json
data = json.loads(sys.argv[1])
rows_a = data["rows_a"]
matrix_b = data["matrix_b"]
start_row = data["start_row"]

result_rows = []
for row in rows_a:
    result_row = []
    for j in range(len(matrix_b[0])):
        val = sum(row[k] * matrix_b[k][j] for k in range(len(row)))
        result_row.append(val)
    result_rows.append(result_row)

print(json.dumps({"start_row": start_row, "result_rows": result_rows}))
""".strip()

    for i in range(chunks):
        start_row = i * chunk_size
        end_row = min(start_row + chunk_size, rows_a)
        chunk_rows = matrix_a[start_row:end_row]
        if not chunk_rows:
            continue
        payload_data = json.dumps({
            "rows_a": chunk_rows,
            "matrix_b": matrix_b,
            "start_row": start_row
        })
        tasks.append({
            "chunk_index": i,
            "payload": {
                "type": "python",
                "script": script,
                "args": [payload_data]
            }
        })
    return tasks


def generate_word_count_job(text: str = "hello world", chunks: int = 5) -> list:
    words = text.split()
    chunk_size = math.ceil(len(words) / chunks) if words else 1
    tasks = []

    script = """
import sys, json
from collections import Counter
data = json.loads(sys.argv[1])
words = data["words"]
counts = dict(Counter(words))
print(json.dumps({"word_counts": counts, "total_words": len(words)}))
""".strip()

    for i in range(chunks):
        start = i * chunk_size
        end = min(start + chunk_size, len(words))
        chunk_words = words[start:end]
        if not chunk_words:
            continue
        payload_data = json.dumps({"words": chunk_words})
        tasks.append({
            "chunk_index": i,
            "payload": {
                "type": "python",
                "script": script,
                "args": [payload_data]
            }
        })
    return tasks


def generate_generic_python_job(script: str = "print('hello')", data_chunks: list = None) -> list:
    if data_chunks is None:
        data_chunks = [{}]
    tasks = []
    for i, chunk_data in enumerate(data_chunks):
        tasks.append({
            "chunk_index": i,
            "payload": {
                "type": "python",
                "script": script,
                "args": [json.dumps(chunk_data)]
            }
        })
    return tasks


def generate_sorting_job(array_size: int = 1000, chunks: int = 5) -> list:
    import random
    random.seed(42)
    data_array = [random.randint(1, 1000000) for _ in range(array_size)]
    chunk_size = math.ceil(array_size / chunks) if array_size else 1
    tasks = []

    script = """
import sys, json
data = json.loads(sys.argv[1])
numbers = data["numbers"]
numbers.sort()
print(json.dumps({"sorted_numbers": numbers}))
""".strip()

    for i in range(chunks):
        start = i * chunk_size
        end = min(start + chunk_size, array_size)
        chunk_data = data_array[start:end]
        if not chunk_data:
            continue
        payload_data = json.dumps({"numbers": chunk_data})
        tasks.append({
            "chunk_index": i,
            "payload": {
                "type": "python",
                "script": script,
                "args": [payload_data]
            }
        })
    return tasks


def generate_image_processing_job(images_count: int = 5, filter_type: str = "grayscale", chunks: int = 2) -> list:
    import random
    random.seed(42)
    images = []
    for img_idx in range(images_count):
        pixels = [[[random.randint(0, 255) for _ in range(3)] for _ in range(10)] for _ in range(10)]
        images.append({"id": img_idx, "pixels": pixels})

    chunk_size = math.ceil(images_count / chunks) if images_count else 1
    tasks = []

    script = """
import sys, json
data = json.loads(sys.argv[1])
images = data["images"]
filter_type = data["filter_type"]

processed = []
for img in images:
    pixels = img["pixels"]
    new_pixels = []
    for row in pixels:
        new_row = []
        for pixel in row:
            r, g, b = pixel[0], pixel[1], pixel[2]
            if filter_type == "grayscale":
                gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                new_row.append([gray, gray, gray])
            elif filter_type == "invert":
                new_row.append([255 - r, 255 - g, 255 - b])
            elif filter_type == "edge":
                edge_val = int(abs(r - g) + abs(g - b)) % 256
                new_row.append([edge_val, edge_val, edge_val])
            else:
                avg = int((r + g + b) / 3)
                new_row.append([avg, avg, avg])
        new_pixels.append(new_row)
    processed.append({"id": img["id"], "pixels": new_pixels})

print(json.dumps({"processed_images": processed, "filter_applied": filter_type}))
""".strip()

    for i in range(chunks):
        start = i * chunk_size
        end = min(start + chunk_size, images_count)
        chunk_images = images[start:end]
        if not chunk_images:
            continue
        payload_data = json.dumps({"images": chunk_images, "filter_type": filter_type})
        tasks.append({
            "chunk_index": i,
            "payload": {
                "type": "python",
                "script": script,
                "args": [payload_data]
            }
        })
    return tasks


def generate_compression_job(file_size_kb: int = 100, chunks: int = 5) -> list:
    raw_text = ("CoCompute distributed computing system payload data " * 50)[: file_size_kb * 1024]
    chunk_size = math.ceil(len(raw_text) / chunks) if raw_text else 1
    tasks = []

    script = """
import sys, json, zlib, base64
data = json.loads(sys.argv[1])
text = data["text"]
compressed = zlib.compress(text.encode("utf-8"))
print(json.dumps({
    "original_length": len(text),
    "compressed_length": len(compressed),
    "compressed_base64": base64.b64encode(compressed).decode("ascii")
}))
""".strip()

    for i in range(chunks):
        start = i * chunk_size
        end = min(start + chunk_size, len(raw_text))
        chunk_text = raw_text[start:end]
        if not chunk_text:
            continue
        payload_data = json.dumps({"text": chunk_text})
        tasks.append({
            "chunk_index": i,
            "payload": {
                "type": "python",
                "script": script,
                "args": [payload_data]
            }
        })
    return tasks


def generate_statistics_job(array_size: int = 1000, chunks: int = 5) -> list:
    import random
    random.seed(42)
    data_array = [round(random.gauss(50, 15), 2) for _ in range(array_size)]
    chunk_size = math.ceil(array_size / chunks) if array_size else 1
    tasks = []

    script = """
import sys, json
data = json.loads(sys.argv[1])
numbers = data["numbers"]
numbers.sort()
print(json.dumps({
    "values": numbers,
    "sum": sum(numbers),
    "count": len(numbers),
    "min": min(numbers) if numbers else None,
    "max": max(numbers) if numbers else None,
}))
""".strip()

    for i in range(chunks):
        start = i * chunk_size
        end = min(start + chunk_size, array_size)
        chunk_data = data_array[start:end]
        if not chunk_data:
            continue
        payload_data = json.dumps({"numbers": chunk_data})
        tasks.append({
            "chunk_index": i,
            "payload": {
                "type": "python",
                "script": script,
                "args": [payload_data]
            }
        })
    return tasks


def generate_search_job(array_size: int = 100000, target: int = 42, chunks: int = 10) -> list:
    import random
    random.seed(42)
    data_array = [random.randint(1, 1000000) for _ in range(array_size)]
    if target not in data_array and array_size > 0:
        insert_pos = random.randint(0, array_size - 1)
        data_array[insert_pos] = target

    chunk_size = math.ceil(array_size / chunks) if array_size else 1
    tasks = []

    script = """
import sys, json
data = json.loads(sys.argv[1])
numbers = data["numbers"]
target = data["target"]
offset = data["offset"]

found = False
global_index = None
for i, num in enumerate(numbers):
    if num == target:
        found = True
        global_index = offset + i
        break

print(json.dumps({
    "target": target,
    "found": found,
    "global_index": global_index,
    "chunk_size": len(numbers)
}))
""".strip()

    for i in range(chunks):
        start = i * chunk_size
        end = min(start + chunk_size, array_size)
        chunk_data = data_array[start:end]
        if not chunk_data:
            continue
        payload_data = json.dumps({
            "numbers": chunk_data,
            "target": target,
            "offset": start
        })
        tasks.append({
            "chunk_index": i,
            "payload": {
                "type": "python",
                "script": script,
                "args": [payload_data]
            }
        })
    return tasks


def generate_job_chunks(job_type: str, params: dict) -> List[dict]:
    """Route to generator based on job_type."""
    if job_type == "prime_generation":
        return generate_prime_job(params.get("start", 1), params.get("end", 100000), params.get("chunks", 10))
    elif job_type == "matrix_multiply":
        return generate_matrix_multiply_job(params.get("rows_a", 10), params.get("cols_a", 10), params.get("cols_b", 10), params.get("chunks", 5))
    elif job_type == "word_count":
        return generate_word_count_job(params.get("text", "hello world"), params.get("chunks", 5))
    elif job_type == "sorting":
        return generate_sorting_job(params.get("array_size", 1000), params.get("chunks", 5))
    elif job_type == "image_processing":
        return generate_image_processing_job(params.get("images_count", 5), params.get("filter_type", "grayscale"), params.get("chunks", 2))
    elif job_type == "compression":
        return generate_compression_job(params.get("file_size_kb", 100), params.get("chunks", 5))
    elif job_type == "statistics":
        return generate_statistics_job(params.get("array_size", 1000), params.get("chunks", 5))
    elif job_type == "search":
        return generate_search_job(params.get("array_size", 100000), params.get("target", 42), params.get("chunks", 10))
    elif job_type == "generic_python":
        return generate_generic_python_job(params.get("script", "print('hello')"), params.get("data_chunks", [{}]))
    
    # Check TaskRegistry for SDK tasks (cipher, ml_training, distributed_inference, llm_finetune)
    task = TaskRegistry.get(job_type)
    if task:
        chunks_count = int(params.get("chunks", 4))
        return task.partition(params, chunks_count)

    raise ValueError(f"Unsupported job type: {job_type}")
