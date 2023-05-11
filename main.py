import struct
from fenwick import FenwickTree
from bitarray import bitarray
import argparse
import os
from dataclasses import dataclass
from codec import StatisticEncoder, StatisticDecoder


@dataclass
class Header:
    # little-endian 8b us, 1b us, 1b us, 1b us
    STRUCT_FMT = '< Q B B B'

    length: int
    ctx_len: int
    mask: bool
    exclude: bool

    @staticmethod
    def header_length():
        return struct.calcsize(Header.STRUCT_FMT)

    def serialize(self):
        return struct.pack(Header.STRUCT_FMT, self.length, self.ctx_len, self.mask, self.exclude)

    @staticmethod
    def deserialize(bytes):
        (length, ctx_len, mask, exclude) = struct.unpack(Header.STRUCT_FMT, bytes)
        return Header(length, ctx_len, mask > 0, exclude > 0)


@dataclass
class CodingParams:
    context_length: int = 6
    mask_seen: bool = False
    exclude_on_update: bool = False


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

    bit_chunk_size = 8 * chunk_size
    bits = bitarray(bit_chunk_size, endian='big')

    i = -1
    for i, bit in enumerate(iter_bits):
        res.append(bit)
        bits[i % bit_chunk_size] = bit
        if i % bit_chunk_size == bit_chunk_size - 1:
            bits.tofile(f)
            bits.clear()

    bits_left = (i + 1) % bit_chunk_size
    bytes_left = (bits_left + 7) // 8
    bits[:8 * bytes_left].tofile(f)

    print('WRITTEN BITS:')
    print(''.join(map(str, res)))


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

    f.write(''.join(chars[: (i + 1) % chunk_size]))

    print('WRITTEN CHARS:')
    print(''.join(res))


def zip(source_file, dest_file=None, coding_params: CodingParams = CodingParams()):
    dest_file = dest_file or f'{source_file}.myzip'

    source_length = os.path.getsize(source_file)  # race condition, also not sure about precision
    header = Header(
        source_length, coding_params.context_length, coding_params.mask_seen, coding_params.exclude_on_update)
    with open(source_file, mode='r', encoding='iso-8859-1') as input_f, \
            open(dest_file, mode='wb') as dest_f:
        dest_f.write(header.serialize())
        encoder = StatisticEncoder(iter_chars(input_f))
        write_bits(encoder.encode(), dest_f)


def unzip(source_file, dest_file=None):
    if dest_file is None:
        dest_file = dest_file[:-(len('.myzip'))] if source_file.endswith('.myzip') else f'{source_file}.original'

    with open(source_file, mode='rb') as input_f, \
            open(dest_file, mode='w', encoding='iso-8859-1') as dest_f:
        header = Header.deserialize(input_f.read(Header.header_length()))
        decoder = StatisticDecoder(iter_bits(input_f), header.length)
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

def test(f_name):
    zip(f_name, f'{f_name}.zip', CodingParams(context_length=3, mask_seen=False, exclude_on_update=False))
    unzip(f'{f_name}.zip', f'{f_name}.unzipped')

    with open(f_name, mode='r') as original_f:
        with open(f'{f_name}.unzipped') as unzipped_f:
            original = original_f.read()
            unzipped = unzipped_f.read()
            if original != unzipped:
                print('Files differ')
                raise AssertionError()
            else:
                print(f'PASSED: {f_name}')

if __name__ == '__main__':
    # console_app()
    # test('empty.txt')
    test('a.txt')

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
