from dataclasses import dataclass
from typing import Any, TypeVar
from marshmallow import Schema, fields, post_load
import pytest
from multi_factories import BaseFactory, Factory, JSONToDomainFactory, lazy_attribute


T = TypeVar("T")


class BaseSchema(Schema):
    _domain_cls: type

    @post_load
    def to_domain(self, incoming_data: dict, **kwargs: Any) -> Any:  # noqa: ARG002
        return self._domain_cls(**incoming_data)


@dataclass
class ChildDomain:
    first_name: str
    second_name: str


@dataclass
class ParentDomain:
    first_name: str
    second_name: str
    children: list[ChildDomain]


class ChildSchema(BaseSchema):
    _domain_cls = ChildDomain

    first_name = fields.String(required=True)
    second_name = fields.String(required=True)


class ParentSchema(BaseSchema):
    _domain_cls = ParentDomain

    first_name = fields.String()
    second_name = fields.String()
    children = fields.Nested(ChildSchema, many=True)


class ChildFactory(Factory[ChildDomain]):
    first_name = "Billy"
    second_name = "Jim"


class ParentFactory(Factory[ParentDomain]):
    first_name = "Jim"
    second_name = "Jim"
    children = lazy_attribute(lambda: [ChildFactory.build()])


class ChildJSONToDomainFactory(JSONToDomainFactory[ChildDomain, ChildSchema]):
    first_name = "Billy"
    second_name = "Jim"


class ParentJSONToDomainFactory(JSONToDomainFactory[ParentDomain, ParentSchema]):
    first_name = "Jim"
    second_name = "Jim"
    children = lazy_attribute(lambda: [ChildJSONToDomainFactory.build().base])


def inject_factory_method(
    factory: type[BaseFactory], batch: bool = False
) -> pytest.MarkDecorator:
    if batch:
        return pytest.mark.parametrize(
            "factory_method", [factory.create_batch, factory.build_batch]
        )
    return pytest.mark.parametrize("factory_method", [factory])
