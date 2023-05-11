from typing import Dict, Optional, List, Iterable, Tuple, Callable
from fenwick import FenwickTree
from fenwick_utils import ExtendableFenwickTree

class LeftContextTree:
    SIGMA = 256

    def __init__(self, ctx_len=3, mask_seen_chars=False, exclude_short_ctx_from_update=False):
        self.ctx_len = ctx_len
        self.mask_seen_chars = mask_seen_chars
        self.exclude_short_ctx_from_update = exclude_short_ctx_from_update

        self.root = LeftContext(None)

        self.pseudo_root = LeftContext(None)
        self.pseudo_root.chars_to_indices = {chr(c): c for c in range(LeftContextTree.SIGMA)}
        self.pseudo_root.indices_to_chars = {c: chr(c) for c in range(LeftContextTree.SIGMA)}
        self.pseudo_root.distribution = ExtendableFenwickTree(LeftContextTree.SIGMA)
        for c in range(LeftContextTree.SIGMA):
            self.pseudo_root.distribution.add(c, 1)
        self.pseudo_root.children = {c: self.root for c in range(LeftContextTree.SIGMA)}

        self.root.parent = self.pseudo_root

        self.left_ctx = ''

        # self.current = self.root

    def encode(self, c) -> Iterable[Tuple[FenwickTree, int]]:
        char_ctx = self._go_down(self.left_ctx)

        if not self.mask_seen_chars:
            encode_ctx = char_ctx
            while True:
                char_idx = encode_ctx.chars_to_indices.get(c)
                if char_idx is not None:
                    yield encode_ctx.distribution, char_idx
                    break
                yield encode_ctx.distribution, encode_ctx.chars_to_indices[LeftContext.UP]
                encode_ctx = encode_ctx.parent
        else:
            raise NotImplementedError

        if not self.exclude_short_ctx_from_update:
            while char_ctx != self.pseudo_root:
                char_ctx.add(c)
                char_ctx = char_ctx.parent
        else:
            raise NotImplementedError

        self.left_ctx = self.left_ctx[-self.ctx_len + 1:] + c

    def decode(self, get_next_char: Callable[[FenwickTree], int]) -> Iterable[str]:
        decoded = []
        while True:
            current = self._go_down(self.left_ctx)

            if not self.mask_seen_chars:
                encode_ctx = current
                while True:
                    char_idx = get_next_char(encode_ctx.distribution)
                    char = encode_ctx.indices_to_chars[char_idx]
                    if char == LeftContext.UP:
                        encode_ctx = encode_ctx.parent
                    else:
                        decoded.append(char)
                        yield char
                        break
            else:
                raise NotImplementedError

            if not self.exclude_short_ctx_from_update:
                while current != self.pseudo_root:
                    current.add(char)
                    current = current.parent
            else:
                raise NotImplementedError

            self.left_ctx = self.left_ctx[-self.ctx_len+1:] + char

    def _go_down(self, left_ctx):
        current = self.root
        for c in reversed(left_ctx[-self.ctx_len:]):
            child = current.children.get(c)
            if child is None:
                return current
        return current


class LeftContext:
    UP = '↑'

    def __init__(self, parent: Optional['LeftContext']):
        self.parent = parent
        self.children: Optional[Dict[str, 'LeftContext']] = None

        self.distribution = ExtendableFenwickTree(1)
        # todo init UP
        self.distribution.add(0, 1)
        self.chars_to_indices = {LeftContext.UP: 0}
        self.indices_to_chars = {0: LeftContext.UP}

    def add(self, c):
        char_idx = self.chars_to_indices.get(c)
        if char_idx is None:
            # todo new char
            self.chars_to_indices[c] = len(self.chars_to_indices)
            self.indices_to_chars[len(self.indices_to_chars)] = c
            self.distribution.append(1)
        else:
            # todo not new char
            self.distribution.add(char_idx, 1)

