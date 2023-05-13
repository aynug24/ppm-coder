import itertools
import math
from fenwick import FenwickTree


class ExtendableFenwickTree:
    def __init__(self, init_length):
        self.length = max(init_length, 1)
        self.capacity = self.length
        self.inner = FenwickTree(self.capacity)

    @staticmethod
    def from_inner(fenwick_tree):
        res = ExtendableFenwickTree(len(fenwick_tree))
        res.inner = fenwick_tree
        return res


    def append(self, freq):
        if self.length == self.capacity:
            freqs = self.inner.frequencies()
            self.capacity = math.ceil(self.capacity * 3 / 2)
            self.inner = FenwickTree(self.capacity)
            self.inner.init(freqs + [0] * (self.capacity - len(freqs)))

        self.inner.add(self.length, freq)
        self.length += 1

    def prefix_sum(self, stop):
        return self.inner.prefix_sum(stop) if stop > 0 else 0

    def add(self, idx, k):
        self.inner.add(idx, k)

    # if given chars_to_indices, return new_incides_to_chars
    def without_chars(self, chars_to_exclude, chars_to_indices, find_char_idx=None):
        indices = {chars_to_indices[c]: c for c in chars_to_exclude if c in chars_to_indices}

        res_freqs = []
        new_indices_to_old_indices = {}
        find_char_new_idx = None
        find_char_old_idx = chars_to_indices[find_char_idx] \
            if find_char_idx is not None and find_char_idx in chars_to_indices \
            else None
        for i, freq in enumerate(self.inner.frequencies()):
            if i not in indices:
                res_freqs.append(freq)
                new_idx = len(new_indices_to_old_indices)
                new_indices_to_old_indices[new_idx] = i
                if find_char_old_idx is not None and i == find_char_old_idx:
                    find_char_new_idx = new_idx

        res = FenwickTree(len(res_freqs))
        res.init(res_freqs)
        return ExtendableFenwickTree.from_inner(res), new_indices_to_old_indices, find_char_new_idx

    def __getitem__(self, idx):
        if idx >= self.length:
            raise IndexError(f'Index {idx}, length {self.length}')
        return self.inner[idx]

    def __len__(self):
        return self.length

    def __repr__(self):
        return f'{self.inner.frequencies()[:self.length]} => {[self.inner.prefix_sum(i) for i in range(1, self.length + 1)]}'
