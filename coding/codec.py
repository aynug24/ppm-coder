from typing import Iterable
from coding.context_tree import LeftContextTree
from coding.bit_number_range import BitNumberRange, DecoderWithRange
import itertools


class StatisticEncoder:
    def __init__(self, iter_chars, coding_params):
        self.iter_chars = iter_chars

        self.left_ctx_tree = LeftContextTree(coding_params)
        self.encoding_range = BitNumberRange()

    def encode(self) -> Iterable[int]:
        for char in self.iter_chars:
            for distribution, char_idx in self.left_ctx_tree.encode(char):
                yield from self.encoding_range.project_probability_pop_prefix(distribution, char_idx)
        yield from self.encoding_range.get_nonzero_prefix_from_range()


class StatisticDecoder:
    def __init__(self, iter_bits, length, coding_params):
        self.iter_bits = iter_bits
        self.length = length

        self.left_ctx_tree = LeftContextTree(coding_params)
        self.decoding_range = DecoderWithRange(self.iter_bits)

    def decode(self) -> Iterable[str]:
        yield from itertools.islice(
            self.left_ctx_tree.decode(
                lambda fenwick_distribution: self.decoding_range.get_next_char_idx(fenwick_distribution)),
            self.length
        )
