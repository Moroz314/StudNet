from fastapi import HTTPException, status


def exception_handler(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)

        except HTTPException as e:
            raise e

        except Exception as e:
            print(e)
            raise e

    return wrapper