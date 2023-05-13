import os
import sys
import argparse
from coding.codec import StatisticEncoder, StatisticDecoder
from coding.coding_params import CodingParams, UpCharCodingAlrorithm
from coding.capitalization import get_cap_data, capitalize_iter, decapitalize_iter
from headers.header import Header
from headers.capitalization_header import CapitalizationHeader
from utils.iter_utils import iter_chars, write_chars, iter_bits, write_bits

def open_or_stdout(filename, **kwargs):
    if filename != '-':
        return open(filename, **kwargs)
    return os.fdopen(sys.stdout.fileno(), closefd=False, **kwargs)


def open_or_stdin(filename, **kwargs):
    if filename != '-':
        return open(filename, **kwargs)
    return os.fdopen(sys.stdin.fileno(), closefd=False, **kwargs)


def zip(source_file, dest_file, coding_params: CodingParams = CodingParams()):
    source_length = os.path.getsize(source_file)  # race condition, also not sure about precision
    header = Header(source_length, coding_params)
    with open_or_stdin(source_file, mode='r', encoding='iso-8859-1', newline='') as input_f, \
            open_or_stdout(dest_file, mode='wb') as dest_f:

        cap_data = None
        if header.coding_params.decapitalize:
            cap_data = get_cap_data(iter_chars(input_f))
            input_f.seek(0)

        dest_f.write(header.serialize())
        if cap_data is not None:
            dest_f.write(CapitalizationHeader(cap_data).serialize())

        iter_char = iter_chars(input_f) if not header.coding_params.decapitalize \
            else decapitalize_iter(iter_chars(input_f))
        encoder = StatisticEncoder(iter_char, coding_params)
        write_bits(encoder.encode(), dest_f)


def unzip(source_file, dest_file):
    with open_or_stdin(source_file, mode='rb') as input_f, \
            open_or_stdout(dest_file, mode='w', encoding='iso-8859-1', newline='') as dest_f:

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
    parser.add_argument('dest_file', type=str)
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


if __name__ == '__main__':
    console_app()
