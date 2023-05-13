import struct
from dataclasses import dataclass
from coding.coding_params import CodingParams, UpCharCodingAlrorithm

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

