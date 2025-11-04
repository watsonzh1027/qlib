from typing import Any, Callable

def _default_okx_factory(*args: Any, **kwargs: Any) -> Any:
    # If this factory is invoked unpatched, raise to make misuse explicit in tests.
    raise RuntimeError(
        "Test shim ccxtpro.okx called — tests should monkeypatch ccxtpro.okx "
        "to return a fake exchange, or run with a real ccxtpro installed."
    )

okx: Callable[..., Any] = _default_okx_factory

__all__ = ["okx"]
