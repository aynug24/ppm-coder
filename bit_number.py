import math
import itertools
from fenwick import FenwickTree
from typing import List

N = 64
MAX = 2 ** N

HIDE_BITS_IF_LOW_GTE = 2 ** (N - 2)
HIDE_BITS_IF_HIGH_LT = 2 ** (N - 1) + 2 ** (N - 2)


def project_to_range(point, old_range_max, new_range_max):
    return math.ceil(point / old_range_max * new_range_max)


def project_distribution_to_subrange(
        fenwick_distribution: FenwickTree,
        char_idx,
        coding_range_max,
        subrange_l,
        subrange_r):
    # todo одной проекцией

    distribution_total = fenwick_distribution.prefix_sum(len(fenwick_distribution))
    distribution_low = fenwick_distribution.prefix_sum(char_idx)
    distribution_high = distribution_low + fenwick_distribution[char_idx]

    coding_range_l = project_to_range(distribution_low, distribution_total, MAX)
    coding_range_r = project_to_range(distribution_high, distribution_total, MAX)

    subrange_new_l = coding_range_l + project_to_range(coding_range_l, MAX, subrange_r - subrange_l + 1)
    subrange_new_r = coding_range_l + project_to_range(coding_range_r, MAX, subrange_r - subrange_l + 1)

    return subrange_new_l, subrange_new_r


def project_subrange_to_distribution(subrange_point, subrange_l, subrange_r, fenwick_distribution: FenwickTree):
    coding_range_point = project_to_range(subrange_point, subrange_r - subrange_l + 1, MAX)
    distribution_point = project_to_range(coding_range_point, MAX, fenwick_distribution.prefix_sum(len(fenwick_distribution)))

    l = 0
    r = len(fenwick_distribution) - 1

    while l <= r:
        mid = (l + r) // 2
        if fenwick_distribution.prefix_sum(mid) > distribution_point:
            r = mid - 1
        else:
            l = mid + 1

    return l


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

    def binsearch_byte_from_distr(self, window_number, fenwick_distribution):
        l = 0
        r = len(fenwick_distribution) - 1

        while l <= r:
            mid = (l + r) // 2
            if fenwick_distribution.prefix_sum(mid) > window_number:
                r = mid - 1
            else:
                l = mid + 1

        return l

    # next_byte_distribution: [124, 864, 1045, ..., 2^N]
    def get_next_char_idx(self, fenwick_distribution):
        next_byte = project_subrange_to_distribution(
            self.window, self.number_range.low, self.number_range.high, fenwick_distribution)  # self.binsearch_byte_from_distr(self.window, fenwick_distribution)
        common_range_prefix = self.number_range.project_probability_pop_prefix(
            fenwick_distribution.prefix_sum(next_byte),
            fenwick_distribution.prefix_sum(next_byte + 1)
        )

        for _ in range(len(common_range_prefix)):
            self.window = (2 * self.window + next(self.iter_bits)) % MAX

        for _ in range(self.number_range.hidden_bits):
            self.window = 2 * self.window - 2 ** (N - 1) + next(self.iter_bits)

        return next_byte


# Not worrying about overflow; instead worrying about performance :)
class BitNumberRange:
    def __init__(self):
        self.low = 0
        self.high = MAX - 1

        self.hidden_bits = 0

    def project_probability_pop_prefix(self, fenwick_distribution, char_idx) -> List[int]:
        self._project_probability(fenwick_distribution, char_idx)
        common_prefix = self._pop_common_prefix()
        self._hide_bits()
        return common_prefix

    def get_nonzero_prefix_from_range(self):
        self.hidden_bits = 0
        return [1]  # 10000000...000000 = 2 ** (N - 1) is always in range

    # returns [1, 0, 1, 1, 0, 1, ...]
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

    # end exclusive, range_start = a, range_end = b + 1
    def _project_probability(self, fenwick_distribution: FenwickTree, char_idx):
        # distribution_low = fenwick_distribution.prefix_sum(char_idx)
        #
        # current_length = self.high - self.low
        # self.low = self.low + math.ceil(range_start / BitNumberRange.MAX * current_length)
        # self.high = self.high + math.ceil(range_end / BitNumberRange.MAX * current_length) - 1
        (self.low, self.high) = project_distribution_to_subrange(
            fenwick_distribution, char_idx, MAX, self.low, self.high)

    def _hide_bits(self):
        while self.low >= HIDE_BITS_IF_LOW_GTE and self.high < HIDE_BITS_IF_HIGH_LT:
            self.low = 2 * self.low - 2 ** (N - 1)
            self.high = 2 * self.high - 2 ** (N - 2) + 1
            self.hidden_bits += 1

    def __repr__(self):
        low_bits = f'{self.low:064b}'
        high_bits = f'{self.high:064b}'

        def fmt(bits, hidden):
            hidden = f'_{"".join(map(str, [1 - int(bits[0])] * self.hidden_bits))}_'
            return bits if hidden == '__' else f'{bits[0]}{hidden}{bits[1:]}'

        return f'{fmt(low_bits, self.hidden_bits)}...{fmt(high_bits, self.hidden_bits)}'
