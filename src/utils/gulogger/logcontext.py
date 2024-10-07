import sys
from contextlib import ContextDecorator
from functools import wraps, partial
from typing import Any, Optional

from loguru import logger
import inspect
from copy import deepcopy

LogC = dict[str, Any]


class MyLogger:
    def __init__(self, add_tags : list[str] | None, logc: Optional[LogC] = None):
        if logc is None:
            logc = dict[str, Any]()
            logc['tags'] = []

        self.logcontext = deepcopy(logc)
        self.logcontext['tags'] += add_tags
        #self.logcontext.update({'tags': add_tags})

        self.__internal_logcontext = deepcopy(self.logcontext)
        self.__internal_logcontext['tags'].append('context_managing')

    def __enter__(self) -> LogC:
        logger.opt(depth=1).debug('Entering context {tags}', **self.__internal_logcontext)
        return self.logcontext

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.opt(depth=1).debug('Exiting context {tags}', **self.__internal_logcontext)

    @staticmethod
    def decorate_function(add_extra: list[str] = None):  # type: ignore
        def contextualizing(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if 'logc' not in kwargs:
                    error_msg = f'`logc=...` not in `{func.__name__}` kwargs. ' \
                                f'always use param `logc=...` in function calls'
                    logger.opt(depth=1).info(error_msg)
                    raise ValueError(error_msg)
                if 'tags' not in kwargs['logc']:
                    logger.opt(depth=1).info(f'creating the tags context from scratch')
                    kwargs['logc']['tags'] = list[str]()
                kwargs['logc'] = deepcopy(kwargs['logc'])
                if add_extra is not None:
                    kwargs['logc']['tags'] += add_extra
                kwargs['logc']['tags'].append(func.__name__)
                logger.opt(depth=1).debug(f'Executing {func.__name__}', **kwargs['logc'])
                return func(*args, **kwargs)
            return wrapper
        return contextualizing


@MyLogger.decorate_function(add_extra=['3'])
def funcao1(logc: dict[str, Any]):
    logger.opt(depth=0).debug('tags: {tags}', **logc)


@MyLogger.decorate_function(add_extra=['4'])
def funcao2(logc: dict[str, Any]):
    logger.opt(depth=0).debug('tags: {tags}', **logc)
    with MyLogger(logc=logc, add_tags=['5']) as logc:
        logger.opt(depth=0).debug('tags: {tags}', **logc)
        funcao1(logc=logc)


if __name__ == '__main__':
    with MyLogger(add_tags=['1']) as logc:
        logger.debug('tags: {tags}', **logc)
        funcao1(logc=logc)
        funcao2(logc=logc)

        with MyLogger(logc=logc, add_tags=['2']) as logc:
            logger.debug('tags: {tags}', **logc)
            funcao1(logc=logc)
            funcao2(logc=logc)
