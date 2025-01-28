from app.config import additional_tests


def additional_test(func):
    def wrapper(*args, **kwargs):
        if additional_tests:
            return func(*args, **kwargs)
        return None

    return wrapper
