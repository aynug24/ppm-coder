from typing import List, Iterator, Iterable


def ternary(n):
    if n == 0:
        return ''
    digits = []
    while n:
        n, r = divmod(n, 3)
        digits.append(str(r))
    return ''.join(reversed(digits))


# this algo uses full two bits for the first digit
# since it has to be able to encode zero
def encode_numbers(nums: Iterable[int]) -> Iterable[int]:
    for num in nums:
        num3 = ternary(num)
        for digit in num3:
            yield from [0, 0] if digit == '0' \
                else [0, 1] if digit == '1' \
                else [1, 0]
        yield from [1, 1]


def decode_numbers(iter_bits: Iterator[int]) -> Iterable[int]:
    while True:
        num = 0
        while True:
            (next_digit, next_next_digit) = next(iter_bits), next(iter_bits)
            if next_digit == 1 and next_next_digit == 1:
                yield num
                break

            num *= 3
            if next_next_digit == 1:
                num += 1
            elif next_digit == 1:
                num += 2
