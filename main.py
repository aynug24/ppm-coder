import struct
from fenwick import FenwickTree
from bitarray import bitarray
import argparse
import os
import dataclasses
from dataclasses import dataclass
from codec import StatisticEncoder, StatisticDecoder
from statistic_encoder import CodingParams, UpCharCodingAlrorithm
import itertools
from capitalization import get_cap_data, capitalize_iter, CapitalizationData, ProperName, decapitalize_iter
from ternary_encoding import encode_numbers, decode_numbers
from typing import Iterator, List, Iterable
from benchmark import benchmark_all_params
import sys

def bits_to_bytes(iter_bits: Iterator[int]) -> bytes:
    bits = bitarray(endian='big')
    for bit in iter_bits:
        bits.append(bit)
    return bits.tobytes()


@dataclass
class Header:
    # little-endian 8b us, 1b us, 1b us, 1b us, 1b us, 1b us
    STRUCT_FMT = '< Q B B B B B'

    length: int
    coding_params: CodingParams

    @staticmethod
    def header_length():
        return struct.calcsize(Header.STRUCT_FMT)

    def serialize(self):
        return struct.pack(
            Header.STRUCT_FMT,
            self.length,
            self.coding_params.context_length,
            self.coding_params.mask_seen,
            self.coding_params.exclude_on_update,
            self.coding_params.up_char_coding.value,
            self.coding_params.decapitalize)

    @staticmethod
    def deserialize(bytes):
        (length, ctx_len, mask, exclude, up_char_coding, decapitalize) = struct.unpack(Header.STRUCT_FMT, bytes)
        return Header(length,
                      CodingParams(ctx_len, mask > 0, exclude > 0, UpCharCodingAlrorithm(up_char_coding), decapitalize)
                      )


@dataclass
class CapitalizationHeader:
    # little-endian 8b us, 8b us
    LENGTHS_FMT = '< Q Q'
    cap_data: CapitalizationData

    def serialize(self) -> bytes:
        (proper_names, rule_exceptions) = (self.cap_data.proper_names, self.cap_data.rule_exceptions)
        serialized = []
        serialized.append(struct.pack(CapitalizationHeader.LENGTHS_FMT, len(proper_names), len(rule_exceptions)))
        pn = b''.join(self._encode_proper_names(proper_names))
        # pn_len = len(b''.join(pn))
        serialized.append(pn)
        ex = self._encode_exceptions(rule_exceptions)
        # ex_len = len(ex)
        serialized.append(ex)
        res = b''.join(serialized)
        # print(f'{len(res)}b cap header: proper names {len(pn)}b, exceptions {len(ex)}b')
        return res


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


def iter_bits(f, chunk_size=5 * 1024):
    read_eof = False
    bits = bitarray(0, endian='big')
    while not read_eof:
        try:
            bits.fromfile(f, chunk_size)
        except EOFError:
            read_eof = True

        yield from bits
        bits.clear()


def iter_chars(f, chunk_size=5 * 1024):
    while True:
        chars = f.read(chunk_size)
        if not chars:
            return
        yield from chars


def write_bits(iter_bits, f, chunk_size=5 * 1024):
    bits = bitarray(0, endian='big')
    for bit in iter_bits:
        bits.append(bit)
        if len(bits) == 8 * chunk_size:
            bits.tofile(f)
            bits.clear()

    bits.tofile(f)


def write_chars(iter_chars, f, chunk_size=5 * 1024):
    chars = [''] * chunk_size

    i = -1
    for i, char in enumerate(iter_chars):
        chars[i % chunk_size] = char
        if i % chunk_size == chunk_size - 1:
            f.write(''.join(chars))

    f.write(''.join(chars[: (i + 1) % chunk_size]))


def zip(source_file, dest_file=None, coding_params: CodingParams = CodingParams(), B=1000, P=15):
    dest_file = dest_file or f'{source_file}.myzip'

    source_length = os.path.getsize(source_file)  # race condition, also not sure about precision
    header = Header(source_length, coding_params)
    with open(source_file, mode='r', encoding='iso-8859-1', newline='') as input_f, \
            open(dest_file, mode='wb') as dest_f:

        cap_data = None
        if header.coding_params.decapitalize:
            cap_data = get_cap_data(iter_chars(input_f), B, P)
            input_f.seek(0)

        dest_f.write(header.serialize())
        if cap_data is not None:
            dest_f.write(CapitalizationHeader(cap_data).serialize())

        iter_char = iter_chars(input_f) if not header.coding_params.decapitalize \
            else decapitalize_iter(iter_chars(input_f))
        encoder = StatisticEncoder(iter_char, coding_params)
        write_bits(encoder.encode(), dest_f)


def unzip(source_file, dest_file=None):
    if dest_file is None:
        dest_file = source_file[:-(len('.myzip'))] if source_file.endswith('.myzip') else f'{source_file}.original'

    with open(source_file, mode='rb') as input_f, \
            open(dest_file, mode='w', encoding='iso-8859-1', newline='') as dest_f:
        header = Header.deserialize(input_f.read(Header.header_length()))

        cap_data = None
        if header.coding_params.decapitalize:
            cap_data = CapitalizationHeader.deserialize(input_f).cap_data

        decoder = StatisticDecoder(iter_bits(input_f), header.length, header.coding_params)

        iter_char = decoder.decode() if not header.coding_params.decapitalize \
            else capitalize_iter(decoder.decode(), cap_data)
        write_chars(iter_char, dest_f)


def console_app():
    parser = argparse.ArgumentParser()

    parser.add_argument('mode', type=str, choices=['zip', 'unzip'])
    parser.add_argument('source_file', type=str)
    parser.add_argument('dest_file', type=str, nargs='?', default=sys.stdout)
    parser.add_argument('-K', '--ctx_length', type=int, default=5)
    parser.add_argument('-m', '--mask', type=bool, default=True)
    parser.add_argument('-e', '--exclude', type=bool, default=False)
    parser.add_argument('-u', '--up_algo', type=str, choices=['A', 'B', 'C', 'D'], default='D')
    parser.add_argument('-c', '--decapitalize', type=bool, default=False)

    args = parser.parse_args()

    if args.mode == 'zip':
        zip(args.source_file, args.dest_file,
            CodingParams(args.ctx_length, args.mask, args.exclude,
                         UpCharCodingAlrorithm.from_letter(args.up_algo), args.decapitalize))
    elif args.mode == 'unzip':
        unzip(args.source_file, args.dest_file)


def test(f_name, coding_params=None):
    f_name = f'tests/{f_name}'

    params = itertools.product(
        [4, 5, 6],  # ctx_len
        [False, True],  # mask
        [False, True],  # exclude from upd
        list(UpCharCodingAlrorithm),  # up encoding algo
        [False, True]  # decapitalize
    )

    for ctx_len, mask, exclude, up_coding, decapitalize in params if coding_params is None else [coding_params]:
        coding_params = CodingParams(ctx_len, mask, exclude, up_coding, decapitalize)
        zip(f_name, f'{f_name}.zip', coding_params)
        unzip(f'{f_name}.zip', f'{f_name}.unzipped')

        with open(f_name, mode='r', encoding='iso-8859-1') as original_f:
            with open(f'{f_name}.unzipped', mode='r', encoding='iso-8859-1') as unzipped_f:
                original = original_f.read()
                unzipped = unzipped_f.read()
                if original != unzipped:
                    print('Files texts differ')
                    raise AssertionError()

        with open(f_name, mode='rb') as original_f:
            with open(f'{f_name}.unzipped', mode='rb') as unzipped_f:
                original = original_f.read()
                unzipped = unzipped_f.read()
                if original != unzipped:
                    print('Files binaries differ')
                    raise AssertionError()

        print(f'Passed {ctx_len}, {mask}, {exclude}, {up_coding} for {f_name}')
    print(f'PASSED ALL FOR {f_name}')


if __name__ == '__main__':
    console_app()

    # params = itertools.product(
    #     [4, 5, 6],  # ctx_len
    #     [False, True],  # mask
    #     [False, True],  # exclude from upd
    #     list(UpCharCodingAlrorithm),  # up encoding algo
    #     [False, True]  # decapitalize
    # )

    # params = itertools.product(
    #     [4],  # ctx_len
    #     [False],  # mask
    #     [False],  # exclude from upd
    #     [UpCharCodingAlrorithm.D_PLUS_HALF_ON_NEW_CHAR],  # up encoding algo
    #     [True, False]  # decapitalize
    # )



    # params = itertools.product(
    #     [4, 5, 6],  # ctx_len
    #     [False, True],  # mask
    #     [False, True],  # exclude from upd
    #     [UpCharCodingAlrorithm.D_PLUS_HALF_ON_NEW_CHAR],  # up encoding algo
    #     [False]  # decapitalize
    # )
    #
    # coding_params = [
    #     CodingParams(ctx_len, mask, exclude, up_coding, decapitalize)
    #     for ctx_len, mask, exclude, up_coding, decapitalize in params
    # ]
    #
    # cap_params = itertools.product(
    #     [10, 20, 30, 50, 70, 100, 150, 200, 300, 500, 700, 1000, 1200, 1500, 1700, 2000, 3000, 4000], # Buff
    #     [5, 7, 9, 10, 11, 13, 15, 17, 20, 25, 30, 35] # Pos thresh
    # )
    #
    # benchmark_all_params(zip, unzip, 'tests/Martin, George RR - Ice and Fire 4 - A Feast for Crows.txt', coding_params)#,# cap_params)

    # test('empty.txt')
    # test('a.txt')
    # test('B.txt')
    # test('BB.txt')
    # test('BBB.txt')
    # test('B. B.txt')
    # test('aaaaaa.txt')
    # test('test.txt') # (3, True, False, UpCharCodingAlrorithm.A_ALWAYS_ONE))
    # test('aca.txt')
    # test('acag.txt')
    # test('acagaatagaga.txt')
    # test('accaccggacca.txt')
    # test('v dver\' vozli medvedica s medvejonkom.txt')
    # test('a_n_b_n.txt')
    # test('a_rn_b.txt')
    # loop(5)
    # test('Martin, George RR - Ice and Fire 4 - A Feast for Crows.txt',
    #      (6, True, True, UpCharCodingAlrorithm.D_PLUS_HALF_ON_NEW_CHAR, False))
    # test('Mini-Martin.txt', (6, True, False, UpCharCodingAlrorithm.D_PLUS_HALF_ON_NEW_CHAR, True))
