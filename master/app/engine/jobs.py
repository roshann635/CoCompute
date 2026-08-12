"""
Job Generator — creates task chunks for different job types.

Supported job types:
  1. prime_generation — find primes in a numeric range
  2. matrix_multiply — distributed matrix multiplication (row-based split)
  3. word_count — MapReduce-style word count on text
  4. generic_python — user-provided script with data chunks
"""
import math
import json
import logging

logger = logging.getLogger(__name__)


def generate_prime_job(start_range: int, end_range: int, chunks: int) -> list:
    """Split a prime number search range into chunks."""
    total_numbers = end_range - start_range
    chunk_size = math.ceil(total_numbers / chunks)
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


def generate_matrix_multiply_job(rows_a: int, cols_a: int, cols_b: int, chunks: int) -> list:
    """
    Distributed matrix multiplication: C = A × B.
    Generates random matrices and splits rows of A across chunks.
    Each chunk computes a subset of rows of C.
    """
    import random
    random.seed(42)

    # Generate matrices
    matrix_a = [[random.randint(1, 10) for _ in range(cols_a)] for _ in range(rows_a)]
    matrix_b = [[random.randint(1, 10) for _ in range(cols_b)] for _ in range(cols_a)]

    chunk_size = math.ceil(rows_a / chunks)
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


def generate_word_count_job(text: str, chunks: int) -> list:
    """
    MapReduce-style word count.
    Splits text into chunks and each worker counts words in their chunk.
    """
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


def generate_generic_python_job(script: str, data_chunks: list) -> list:
    """
    Generic job: user provides a Python script and a list of data chunks.
    Each chunk is passed as a JSON arg to the script.
    """
    tasks = []
    for i, chunk_data in enumerate(data_chunks):
        tasks.append({
            "chunk_index": i,
            "payload": {
                "type": "python",
                "script": script,
                "args": [json.dumps(chunk_data)] if isinstance(chunk_data, (dict, list)) else [str(chunk_data)]
            }
        })
    return tasks


def generate_sorting_job(array_size: int, chunks: int) -> list:
    """
    Distributed sorting.
    Generates a large list of random numbers, splits it into chunks,
    and each worker sorts its chunk.
    """
    import random
    random.seed(42)
    data_array = [random.randint(1, 1000000) for _ in range(array_size)]
    
    chunk_size = math.ceil(array_size / chunks) if array_size else 1
    tasks = []
    
    script = """
import sys, json

data = json.loads(sys.argv[1])
numbers = data["numbers"]
sorted_numbers = sorted(numbers)
print(json.dumps({"sorted_numbers": sorted_numbers}))
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


def generate_image_processing_job(images_count: int, filter_type: str, chunks: int) -> list:
    """
    Distributed Image Processing (Mock representation using pixel matrices).
    Each image is represented as a 10x10 matrix of [R, G, B] values.
    """
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
            else:
                new_row.append([r, g, b])
        new_pixels.append(new_row)
    processed.append({"id": img["id"], "pixels": new_pixels})
    
print(json.dumps({"processed_images": processed}))
""".strip()

    for i in range(chunks):
        start = i * chunk_size
        end = min(start + chunk_size, images_count)
        chunk_images = images[start:end]
        if not chunk_images:
            continue
            
        payload_data = json.dumps({
            "images": chunk_images,
            "filter_type": filter_type
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


def generate_compression_job(file_size_kb: int, chunks: int) -> list:
    """
    Distributed Compression.
    Splits text lines into chunks and compresses them using zlib.
    """
    text_block = "CoCompute distributed execution test data. " * (file_size_kb * 20)
    lines = [text_block[i:i+100] for i in range(0, len(text_block), 100)]
    
    chunk_size = math.ceil(len(lines) / chunks) if lines else 1
    tasks = []
    
    script = """
import sys, json, zlib, base64

data = json.loads(sys.argv[1])
text = data["text"]
compressed = base64.b64encode(zlib.compress(text.encode())).decode()
print(json.dumps({"compressed_data": compressed, "original_length": len(text)}))
""".strip()

    for i in range(chunks):
        start = i * chunk_size
        end = min(start + chunk_size, len(lines))
        chunk_text = "\n".join(lines[start:end])
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


def generate_job_chunks(job_type: str, params: dict) -> list:
    """Route to the correct job generator based on type."""
    if job_type == "prime_generation":
        return generate_prime_job(
            params.get("start", 1),
            params.get("end", 100000),
            params.get("chunks", 10)
        )
    elif job_type == "matrix_multiply":
        return generate_matrix_multiply_job(
            params.get("rows_a", 10),
            params.get("cols_a", 10),
            params.get("cols_b", 10),
            params.get("chunks", 5)
        )
    elif job_type == "word_count":
        return generate_word_count_job(
            params.get("text", "hello world"),
            params.get("chunks", 5)
        )
    elif job_type == "sorting":
        return generate_sorting_job(
            params.get("array_size", 1000),
            params.get("chunks", 5)
        )
    elif job_type == "image_processing":
        return generate_image_processing_job(
            params.get("images_count", 5),
            params.get("filter_type", "grayscale"),
            params.get("chunks", 2)
        )
    elif job_type == "compression":
        return generate_compression_job(
            params.get("file_size_kb", 100),
            params.get("chunks", 5)
        )
    elif job_type == "generic_python":
        return generate_generic_python_job(
            params.get("script", "print('hello')"),
            params.get("data_chunks", [{}])
        )
    else:
        raise ValueError(f"Unsupported job type: {job_type}")
