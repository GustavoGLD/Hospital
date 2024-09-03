from contextlib import ContextDecorator
from functools import wraps, partial
from loguru import logger
import inspect


def log_func(*args1):
    def contextualizing(func):
        @wraps(func)
        def wrapper(*args2, **kwargs):
            func_args = inspect.signature(func).bind(*args2, **kwargs).arguments
            func_args_str = ", ".join(map("{0[0]}={0[1]!r}".format, func_args.items()))
            logger.opt(depth=1).info(f'Calling {func.__name__}({func_args_str})')
            result = func(*args2, **kwargs)
            logger.opt(depth=1).info(f'{func.__name__} -> {result!r}')
        return wrapper
    return contextualizing


class Context:
    def __init__(self, logc: list[str] | None = None, addlogc : list[str] | None = None):
        if addlogc is None:
            addlogc = list[str]()
        logc = logc.copy()
        logc += addlogc
        self.logcontext = logc

    def __enter__(self) -> list[str]:
        logger.opt(depth=1).debug(f'Entering context {self.logcontext}')
        return self.logcontext

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.opt(depth=1).debug(f'Exiting context {self.logcontext}')


def log_context(*args: str):
    wlogc = list[str](args)

    def contextualizing(func):
        @wraps(func)
        def wrapper(*args2, **kwargs):
            if 'logc' not in kwargs:
                raise ValueError(f'`logc=...` not in `{func.__name__}` kwargs. '
                                 f'always use param `logc=...` in function calls')
            kwargs['logc'] = kwargs['logc'].copy()
            kwargs['logc'] += wlogc
            func(*args2, **kwargs)
        return wrapper
    return contextualizing


@log_context('3')
def funcao2(logc: list[str]):
    print(f'{funcao2.__name__}.{logc=}')


@log_context('5')
def funcao3(logc: list[str]):
    print(f'{funcao3.__name__}.{logc=}')


@log_context('2')
def funcao1(logc: list[str]):
    print(f'{funcao1.__name__}.{logc=}')
    funcao2(logc=logc)

    with Context(logc=logc, addlogc=['4']) as logc:
        print(f'{logc=}')
        funcao3(logc=logc)


if __name__ == '__main__':
    # somar(a=1, b=2)
    with Context(logc=['1']) as logc:
        print(f'{logc=}')
        funcao1(logc=logc)



