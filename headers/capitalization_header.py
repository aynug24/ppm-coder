import struct
import dataclasses
from dataclasses import dataclass
import itertools
from coding.capitalization import CapitalizationData, ProperName
from utils.ternary_encoding import encode_numbers, decode_numbers
from utils.iter_utils import bits_to_bytes, iter_bits
from typing import List, Iterable


@dataclass
class CapitalizationHeader:
    # little-endian 8b us, 8b us
    LENGTHS_FMT = '< Q Q'
    cap_data: CapitalizationData

    def serialize(self) -> bytes:
        (proper_names, rule_exceptions) = (self.cap_data.proper_names, self.cap_data.rule_exceptions)
        serialized = []
        serialized.append(struct.pack(CapitalizationHeader.LENGTHS_FMT, len(proper_names), len(rule_exceptions)))
        serialized.extend(self._encode_proper_names(proper_names))
        serialized.append(self._encode_exceptions(rule_exceptions))
        return b''.join(serialized)

    # можно сильно компактнее конечно, но текст сжимать мы уже умеем) + имён достаточно мало
    def _encode_string(self, s: str) -> bytes:
        if '\0' in s:
            raise Exception('No zero byte in proper names, please')
        return s.encode('iso-8859-1') + b'\0'

    def _encode_proper_names(self, proper_names: List[ProperName]) -> Iterable[bytes]:
        sorted_names = list(sorted(proper_names, key=lambda pn: pn.from_pos))
        for i in range(len(sorted_names) - 1, 0, -1):
            sorted_names[i] = dataclasses.replace(
                sorted_names[i], from_pos=sorted_names[i].from_pos - sorted_names[i - 1].from_pos)
        return (self._encode_proper_name(proper_name) for proper_name in sorted_names)

    def _encode_proper_name(self, proper_name: ProperName) -> bytes:
        name_bytes = self._encode_string(proper_name.word)
        from_pos_bytes = bits_to_bytes(encode_numbers([proper_name.from_pos]))
        return b''.join((name_bytes, from_pos_bytes))

    def _encode_exceptions(self, exceptions: List[int]) -> bytes:
        exceptions_diffs = (
            exceptions[i] - (exceptions[i - 1] if i > 0 else 0)
            for i in range(len(exceptions))
        )
        return bits_to_bytes(encode_numbers(exceptions_diffs))

    @staticmethod
    def deserialize(f):
        lengths_bytes = f.read(struct.calcsize(CapitalizationHeader.LENGTHS_FMT))
        proper_names_len, exceptions_len = struct.unpack(CapitalizationHeader.LENGTHS_FMT, lengths_bytes)
        proper_names = CapitalizationHeader._read_proper_names(proper_names_len, f)
        exceptions = CapitalizationHeader._read_exceptions(exceptions_len, f)
        return CapitalizationHeader(CapitalizationData(proper_names, exceptions))

    @staticmethod
    def _read_string(f):
        res = []
        while True:
            c = f.read(1)
            if c == b'\0':
                break
            res.append(c.decode('iso-8859-1'))
        return ''.join(res)

    @staticmethod
    def _read_proper_names(proper_names_len, f) -> List[ProperName]:
        proper_names = []
        for _ in range(proper_names_len):
            word = CapitalizationHeader._read_string(f)
            from_pos = next(decode_numbers(iter_bits(f, chunk_size=1)))  # сильно опирающийся на ленивость код
            proper_names.append(ProperName(word, from_pos))

        for i in range(1, len(proper_names)):
            proper_names[i] = dataclasses.replace(
                proper_names[i], from_pos=proper_names[i].from_pos + proper_names[i - 1].from_pos)
        return proper_names

    @staticmethod
    def _read_exceptions(exceptions_len, f):
        exceptions = list(itertools.islice(decode_numbers(iter_bits(f, chunk_size=1)), exceptions_len))  # same
        for i in range(1, len(exceptions)):
            exceptions[i] += exceptions[i - 1]
        return exceptions
