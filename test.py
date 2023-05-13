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

def run_tests():
    pass
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