import inspect

from loguru import logger


def log_func(func):
    @logger.catch
    def wrapper(*args, **kwargs):
        func_args = inspect.signature(func).bind(*args, **kwargs).arguments
        func_args_str = ", ".join(map("{0[0]} = {0[1]!r}".format, func_args.items()))
        logger.debug(f"{func.__name__}({func_args_str})".replace('{', '[').replace('}', ']'), **kwargs['logc'])
        result = func(*args, **kwargs)
        logger.debug(f"{func.__name__} -> {result!r}".replace('{', '[').replace('}', ']'), **kwargs['logc'])
        return result

    return wrapper