from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable

import pytest

from marshmallow import Schema, fields
from multi_factories import (
    BaseFactory,
    Factory,
    FactoryError,
    JSONToDomainFactory,
    JSONToDomainFactoryResult,
    lazy_attribute,
)


@dataclass
class ChildDomain:
    first_name: str
    second_name: str


@dataclass
class ParentDomain:
    first_name: str
    second_name: str
    children: list[ChildDomain]


class ChildSchema(Schema):
    first_name = fields.String()
    second_name = fields.String()


class ParentSchema(Schema):
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


@pytest.fixture
def child_dict() -> dict[str, Any]:
    return {"first_name": "Billy", "second_name": "Jim"}


@pytest.fixture
def parent_dict(child_dict: dict[str, Any]) -> dict[str, Any]:
    return {"first_name": "Jim", "second_name": "Jim", "children": [child_dict]}


@pytest.fixture
def child_domain() -> ChildDomain:
    return ChildDomain(first_name="Billy", second_name="Jim")


@pytest.fixture
def parent_domain(child_domain: ChildDomain) -> ParentDomain:
    return ParentDomain(first_name="Jim", second_name="Jim", children=[child_domain])


@pytest.fixture
def json_to_domain_factory_result(
    parent_dict: dict[str, Any], parent_domain: ParentDomain
) -> JSONToDomainFactoryResult[ParentDomain]:
    return JSONToDomainFactoryResult(
        base=parent_dict, json=parent_dict, domain=parent_domain
    )


def inject_factory_method(
    factory: type[BaseFactory], batch: bool = False
) -> pytest.MarkDecorator:
    if batch:
        return pytest.mark.parametrize(
            "factory_method", [factory.create_batch, factory.build_batch]
        )
    return pytest.mark.parametrize(
        "factory_method", [factory, factory.create, factory.build]
    )


@inject_factory_method(ParentJSONToDomainFactory)
def test_json_to_domain_factory(
    factory_method: Callable,
    json_to_domain_factory_result: JSONToDomainFactoryResult[ParentDomain],
) -> None:
    model = factory_method()
    assert model == json_to_domain_factory_result


@inject_factory_method(ParentFactory)
def test_factory(factory_method: Callable, parent_domain: ParentDomain) -> None:
    model = factory_method()
    assert model == parent_domain


@inject_factory_method(ParentJSONToDomainFactory, batch=True)
def test_json_to_domain_factory_batch(
    factory_method: Callable,
    json_to_domain_factory_result: JSONToDomainFactoryResult[ParentDomain],
) -> None:
    models = factory_method(size=1)
    assert models == [json_to_domain_factory_result]


@inject_factory_method(ParentFactory, batch=True)
def test_factory_batch(factory_method: Callable, parent_domain: ParentDomain) -> None:
    models = factory_method(size=1)
    assert models == [parent_domain]


def test_factory_excludes(child_domain: ChildDomain) -> None:
    # `other_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesFactory(Factory[ChildDomain], exclude="other_field"):
        first_name = "Billy"
        second_name = "Jim"
        other_field = "Bob"

    assert _ExcludesFactory() == child_domain


def test_factory_excludes_merges_with_superclass(child_domain: ChildDomain) -> None:
    # `other_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesFactory(Factory[ChildDomain], exclude="another_field"):
        first_name = "Billy"
        second_name = "Jim"
        another_field = "Bob"

    # `other_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesDerivedFactory(_ExcludesFactory, exclude="other_field"):
        other_field = "Bob"

    assert _ExcludesDerivedFactory() == child_domain


def test_factory_excludes_in_meta_inner_class(child_domain: ChildDomain) -> None:
    # `other_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesFactory(Factory[ChildDomain]):
        class Meta:
            exclude = ("other_field",)

        first_name = "Billy"
        second_name = "Jim"
        other_field = "Bob"

    assert _ExcludesFactory() == child_domain


def test_factory_excludes_in_meta_inner_class_merges_with_superclass(
    child_domain: ChildDomain,
) -> None:
    # `another_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesFactory(Factory[ChildDomain]):
        class Meta:
            exclude = ("another_field",)

        first_name = "Billy"
        second_name = "Jim"
        another_field = "Bob"

    # `other_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesDerivedFactory(_ExcludesFactory):
        class Meta:
            exclude = ("other_field",)

        other_field = "Bob"

    assert _ExcludesDerivedFactory() == child_domain


def test_json_to_domain_factory_excludes(
    child_dict: dict[str, Any], child_domain: ChildDomain
) -> None:
    # `other_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesFactory(
        JSONToDomainFactory[ChildDomain, ChildSchema], exclude="other_field"
    ):
        first_name = "Billy"
        second_name = "Jim"
        other_field = "Bob"

    assert _ExcludesFactory() == JSONToDomainFactoryResult(
        base=child_dict, json=child_dict, domain=child_domain
    )


def test_json_to_domain_factory_excludes_merges_with_superclass(
    child_dict: dict[str, Any], child_domain: ChildDomain
) -> None:
    # `another_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesFactory(
        JSONToDomainFactory[ChildDomain, ChildSchema], exclude="another_field"
    ):
        first_name = "Billy"
        second_name = "Jim"
        another_field = "Bob"

    # `other_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesDerivedFactory(_ExcludesFactory, exclude="other_field"):
        other_field = "Bob"

    assert _ExcludesDerivedFactory() == JSONToDomainFactoryResult(
        base=child_dict, json=child_dict, domain=child_domain
    )


def test_json_to_domain_factory_excludes_in_meta_inner_class(
    child_dict: dict[str, Any], child_domain: ChildDomain
) -> None:
    # `other_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesFactory(JSONToDomainFactory[ChildDomain, ChildSchema]):
        class Meta:
            exclude = ("other_field",)

        first_name = "Billy"
        second_name = "Jim"
        other_field = "Bob"

    assert _ExcludesFactory() == JSONToDomainFactoryResult(
        base=child_dict, json=child_dict, domain=child_domain
    )


def test_json_to_domain_factory_excludes_in_meta_inner_class_merges_with_superclass(
    child_dict: dict[str, Any], child_domain: ChildDomain
) -> None:
    # `another_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesFactory(JSONToDomainFactory[ChildDomain, ChildSchema]):
        class Meta:
            exclude = ("another_field",)

        first_name = "Billy"
        second_name = "Jim"
        another_field = "Bob"

    # `other_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesDerivedFactory(_ExcludesFactory):
        class Meta:
            exclude = ("other_field",)

        other_field = "Bob"

    assert _ExcludesDerivedFactory() == JSONToDomainFactoryResult(
        base=child_dict, json=child_dict, domain=child_domain
    )


def test_json_to_domain_factory_enum_conversion_map() -> None:
    class _TempEnum(Enum):
        FIRST = auto()

    @dataclass
    class _TempDomain:
        first: _TempEnum

    class _TempSchema(Schema):
        first = fields.Enum(_TempEnum)

    # We will use `_TempEnum.name.upper()` in the below factory when we convert
    # `first` into a JSON serialisable form
    class _EnumConverionFactory(
        JSONToDomainFactory[_TempDomain, _TempSchema],
        enum_conversion_map={_TempEnum: lambda enum: enum.name.upper()},
    ):
        first = _TempEnum.FIRST

    assert _EnumConverionFactory() == JSONToDomainFactoryResult(
        base={"first": _TempEnum.FIRST},
        json={"first": "FIRST"},
        domain=_TempDomain(first=_TempEnum.FIRST),
    )


def test_json_to_domain_factory_enum_conversion_map_merges_with_superclass() -> None:
    class _TempEnum(Enum):
        FIRST = auto()

    class _TempEnum2(Enum):
        SECOND = auto()

    @dataclass
    class _TempDomain:
        first: _TempEnum
        second: _TempEnum2

    class _TempSchema(Schema):
        first = fields.Enum(_TempEnum)
        second = fields.Enum(_TempEnum2)

    # We will use `_TempEnum.name.upper()` in the below factory when we convert
    # `first` into a JSON serialisable form
    class _EnumConverionFactory(
        JSONToDomainFactory[_TempDomain, _TempSchema],
        enum_conversion_map={_TempEnum: lambda enum: enum.name.upper()},
    ):
        first = _TempEnum.FIRST
        second = _TempEnum2.SECOND

    class _EnumConverionDerivedFactory(
        _EnumConverionFactory,
        enum_conversion_map={_TempEnum2: lambda enum: enum.name.lower()},
    ):
        pass

    assert _EnumConverionDerivedFactory() == JSONToDomainFactoryResult(
        base={"first": _TempEnum.FIRST, "second": _TempEnum2.SECOND},
        json={"first": "FIRST", "second": "second"},
        domain=_TempDomain(first=_TempEnum.FIRST, second=_TempEnum2.SECOND),
    )


def test_json_to_domain_factory_with_no_enum_conversion_map_defaults_to_lower_case_name() -> (
    None
):
    class _TempEnum(Enum):
        FIRST = auto()

    @dataclass
    class _TempDomain:
        first: _TempEnum

    class _TempSchema(Schema):
        first = fields.Enum(_TempEnum)

    # We will use `_TempEnum.name.lower()` in the below factory when we convert
    # `first` into a JSON serialisable form by default as `enum_conversion_map` isn't provided
    class _NoEnumConverionFactory(JSONToDomainFactory[_TempDomain, _TempSchema]):
        first = _TempEnum.FIRST

    assert _NoEnumConverionFactory() == JSONToDomainFactoryResult(
        base={"first": _TempEnum.FIRST},
        json={"first": "first"},
        domain=_TempDomain(first=_TempEnum.FIRST),
    )


def test_raises_when_json_to_domain_factory_data_does_match_model() -> None:
    with pytest.raises(
        FactoryError,
        match=r"Failed to define '_InvalidFactory' : Failed to create Model object : ChildDomain.__init__\(\) got an unexpected keyword argument 'other_name'",
    ):
        # `other_name` is not valid property for the `ChildDomain` base model
        class _(Factory[ChildDomain]):
            other_name = "Billy"


def test_raises_when_json_to_domain_factory_domain_type_does_not_match_schema_domain_type() -> (
    None
):
    with pytest.raises(
        FactoryError,
        match="Failed to define '_InvalidFactory' : Schema domain type 'ParentDomain' doesn't match provided domain type 'ChildDomain'",
    ):
        # `ChildSchema` is not the same as `ParentSchema._domain_cls`
        class _(JSONToDomainFactory[ChildDomain, ParentSchema]):
            first_name = "Billy"
            second_name = "Jim"


def test_raises_when_json_to_domain_factory_data_fails_schema_validation() -> None:
    with pytest.raises(
        FactoryError,
        match=r"Failed to define '_InvalidFactory' : Schema failed to validate data : {'first_name': \['Missing data for required field.'\]}",
    ):
        # `first_name` is not defined on the factory, so schema validation will fail
        class _(JSONToDomainFactory[ChildDomain, ChildSchema]):
            second_name = "Jim"


def test_raises_when_json_to_domain_factory_data_does_not_match_domain() -> None:
    @dataclass
    class _TempDomain:
        first_name: str

    class _TempSchema(Schema):
        first_name = fields.String()
        second_name = fields.String()

    with pytest.raises(
        FactoryError,
        match=r"Failed to define '_InvalidFactory' : Failed to create Domain object : .* got an unexpected keyword argument 'second_name'",
    ):
        # `second_name` is not defined on `_TempDomain`, so domain object creation will fail
        class _(JSONToDomainFactory[_TempDomain, _TempSchema]):
            first_name = "Billy"
            second_name = "Jim"
