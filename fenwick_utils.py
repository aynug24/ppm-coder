import itertools
import math
from fenwick import FenwickTree


class ExtendableFenwickTree:
    def __init__(self, init_length):
        self.length = max(init_length, 1)
        self.capacity = self.length
        self.inner = FenwickTree(self.capacity)

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

    def __getitem__(self, idx):
        if idx >= self.length:
            raise IndexError(f'Index {idx}, length {self.length}')
        return self.inner[idx]

    def __len__(self):
        return self.length

    def __repr__(self):
        return f'{self.inner.frequencies()} => {[self.inner.prefix_sum(i) for i in range(1, len(self.inner) + 1)]}'
