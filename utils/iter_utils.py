from typing import Iterable
from bitarray import bitarray

def bits_to_bytes(iter_bits: Iterable[int]) -> bytes:
    bits = bitarray(endian='big')
    for bit in iter_bits:
        bits.append(bit)
    return bits.tobytes()


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
