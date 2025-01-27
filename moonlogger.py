import inspect
import time
from loguru import logger


class MoonLogger:
    time_dict = dict[str, float]()  # Dicionário estático para armazenar o tempo total por função

    @staticmethod
    def log_func(enabled: bool = True):
        def decorator(func):
            @logger.catch
            def wrapper(*args, **kwargs):
                # Medição do tempo de início
                start_time = time.perf_counter()

                if enabled:
                    # Log dos argumentos da função
                    try:
                        func_args = inspect.signature(func).bind(*args, **kwargs).arguments
                    except TypeError as e:
                        logger.error(f"Erro ao obter os argumentos da função {func.__qualname__}: {e}")
                        raise  # Re-raise the exception
                    func_args_str = ", ".join(map("{0[0]} = {0[1]!r}".format, func_args.items()))
                    logger.opt(depth=2).debug(f"{func.__qualname__}({func_args_str})".replace('{', '[').replace('}', ']'))

                # Execução da função
                result = func(*args, **kwargs)

                # Medição do tempo de término e cálculo da duração
                end_time = time.perf_counter()
                duration = end_time - start_time

                # Atualização do tempo total no dicionário
                func_name = func.__qualname__
                if func_name in MoonLogger.time_dict:
                    MoonLogger.time_dict[func_name] += duration
                else:
                    MoonLogger.time_dict[func_name] = duration

                if enabled:
                    # Log do resultado da função e do tempo gasto
                    logger.opt(depth=2).debug(f"{func.__qualname__} -> {result!r}".replace('{', '[').replace('}', ']'))

                return result

            return wrapper

        return decorator