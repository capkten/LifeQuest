from functools import wraps


def rollback_on_error(method):
    @wraps(method)
    def guarded(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except Exception:
            self.db.rollback()
            raise

    return guarded
