import struct
from fenwick import FenwickTree
from bitarray import bitarray
import argparse
import os
from dataclasses import dataclass
from codec import StatisticEncoder, StatisticDecoder
from statistic_encoder import CodingParams, UpCharCodingAlrorithm
import itertools

@dataclass
class Header:
    # little-endian 8b us, 1b us, 1b us, 1b us
    STRUCT_FMT = '< Q B B B B'

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
            self.coding_params.up_char_coding.value)

    @staticmethod
    def deserialize(bytes):
        (length, ctx_len, mask, exclude, up_char_coding) = struct.unpack(Header.STRUCT_FMT, bytes)
        return Header(length, CodingParams(ctx_len, mask > 0, exclude > 0, UpCharCodingAlrorithm(up_char_coding)))


def iter_bits(f, chunk_size=5 * 1024):
    read_eof = False
    bits = bitarray(0, endian='big')
    while not read_eof:
        # bytes = f.read(chunk_size)

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
    # TODO DELETE
    res = []

    bits = bitarray(0, endian='big')
    for bit in iter_bits:
        res.append(bit)
        bits.append(bit)
        if len(bits) == 8 * chunk_size:
            bits.tofile(f)
            bits.clear()

        # if len(res) % 80000 == 0:
        #     print(f'Written {len(res) / 8} bytes of 500k')

    bits.tofile(f)

    # print('WRITTEN BITS:')
    # print(''.join(map(str, res)))


def write_chars(iter_chars, f, chunk_size=5 * 1024):
    # TODO DELETE
    res = []

    chars = [''] * chunk_size

    i = -1
    for i, char in enumerate(iter_chars):
        res.append(char)
        chars[i % chunk_size] = char
        if i % chunk_size == chunk_size - 1:
            f.write(''.join(chars))

        # if i % 10000 == 0:
        #     print(f'Written {i} chars of 1.7 mil')

    f.write(''.join(chars[: (i + 1) % chunk_size]))

    # print('WRITTEN CHARS:')
    # print(''.join(res))


def zip(source_file, dest_file=None, coding_params: CodingParams = CodingParams()):
    dest_file = dest_file or f'{source_file}.myzip'

    source_length = os.path.getsize(source_file)  # race condition, also not sure about precision
    header = Header(source_length, coding_params)
    with open(source_file, mode='r', encoding='iso-8859-1', newline='') as input_f, \
            open(dest_file, mode='wb') as dest_f:
        dest_f.write(header.serialize())
        encoder = StatisticEncoder(iter_chars(input_f), coding_params)
        write_bits(encoder.encode(), dest_f)


def unzip(source_file, dest_file=None):
    if dest_file is None:
        dest_file = dest_file[:-(len('.myzip'))] if source_file.endswith('.myzip') else f'{source_file}.original'

    with open(source_file, mode='rb') as input_f, \
            open(dest_file, mode='w', encoding='iso-8859-1', newline='') as dest_f:
        header = Header.deserialize(input_f.read(Header.header_length()))
        decoder = StatisticDecoder(iter_bits(input_f), header.length, header.coding_params)
        write_chars(decoder.decode(), dest_f)


def console_app():
    parser = argparse.ArgumentParser()

    parser.add_argument('mode', type=str, choices=['zip, unzip'])
    parser.add_argument('source_file', type=str)
    parser.add_argument('dest_file', type=str)
    parser.add_argument('-K', '--ctx_length', type=int, default=6)
    parser.add_argument('-m', '--mask', type=bool, default=False)
    parser.add_argument('-e', '--exclude', type=bool, default=False)

    args = parser.parse_args()

    if args.mode == 'zip':
        zip(args.source_file, args.dest_file, CodingParams(args.ctx_lengt, args.mask, args.exclude))
    elif args.mode == 'unzip':
        unzip(args.source_file, args.dest_file)

def test(f_name, coding_params=None):
    f_name = f'tests/{f_name}'

    params = itertools.product(
        [4, 5, 6],  # ctx_len
        [False, True],  # mask
        [False, True],  # exclude from upd
        list(UpCharCodingAlrorithm)
    )

    for ctx_len, mask, exclude, up_coding in params if coding_params is None else [coding_params]:
        coding_params = CodingParams(ctx_len, mask, exclude, up_coding)
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
    # console_app()

    # test('empty.txt')
    # test('a.txt')
    # test('aaaaaa.txt')
    # test('test.txt') # (3, True, False, UpCharCodingAlrorithm.A_ALWAYS_ONE))
    # test('aca.txt')
    # test('acag.txt')
    # test('acagaatagaga.txt')
    # test('accaccggacca.txt')
    # test('v dver\' vozli medvedica s medvejonkom.txt')
    # test('a_n_b_n.txt')
    # test('a_rn_b.txt')
    # test('Martin, George RR - Ice and Fire 4 - A Feast for Crows.txt')
    test('Mini-Martin.txt')

# if __name__ == '__main__':
#     pass
# fenwick_tree = FenwickTree(15)
# fenwick_tree.init([10, 4, 0, 2, 16] * 3)
# fenwick_tree.add(3, 7)  # Adds 7 to element 3's frequency
# fenwick_tree.prefix_sum(5)
# fenwick_tree.range_sum(5, 10)
# freq_10 = fenwick_tree[10]
# freqs = fenwick_tree.frequencies()
# print('hi')


# See PyCharm help at https://www.jetbrains.com/help/pycharm/
