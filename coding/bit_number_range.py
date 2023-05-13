import math
import itertools
from fenwick import FenwickTree
from typing import List

N = 64
MAX = 2 ** N

HIDE_BITS_IF_LOW_GTE = 2 ** (N - 2)
HIDE_BITS_IF_HIGH_LT = 2 ** (N - 1) + 2 ** (N - 2)


def project_to_range(point, old_range_max, new_range_max):
    return min(math.ceil(point / old_range_max * new_range_max), new_range_max - 1)


def project_distribution_to_subrange(
        fenwick_distribution: FenwickTree,
        char_idx,
        subrange_l,
        subrange_r):
    distribution_total = fenwick_distribution.prefix_sum(len(fenwick_distribution))
    distribution_low = fenwick_distribution.prefix_sum(char_idx)
    distribution_high = distribution_low + fenwick_distribution[char_idx]

    if distribution_low == distribution_high:
        raise Exception('uhm')

    subrange_new_l = subrange_l + project_to_range(distribution_low, distribution_total, subrange_r - subrange_l + 1)
    subrange_new_r = subrange_l + project_to_range(distribution_high, distribution_total,
                                                   subrange_r - subrange_l + 1) - 1

    return subrange_new_l, subrange_new_r


def project_subrange_to_distribution(subrange_point, subrange_l, subrange_r, fenwick_distribution: FenwickTree):
    total = fenwick_distribution.prefix_sum(len(fenwick_distribution))

    left = 0
    right = len(fenwick_distribution) - 1
    result = -1

    while left <= right:
        mid = (left + right) // 2

        if project_to_range(fenwick_distribution.prefix_sum(mid), total,
                            subrange_r - subrange_l + 1) <= subrange_point - subrange_l:
            result = mid
            left = mid + 1
        else:
            right = mid - 1

    return result


def extend_iterator(iterator, tail):
    while True:
        try:
            yield next(iterator)
        except StopIteration:
            yield tail


class DecoderWithRange:
    def __init__(self, iter_bits):
        self.iter_bits = extend_iterator(iter_bits, 0)
        self.number_range = BitNumberRange()
        self.window = int(''.join(map(str, itertools.islice(self.iter_bits, N))), 2)

    def get_next_char_idx(self, fenwick_distribution):
        if self.window < 0:
            raise Exception()
        # print(f'Finding {self.window} of {self.number_range.__repr__()} in {fenwick_distribution.__repr__()}')
        next_char_idx = project_subrange_to_distribution(
            self.window, self.number_range.low, self.number_range.high,
            fenwick_distribution)

        old_hidden_bits = self.number_range.hidden_bits
        common_range_prefix = self.number_range.project_probability_pop_prefix(fenwick_distribution, next_char_idx)
        self._move_window(old_hidden_bits, common_range_prefix)

        # print(f'Found {next_char_idx}, window is {self.window}')
        return next_char_idx

    def _move_window(self, old_hidden_bits, common_prefix):
        if len(common_prefix) == 0:
            for _ in range(self.number_range.hidden_bits - old_hidden_bits):
                self.window = 2 * self.window - 2 ** (N - 1) + next(self.iter_bits)
            return

        for _ in range(len(common_prefix) - old_hidden_bits):
            self.window = (2 * self.window + next(self.iter_bits)) % MAX

        for _ in range(self.number_range.hidden_bits):
            self.window = 2 * self.window - 2 ** (N - 1) + next(self.iter_bits)


# Not worrying about overflow; instead worrying about performance :)
class BitNumberRange:
    def __init__(self):
        self.low = 0
        self.high = MAX - 1

        self.hidden_bits = 0

    def project_probability_pop_prefix(self, fenwick_distribution, char_idx) -> List[int]:
        # print(f'Before encoding {char_idx} in {fenwick_distribution.__repr__()}:')
        self._project_probability(fenwick_distribution, char_idx)
        if not 0 <= self.low < self.high < MAX:
            raise Exception()

        common_prefix = self._pop_common_prefix()
        self._hide_bits()
        if not 0 <= self.low < self.high < MAX:
            raise Exception()

        return common_prefix

    def get_nonzero_prefix_from_range(self):
        self.hidden_bits = 0
        return [1]  # 10000000...000000 = 2 ** (N - 1) is always in range

    # returns bits: [1, 0, 1, 1, 0, 1, ...]
    def _pop_common_prefix(self) -> List[int]:
        common_prefix = []

        first_common_digit = True
        while self.low >> (N - 1) == self.high >> (N - 1):
            common_prefix.append(self.low >> (N - 1))
            self.low = 2 * self.low % MAX
            self.high = (2 * self.high + 1) % MAX

            if first_common_digit:
                common_prefix.extend([1 - common_prefix[0]] * self.hidden_bits)
                self.hidden_bits = 0
                first_common_digit = False

        return common_prefix

    def _project_probability(self, fenwick_distribution: FenwickTree, char_idx):
        (self.low, self.high) = project_distribution_to_subrange(
            fenwick_distribution, char_idx, self.low, self.high)

    def _hide_bits(self):
        while self.low >= HIDE_BITS_IF_LOW_GTE and self.high < HIDE_BITS_IF_HIGH_LT:
            self.low = 2 * self.low - 2 ** (N - 1)
            self.high = 2 * self.high - 2 ** (N - 1) + 1
            self.hidden_bits += 1

    def __repr__(self):
        low_bits = f'{self.low:0{N}b}'
        high_bits = f'{self.high:0{N}b}'

        def fmt(bits, hidden):
            hidden = f'_{"".join(map(str, [1 - int(bits[0])] * self.hidden_bits))}_'
            return bits if hidden == '__' else f'{bits[0]}{hidden}{bits[1:]}'

        return f'{fmt(low_bits, self.hidden_bits)}...{fmt(high_bits, self.hidden_bits)}'
