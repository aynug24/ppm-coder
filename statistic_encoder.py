from typing import Dict, Optional, List, Iterable, Tuple, Callable
from fenwick import FenwickTree
from fenwick_utils import ExtendableFenwickTree
from enum import Enum
from dataclasses import dataclass


class UpCharCodingAlrorithm(Enum):
    A_ALWAYS_ONE = 1
    B_OTHER_CHAR_COUNT = 2
    C_PLUS_ONE_ON_NEW_CHAR = 3
    D_PLUS_HALF_ON_NEW_CHAR = 4

    @staticmethod
    def from_letter(c):
        return [x for x in list(UpCharCodingAlrorithm) if x.name.startswith(c)][0]


@dataclass
class CodingParams:
    context_length: int = 6
    mask_seen: bool = False
    exclude_on_update: bool = False
    up_char_coding: UpCharCodingAlrorithm = UpCharCodingAlrorithm.A_ALWAYS_ONE
    decapitalize: bool = True

def fmt_dist(distribution, point, ctx: 'LeftContext'):
    total = distribution.prefix_sum(len(distribution))
    point_len = distribution[point]
    return f'{point_len:3}/{total:4} ≈ {(point_len/total):.3f}, keys: {list(sorted(((ctx.seen_once_chars if ctx.seen_once_chars is not None else set()) | ctx.chars_to_indices.keys()) - {LeftContext.UP}))}'

class LeftContextTree:
    SIGMA = 256

    def __init__(self, coding_params):
        self.coding_params = coding_params

        self.root = None  # !!! kinda important...

        self.pseudo_root = LeftContext(None, '↓')
        self.pseudo_root.chars_to_indices = {chr(c): c for c in range(LeftContextTree.SIGMA) if not (coding_params.decapitalize and chr(c).isupper())}
        self.pseudo_root.indices_to_chars = {c: chr(c) for c in range(LeftContextTree.SIGMA) if not (coding_params.decapitalize and chr(c).isupper())}
        self.pseudo_root.distribution = ExtendableFenwickTree(LeftContextTree.SIGMA)
        for c in range(LeftContextTree.SIGMA):
            self.pseudo_root.distribution.add(c, 1)

        self.left_ctx = ''

        # self.current = self.root

    def encode(self, c) -> Iterable[Tuple[FenwickTree, int]]:
        # print(f'ENCODING {c} IN \'{self.left_ctx}\'')
        char_ctx = self._go_down(self.left_ctx)

        if not self.coding_params.mask_seen:
            encode_ctx = char_ctx
            while True:
                char_idx = encode_ctx.chars_to_indices.get(c)
                if char_idx is not None:
                    # print(f'''Encoding \'{c}\' in {("'" + encode_ctx.s + "'"):8} as {char_idx:2} in {fmt_dist(encode_ctx.distribution, char_idx, encode_ctx)}: {encode_ctx.distribution.__repr__()}''')
                    yield encode_ctx.distribution, char_idx
                    break
                # print(f'''Encoding \'↑\' in {("'" + encode_ctx.s + "'"):8} as {0:2} in {fmt_dist(encode_ctx.distribution, 0, encode_ctx)}: {encode_ctx.distribution.__repr__()}''')
                yield encode_ctx.distribution, encode_ctx.chars_to_indices[LeftContext.UP]
                encode_ctx = encode_ctx.parent
        else:
            encode_ctx = char_ctx
            seen_chars = set()
            while True:
                masked_distribution, _, char_masked_idx = encode_ctx.distribution.without_chars(
                    seen_chars, encode_ctx.chars_to_indices, find_char_idx=c)
                if char_masked_idx is not None:
                    # print(f'''Encoding \'{c}\' in {("'" + encode_ctx.s + "'"):8} as {char_masked_idx:2} in {fmt_dist(masked_distribution, char_masked_idx, encode_ctx)}: {masked_distribution.__repr__()}''')
                    yield masked_distribution, char_masked_idx
                    break
                # print(f'''Encoding \'↑\' in {("'" + encode_ctx.s + "'"):8} as {0:2} in {fmt_dist(masked_distribution, 0, encode_ctx)}: {masked_distribution.__repr__()}''')
                yield masked_distribution, 0  # i give up using LeftCtx.UP, lets just write zero here
                seen_chars |= encode_ctx.chars_to_indices.keys()
                seen_chars.remove(LeftContext.UP)
                encode_ctx = encode_ctx.parent

        self._update_tree(self.left_ctx, c, encode_ctx)
        self.left_ctx = self.left_ctx[-self.coding_params.context_length + 1:] + c
        # print(f'ENCODED, CTX IS {self.left_ctx}')

    def decode(self, get_next_char: Callable[[FenwickTree], int]) -> Iterable[str]:
        decoded = []
        while True:
            char_ctx = self._go_down(self.left_ctx)

            if not self.coding_params.mask_seen:
                encode_ctx = char_ctx
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
                encode_ctx = char_ctx
                seen_chars = set()
                while True:
                    masked_distribution, masked_indices_to_ctx_indices, _ = encode_ctx.distribution.without_chars(
                        seen_chars, encode_ctx.chars_to_indices)
                    char_masked_idx = get_next_char(masked_distribution)
                    char = encode_ctx.indices_to_chars[masked_indices_to_ctx_indices[char_masked_idx]]
                    if char == LeftContext.UP:
                        seen_chars |= encode_ctx.chars_to_indices.keys()
                        seen_chars.remove(LeftContext.UP)
                        encode_ctx = encode_ctx.parent
                    else:
                        decoded.append(char)
                        yield char
                        break

            self._update_tree(self.left_ctx, char, encode_ctx)
            self.left_ctx = self.left_ctx[-self.coding_params.context_length + 1:] + char

    def _go_down(self, left_ctx):
        if self.root is None:
            return self.pseudo_root

        current = self.root
        for c in reversed(left_ctx):
            child = current.get_children().get(c)
            if child is None:
                return current
            current = child
        return current

    def _extend_down(self, left_ctx):
        if self.root is None:
            self.root = LeftContext(self.pseudo_root, '')
            return self.root

        current = self.root
        for c in reversed(left_ctx):
            child = current.get_children().get(c)
            if child is None:
                current = current.make_child(c)
            else:
                current = child
        return current

    def _update_tree(self, left_ctx, c, encoding_ctx):
        current = self._extend_down(left_ctx)

        if not self.coding_params.exclude_on_update:
            while True:
                current.add(c, self.coding_params.up_char_coding)
                current = current.parent
                if current == self.pseudo_root:
                    break
        else:

            if current != encoding_ctx:
                while True:
                    current.add(c, self.coding_params.up_char_coding)
                    if current == encoding_ctx:
                        break
                    current = current.parent
            else:
                while True:
                    char_count = current.get_char_count()
                    if not (char_count == 0 or char_count == 1 and current.contains(c)):
                        break
                    current.add(c, self.coding_params.up_char_coding)
                    current = current.parent


class LeftContext:
    UP = '↑'

    def __init__(self, parent: Optional['LeftContext'], s):
        self.s = s
        self.parent = parent
        self._children: Optional[Dict[str, 'LeftContext']] = None

        self.distribution = ExtendableFenwickTree(1)
        # self.distribution.add(0, 1)
        self.chars_to_indices = {LeftContext.UP: 0}
        self.indices_to_chars = {0: LeftContext.UP}
        self.seen_once_chars = None  # for B Up encoding when assigning freq zero (which will prob break projections)

    def add(self, c, up_char_coding: UpCharCodingAlrorithm):
        char_idx = self.chars_to_indices.get(c)
        if char_idx is None or (self.seen_once_chars is not None and c not in self.seen_once_chars):
            # new char
            if up_char_coding != UpCharCodingAlrorithm.B_OTHER_CHAR_COUNT:
                self.chars_to_indices[c] = len(self.chars_to_indices)
                self.indices_to_chars[len(self.indices_to_chars)] = c

            if up_char_coding == UpCharCodingAlrorithm.A_ALWAYS_ONE:
                self.distribution.inner[0] = 1
                self.distribution.append(1)
            elif up_char_coding == UpCharCodingAlrorithm.B_OTHER_CHAR_COUNT:
                self.seen_once_chars = self.seen_once_chars or {c}

                self.distribution.add(self.chars_to_indices[LeftContext.UP], 1)
            elif up_char_coding == UpCharCodingAlrorithm.C_PLUS_ONE_ON_NEW_CHAR:
                self.distribution.append(1)
                self.distribution.add(self.chars_to_indices[LeftContext.UP], 1)
            elif up_char_coding == UpCharCodingAlrorithm.D_PLUS_HALF_ON_NEW_CHAR:
                self.distribution.append(1)
                self.distribution.add(self.chars_to_indices[LeftContext.UP], 1)
            else:
                raise Exception()
        else:
            # already seen char
            if up_char_coding == UpCharCodingAlrorithm.B_OTHER_CHAR_COUNT and \
                    self.seen_once_chars is not None and c in self.seen_once_chars:

                self.seen_once_chars.remove(c)
                if len(self.seen_once_chars) == 0:
                    self.seen_once_chars = None

                char_idx = len(self.chars_to_indices)
                self.chars_to_indices[c] = char_idx
                self.indices_to_chars[char_idx] = c

                self.distribution.append(1)
            elif up_char_coding == UpCharCodingAlrorithm.D_PLUS_HALF_ON_NEW_CHAR:
                self.distribution.add(char_idx, 2)
            else:
                self.distribution.add(char_idx, 1)

    def get_children(self):
        self._children = self._children or {}
        return self._children

    def get_char_count(self):
        return len(self.chars_to_indices) + (len(self.seen_once_chars) if self.seen_once_chars is not None else 0) - 1

    def contains(self, char):
        return char in self.chars_to_indices or (self.seen_once_chars is not None and char in self.seen_once_chars)

    def make_child(self, c):
        child = LeftContext(self, c + self.s)
        self.get_children()[c] = child
        return child
