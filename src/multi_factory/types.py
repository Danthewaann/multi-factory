from enum import Enum
from typing import Any, Callable, Protocol, TypeVar


class Schema(Protocol):
    @classmethod
    def domain_cls(cls) -> type:
        ...

    def load(self, *args: Any, **kwargs: Any) -> Any:
        ...


BaseT = TypeVar("BaseT")
DomainT = TypeVar("DomainT", bound="Any")
SchemaT = TypeVar("SchemaT", bound="Schema | None")
EnumConversionMap = dict[type[Enum], Callable[[Enum], Any]]
