import io
import json
import time

from pytracing import TraceProfiler


def function_a(x):
    print('sleeping {}'.format(x))
    time.sleep(x)
    return


def function_b(x):
    function_a(x)


def main():
    function_a(1)
    function_b(2)


if __name__ == '__main__':
    with io.open('./trace.out', mode='w', encoding='utf-8') as fh:
        tp = TraceProfiler(output=fh)
        tp.init()
        main()
        tp.shutdown()
        print('wrote trace.out')

    # ensure the output is at least valid JSON
    with io.open('./trace.out', encoding='utf-8') as fh:
        json.load(fh)
