from typing import Any, Callable

import factory

from multi_factory import BaseFactory


def lazy_attribute(
    func: Callable[..., Any], *args: Any, inject_lazy_stub: bool = False, **kwargs: Any
) -> Any:
    """Convenience function that wraps `factory.LazyAttribute`.

    If `inject_lazy_stub` is `True`, the LazyStub for the current factory will get passed to `func` as the first argument.
    This allows `func` to have access to all other computed values in the factory.
    """
    if inject_lazy_stub:
        return factory.LazyAttribute(lambda obj: func(obj, *args, **kwargs))
    return factory.LazyAttribute(lambda _: func(*args, **kwargs))


def sub_factory(sub_factory: type[BaseFactory[Any, Any, Any]], **kwargs: Any) -> Any:
    """Convenience function that wraps `factory.SubFactory`."""
    return factory.SubFactory(sub_factory, **kwargs)
