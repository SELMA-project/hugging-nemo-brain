from dataclasses import dataclass
from typing import Iterable, Optional, Union

import numpy as np
import pytest
from beartype import beartype

from ml4audio.audio_utils.overlap_array_chunker import (
    _DONT_EMIT_PREMATURE_CHUNKS,
    DONT_EMIT_PREMATURE_CHUNKS,
    OverlapArrayChunker,
    MessageChunk,
)


@beartype
def chunk_test_data(seq: Iterable, chunk_len: int):
    buffer = []
    for k in seq:
        if len(buffer) >= chunk_len:
            yield buffer[:chunk_len]
            buffer = buffer[chunk_len:]
        buffer.append(k)

    if len(buffer) > 0:
        yield buffer


TestSequence = list[list[int]]


@beartype
def build_test_chunks(input_data: Iterable[TestSequence]) -> list[MessageChunk]:
    def gen_seq(test_chunks):
        frame_idx = np.cumsum([0] + [len(tc) for tc in test_chunks[:-1]]).tolist()
        yield from [
            MessageChunk(
                message_id=f"test-message",
                frame_idx=k,
                array=np.array(chunk, dtype=np.int16),
                end_of_signal=k == frame_idx[-1],
            )
            for k, chunk in zip(frame_idx, test_chunks)
        ]

    input_chunks = [x for tc in input_data for x in gen_seq(tc)]
    print(f"{[len(ic.array) for ic in input_chunks]=}")
    return input_chunks


@dataclass
class TestCase:
    input_chunks: list[MessageChunk]
    chunk_size: int
    min_step_size: int
    expected: list[int]
    minimum_chunk_size: Union[int, _DONT_EMIT_PREMATURE_CHUNKS]
    max_step_size: Optional[int] = None


test_case_0 = TestCase(
    input_chunks=build_test_chunks(
        [
            list(chunk_test_data([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], 2)),
        ]
    ),
    chunk_size=4,
    min_step_size=2,
    expected=[0, 1, 2, 3, 2, 3, 4, 5, 4, 5, 6, 7, 6, 7, 8, 9],
    # + [8, 9],  # cropped,
    minimum_chunk_size=DONT_EMIT_PREMATURE_CHUNKS,
)

flushed_fullgrown = [7, 8, 9, 10]
shorten_stepsize_to_flush_fullgrown = TestCase(
    input_chunks=build_test_chunks(
        [
            list(chunk_test_data([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 2)),
        ]
    ),
    chunk_size=4,
    min_step_size=2,
    expected=[0, 1, 2, 3]
    + [2, 3, 4, 5]
    + [4, 5, 6, 7]
    + [6, 7, 8, 9]
    + flushed_fullgrown,
    minimum_chunk_size=DONT_EMIT_PREMATURE_CHUNKS,
    max_step_size=None,
)

big_input_chunk_len = TestCase(
    input_chunks=build_test_chunks(
        [
            list(chunk_test_data([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 6)),
        ]
    ),
    chunk_size=4,
    min_step_size=2,
    expected=[0, 1, 2, 3]
    + [2, 3, 4, 5]
    + [4, 5, 6, 7]
    + [6, 7, 8, 9]
    + flushed_fullgrown,
    minimum_chunk_size=DONT_EMIT_PREMATURE_CHUNKS,
    max_step_size=None,
)
premature_chunk = [0, 1]

test_case_premature = TestCase(
    input_chunks=build_test_chunks(
        [
            list(chunk_test_data([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], 2)),
        ]
    ),
    chunk_size=4,
    min_step_size=2,
    expected=premature_chunk + [0, 1, 2, 3, 2, 3, 4, 5, 4, 5, 6, 7, 6, 7, 8, 9],
    # + [8, 9],  # cropped,
    minimum_chunk_size=2,
)
premature_chunk_1 = [0, 1]
premature_chunk_2 = [0, 1, 2, 3]

test_case_premature_1 = TestCase(
    build_test_chunks(
        [
            list(chunk_test_data([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], 1)),
        ]
    ),
    chunk_size=6,
    min_step_size=2,
    expected=premature_chunk_1
    + premature_chunk_2
    + [0, 1, 2, 3, 4, 5]
    + [2, 3, 4, 5, 6, 7]
    + [4, 5, 6, 7, 8, 9],
    # + [ 6, 7, 8, 9], # do not yield this cropped
    minimum_chunk_size=2,
)
test_case_premature_2 = TestCase(
    build_test_chunks(
        [
            list(chunk_test_data([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], 2)),
        ]
    ),
    chunk_size=6,
    min_step_size=2,
    expected=premature_chunk_1
    + premature_chunk_2
    + [0, 1, 2, 3, 4, 5]
    + [2, 3, 4, 5, 6, 7]
    + [4, 5, 6, 7, 8, 9],
    # + [ 6, 7, 8, 9], # do not yield this cropped
    minimum_chunk_size=2,
)

premature_2_flush_no_cropped = TestCase(
    build_test_chunks(
        [
            list(chunk_test_data([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 1)),
        ]
    ),
    chunk_size=6,
    min_step_size=2,
    expected=premature_chunk_1
    + premature_chunk_2
    + [0, 1, 2, 3, 4, 5]
    + [2, 3, 4, 5, 6, 7]
    + [4, 5, 6, 7, 8, 9]
    + [
        5,
        6,
        7,
        8,
        9,
        10,
    ],  # flushed ending, here stepped by one! even though step-size is not variable!
    minimum_chunk_size=2,
)

test_case_premature_3_no_cropped = TestCase(
    build_test_chunks(
        [
            list(chunk_test_data([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], 1)),
        ]
    ),
    chunk_size=6,
    min_step_size=2,
    expected=premature_chunk_1
    + premature_chunk_2
    + [0, 1, 2, 3, 4, 5]
    + [2, 3, 4, 5, 6, 7]
    + [4, 5, 6, 7, 8, 9],
    # + [6, 7, 8, 9],  # no cropped!
    minimum_chunk_size=2,
)

test_case_premature_3_varlen = TestCase(
    build_test_chunks(
        [
            [[0], [1], [2, 3], [4, 5], [6, 7, 8, 9], [10, 11]],
        ]
    ),
    chunk_size=6,
    min_step_size=1,
    expected=[0]
    + premature_chunk_1
    + premature_chunk_2
    + [0, 1, 2, 3, 4, 5]
    + [3, 4, 5, 6, 7, 8]  # stepped 3
    + [4, 5, 6, 7, 8, 9]  # stepped 1
    + [6, 7, 8, 9, 10, 11],  # stepped 2
    minimum_chunk_size=1,
    max_step_size=3,
)


@pytest.mark.parametrize(
    "test_case",
    [
        test_case_0,
        shorten_stepsize_to_flush_fullgrown,
        big_input_chunk_len,
        test_case_premature,
        test_case_premature_1,
        test_case_premature_2,
        premature_2_flush_no_cropped,
        test_case_premature_3_no_cropped,
        test_case_premature_3_varlen,
    ],
)
def test_OverlapArrayChunker(test_case: TestCase):

    ab = OverlapArrayChunker(
        test_case.chunk_size,
        min_step_size=test_case.min_step_size,
        minimum_chunk_size=test_case.minimum_chunk_size,
        max_step_size=test_case.max_step_size,
    )
    ab.reset()
    messages = [x for m in test_case.input_chunks for x in ab.handle_datum(m)]
    arrays = [m.array for m in messages]
    pred = [str(i) for i in np.concatenate(arrays).tolist()]
    expected = [str(i) for i in test_case.expected]
    assert pred == expected
