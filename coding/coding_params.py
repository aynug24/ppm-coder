from dataclasses import dataclass
from enum import Enum


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
    context_length: int = 5
    mask_seen: bool = True
    exclude_on_update: bool = False
    up_char_coding: UpCharCodingAlrorithm = UpCharCodingAlrorithm.A_ALWAYS_ONE
    decapitalize: bool = False
