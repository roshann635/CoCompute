import pytest
import json
from master.app.engine.jobs import (
    generate_prime_job,
    generate_matrix_multiply_job,
    generate_word_count_job,
    generate_generic_python_job,
    generate_sorting_job,
    generate_image_processing_job,
    generate_compression_job,
    generate_job_chunks
)

def test_generate_prime_job():
    tasks = generate_prime_job(start_range=1, end_range=10, chunks=3)
    assert len(tasks) == 3
    # Check first chunk
    assert tasks[0]["chunk_index"] == 0
    assert tasks[0]["payload"]["type"] == "python"
    assert tasks[0]["payload"]["args"] == ["1", "4"]
    # Check last chunk
    assert tasks[2]["chunk_index"] == 2
    assert tasks[2]["payload"]["args"] == ["7", "10"]


def test_generate_matrix_multiply_job():
    tasks = generate_matrix_multiply_job(rows_a=6, cols_a=3, cols_b=4, chunks=3)
    assert len(tasks) == 3
    for i, t in enumerate(tasks):
        assert t["chunk_index"] == i
        args_data = json.loads(t["payload"]["args"][0])
        assert "rows_a" in args_data
        assert "matrix_b" in args_data
        assert args_data["start_row"] == i * 2
        assert len(args_data["rows_a"]) == 2
        assert len(args_data["matrix_b"]) == 3  # cols_a rows
        assert len(args_data["matrix_b"][0]) == 4  # cols_b columns


def test_generate_word_count_job():
    text = "hello world python testing map reduce split count"
    tasks = generate_word_count_job(text=text, chunks=4)
    # 8 words. chunks=4 => 2 words per chunk.
    assert len(tasks) == 4
    args_data = json.loads(tasks[0]["payload"]["args"][0])
    assert args_data["words"] == ["hello", "world"]


def test_generate_generic_python_job():
    script = "print('custom python script')"
    data_chunks = [{"id": 1, "val": "A"}, {"id": 2, "val": "B"}]
    tasks = generate_generic_python_job(script=script, data_chunks=data_chunks)
    assert len(tasks) == 2
    assert tasks[0]["chunk_index"] == 0
    assert tasks[0]["payload"]["script"] == script
    assert json.loads(tasks[0]["payload"]["args"][0]) == {"id": 1, "val": "A"}


def test_generate_sorting_job():
    tasks = generate_sorting_job(array_size=25, chunks=5)
    assert len(tasks) == 5
    for i, t in enumerate(tasks):
        assert t["chunk_index"] == i
        args_data = json.loads(t["payload"]["args"][0])
        assert "numbers" in args_data
        assert len(args_data["numbers"]) == 5


def test_generate_image_processing_job():
    tasks = generate_image_processing_job(images_count=6, filter_type="invert", chunks=3)
    assert len(tasks) == 3
    for i, t in enumerate(tasks):
        assert t["chunk_index"] == i
        args_data = json.loads(t["payload"]["args"][0])
        assert args_data["filter_type"] == "invert"
        assert len(args_data["images"]) == 2
        assert args_data["images"][0]["id"] == i * 2


def test_generate_compression_job():
    tasks = generate_compression_job(file_size_kb=1, chunks=2)
    assert len(tasks) == 2
    for i, t in enumerate(tasks):
        assert t["chunk_index"] == i
        args_data = json.loads(t["payload"]["args"][0])
        assert "text" in args_data
        assert len(args_data["text"]) > 0


def test_generate_job_chunks_routing():
    # Test routing to all types
    p_tasks = generate_job_chunks("prime_generation", {"start": 2, "end": 12, "chunks": 2})
    assert len(p_tasks) == 2

    m_tasks = generate_job_chunks("matrix_multiply", {"rows_a": 4, "cols_a": 2, "cols_b": 2, "chunks": 2})
    assert len(m_tasks) == 2

    w_tasks = generate_job_chunks("word_count", {"text": "hello test", "chunks": 1})
    assert len(w_tasks) == 1

    s_tasks = generate_job_chunks("sorting", {"array_size": 10, "chunks": 2})
    assert len(s_tasks) == 2

    i_tasks = generate_job_chunks("image_processing", {"images_count": 2, "filter_type": "grayscale", "chunks": 1})
    assert len(i_tasks) == 1

    c_tasks = generate_job_chunks("compression", {"file_size_kb": 1, "chunks": 1})
    assert len(c_tasks) == 1

    g_tasks = generate_job_chunks("generic_python", {"script": "pass", "data_chunks": [1, 2]})
    assert len(g_tasks) == 2

    # Test error
    with pytest.raises(ValueError) as excinfo:
        generate_job_chunks("invalid_job_type", {})
    assert "Unsupported job type" in str(excinfo.value)
