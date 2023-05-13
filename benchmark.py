import os
import gc
import time
import threading
from dataclasses import dataclass
from typing import Iterable
from statistic_encoder import CodingParams
import random


@dataclass
class BenchmarkResult:
    # B: int
    # P: int

    original_size: int
    archive_size: int

    encode_time_s: int
    decode_time_s: int

    encode_mem_mb: int
    decode_mem_mb: int


def get_archiver_stats(zip_func, unzip_func, path_to_txt: str, coding_params: CodingParams):  # , B, P):
    import psutil

    max_mem_mb = -1

    def record_mem():
        nonlocal max_mem_mb
        mem_mb = psutil.Process().memory_info().rss // (1024 * 1024)
        if max_mem_mb == -1 or max_mem_mb < mem_mb:
            max_mem_mb = mem_mb

    def loop(interval):
        timer = threading.Timer(interval, loop, args=(interval,))
        timer.start()
        record_mem()

    gc.collect()
    loop(5)

    t0 = time.time()
    zip_func(path_to_txt, dest_file=f'{path_to_txt}.myzip', coding_params=coding_params)  # , B=B, P=P)
    t1 = time.time()
    max_mem_mb_encode = max_mem_mb

    gc.collect()  # yeaaaah its bad but its not like we need precise data
    max_mem_mb = -1

    t2 = time.time()
    unzip_func(f'{path_to_txt}.myzip', dest_file=f'{path_to_txt}.unzipped')
    t3 = time.time()
    max_mem_mb_decode = max_mem_mb

    gc.collect()
    max_mem_mb = -1

    with open(path_to_txt, newline='', encoding='iso-8859-1') as f_orig, \
            open(f'{path_to_txt}.unzipped', newline='', encoding='iso-8859-1') as f_new:
        orig_text = f_orig.read()
        new_text = f_new.read()
        if orig_text != new_text:
            raise Exception()

    original_size = os.path.getsize(path_to_txt)
    archive_size = os.path.getsize(f'{path_to_txt}.myzip')

    return BenchmarkResult(original_size, archive_size, round(t1 - t0), round(t3 - t2), max_mem_mb_encode,
                           max_mem_mb_decode)


def benchmark_all_params(zip_func, unzip_func, path_to_txt: str, coding_params: Iterable[CodingParams]):  # cap_params):
    import psutil

    for coding_param in coding_params:
        bench_res = get_archiver_stats(zip_func, unzip_func, path_to_txt, coding_param)
        print()
        print(coding_param)
        print(bench_res)

    # seen = set()
    # cap_params = list(cap_params)
    # coding_param = next(iter(coding_params))
    # while True:
    #     (B, P) = random.sample(cap_params, 1)[0]
    #     if (B, P) in seen:
    #         continue
    #     elif B / P < 10 or B / P > 500:
    #         r = random.random()
    #         if r < 0.1:
    #             seen.add((B, P))
    #         else:
    #             continue
    #     else:
    #         seen.add((B, P))
    #     print()
    #     print(f'B={B}, P={P}', coding_param)
    #     bench_res = get_archiver_stats(zip_func, unzip_func, path_to_txt, coding_param, B, P)
    #     print(bench_res)
