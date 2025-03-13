from dataclasses import dataclass
from typing import Any
import pytest
from multi_factory import BaseFactory


@dataclass
class ChildDomain:
    first_name: str
    second_name: str


@dataclass
class ParentDomain:
    first_name: str
    second_name: str
    children: list[ChildDomain]


def inject_factory_method(
    factory: type[BaseFactory[Any, Any, Any]], batch: bool = False
) -> pytest.MarkDecorator:
    if batch:
        return pytest.mark.parametrize(
            "factory_method", [factory.create_batch, factory.build_batch]
        )
    return pytest.mark.parametrize("factory_method", [factory])
