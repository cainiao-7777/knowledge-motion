"""Small helpers shared by long-running generation and revision steps."""


class OperationCancelled(RuntimeError):
    """Raised when an operation has passed its allowed runtime."""


def check_cancelled(cancel_event):
    # Long steps call this at boundaries so timeout does not start more work.
    if cancel_event is not None and cancel_event.is_set():
        raise OperationCancelled('任务等待超时，已自动取消')
