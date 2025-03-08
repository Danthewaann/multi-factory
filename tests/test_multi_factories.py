from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable

import pytest

from tests import common

from marshmallow import fields
from multi_factories import (
    Factory,
    FactoryError,
    JSONToDomainFactory,
    JSONToDomainFactoryResult,
)
from tests.common import inject_factory_method


@pytest.fixture
def child_dict() -> dict[str, Any]:
    return {"first_name": "Billy", "second_name": "Jim"}


@pytest.fixture
def parent_dict(child_dict: dict[str, Any]) -> dict[str, Any]:
    return {"first_name": "Jim", "second_name": "Jim", "children": [child_dict]}


@pytest.fixture
def child_domain() -> common.ChildDomain:
    return common.ChildDomain(first_name="Billy", second_name="Jim")


@pytest.fixture
def parent_domain(child_domain: common.ChildDomain) -> common.ParentDomain:
    return common.ParentDomain(
        first_name="Jim", second_name="Jim", children=[child_domain]
    )


@pytest.fixture
def json_to_domain_factory_result(
    parent_dict: dict[str, Any], parent_domain: common.ParentDomain
) -> JSONToDomainFactoryResult[common.ParentDomain]:
    return JSONToDomainFactoryResult(
        base=parent_dict, json=parent_dict, domain=parent_domain
    )


@inject_factory_method(common.ParentJSONToDomainFactory)
def test_json_to_domain_factory(
    factory_method: Callable,
    json_to_domain_factory_result: JSONToDomainFactoryResult[common.ParentDomain],
) -> None:
    model = factory_method()
    assert model == json_to_domain_factory_result


@inject_factory_method(common.ParentFactory)
def test_factory(factory_method: Callable, parent_domain: common.ParentDomain) -> None:
    model = factory_method()
    assert model == parent_domain


@inject_factory_method(common.ParentJSONToDomainFactory, batch=True)
def test_json_to_domain_factory_batch(
    factory_method: Callable,
    json_to_domain_factory_result: JSONToDomainFactoryResult[common.ParentDomain],
) -> None:
    models = factory_method(size=1)
    assert models == [json_to_domain_factory_result]


@inject_factory_method(common.ParentFactory, batch=True)
def test_factory_batch(
    factory_method: Callable, parent_domain: common.ParentDomain
) -> None:
    models = factory_method(size=1)
    assert models == [parent_domain]


def test_factory_excludes(child_domain: common.ChildDomain) -> None:
    # `other_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesFactory(Factory[common.ChildDomain], exclude="other_field"):
        first_name = "Billy"
        second_name = "Jim"
        other_field = "Bob"

    assert _ExcludesFactory() == child_domain


def test_factory_excludes_merges_with_superclass(
    child_domain: common.ChildDomain,
) -> None:
    # `other_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesFactory(Factory[common.ChildDomain], exclude="another_field"):
        first_name = "Billy"
        second_name = "Jim"
        another_field = "Bob"

    # `other_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesDerivedFactory(_ExcludesFactory, exclude="other_field"):
        other_field = "Bob"

    assert _ExcludesDerivedFactory() == child_domain


def test_factory_excludes_in_meta_inner_class(child_domain: common.ChildDomain) -> None:
    # `other_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesFactory(Factory[common.ChildDomain]):
        class Meta:
            exclude = ("other_field",)

        first_name = "Billy"
        second_name = "Jim"
        other_field = "Bob"

    assert _ExcludesFactory() == child_domain


def test_factory_excludes_in_meta_inner_class_merges_with_superclass(
    child_domain: common.ChildDomain,
) -> None:
    # `another_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesFactory(Factory[common.ChildDomain]):
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
    child_dict: dict[str, Any], child_domain: common.ChildDomain
) -> None:
    # `other_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesFactory(
        JSONToDomainFactory[common.ChildDomain, common.ChildSchema],
        exclude="other_field",
    ):
        first_name = "Billy"
        second_name = "Jim"
        other_field = "Bob"

    assert _ExcludesFactory() == JSONToDomainFactoryResult(
        base=child_dict, json=child_dict, domain=child_domain
    )


def test_json_to_domain_factory_excludes_merges_with_superclass(
    child_dict: dict[str, Any], child_domain: common.ChildDomain
) -> None:
    # `another_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesFactory(
        JSONToDomainFactory[common.ChildDomain, common.ChildSchema],
        exclude="another_field",
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
    child_dict: dict[str, Any], child_domain: common.ChildDomain
) -> None:
    # `other_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesFactory(JSONToDomainFactory[common.ChildDomain, common.ChildSchema]):
        class Meta:
            exclude = ("other_field",)

        first_name = "Billy"
        second_name = "Jim"
        other_field = "Bob"

    assert _ExcludesFactory() == JSONToDomainFactoryResult(
        base=child_dict, json=child_dict, domain=child_domain
    )


def test_json_to_domain_factory_excludes_in_meta_inner_class_merges_with_superclass(
    child_dict: dict[str, Any], child_domain: common.ChildDomain
) -> None:
    # `another_field` shouldn't get used when creating the model or domain object for this factory
    class _ExcludesFactory(JSONToDomainFactory[common.ChildDomain, common.ChildSchema]):
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

    class _TempSchema(common.BaseSchema):
        _domain_cls = _TempDomain
        first = fields.Enum(_TempEnum)

    # We will use `_TempEnum.name.upper()` in the below factory when we convert
    # `first` into a JSON serialisable form
    class _EnumConversionFactory(
        JSONToDomainFactory[_TempDomain, _TempSchema],
        enum_conversion_map={_TempEnum: lambda enum: enum.name.upper()},
    ):
        first = _TempEnum.FIRST

    assert _EnumConversionFactory() == JSONToDomainFactoryResult(
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

    class _TempSchema(common.BaseSchema):
        _domain_cls = _TempDomain
        first = fields.Enum(_TempEnum)
        second = fields.Enum(_TempEnum2)

    # We will use `_TempEnum.name.upper()` in the below factory when we convert
    # `first` into a JSON serialisable form
    class _EnumConversionFactory(
        JSONToDomainFactory[_TempDomain, _TempSchema],
        enum_conversion_map={_TempEnum: lambda enum: enum.name.upper()},
    ):
        first = _TempEnum.FIRST
        second = _TempEnum2.SECOND

    class _EnumConverionDerivedFactory(
        _EnumConversionFactory,
        enum_conversion_map={_TempEnum2: lambda enum: enum.name.upper()},
    ):
        second = _TempEnum2.SECOND

    assert _EnumConverionDerivedFactory() == JSONToDomainFactoryResult(
        base={"first": _TempEnum.FIRST, "second": _TempEnum2.SECOND},
        json={"first": "FIRST", "second": "SECOND"},
        domain=_TempDomain(first=_TempEnum.FIRST, second=_TempEnum2.SECOND),
    )


def test_json_to_domain_factory_with_no_enum_conversion_map_defaults_to_name() -> None:
    class _TempEnum(Enum):
        FIRST = auto()

    @dataclass
    class _TempDomain:
        first: _TempEnum

    class _TempSchema(common.BaseSchema):
        _domain_cls = _TempDomain
        first = fields.Enum(_TempEnum)

    # We will use `_TempEnum.name` in the below factory when we convert
    # `first` into a JSON serialisable form by default as `enum_conversion_map` isn't provided
    class _NoEnumConverionFactory(JSONToDomainFactory[_TempDomain, _TempSchema]):
        first = _TempEnum.FIRST

    assert _NoEnumConverionFactory() == JSONToDomainFactoryResult(
        base={"first": _TempEnum.FIRST},
        json={"first": "FIRST"},
        domain=_TempDomain(first=_TempEnum.FIRST),
    )


def test_raises_when_json_to_domain_factory_data_does_match_model() -> None:
    with pytest.raises(
        FactoryError,
        match=r"Failed to define '_InvalidFactory' : Failed to create Model object : ChildDomain.__init__\(\) got an unexpected keyword argument 'other_name'",
    ):
        # `other_name` is not valid property for the `ChildDomain` base model
        class _InvalidFactory(Factory[common.ChildDomain]):
            other_name = "Billy"


def test_raises_when_json_to_domain_factory_domain_type_does_not_match_schema_domain_type() -> (
    None
):
    with pytest.raises(
        FactoryError,
        match="Failed to define '_InvalidFactory' : Schema domain type 'ParentDomain' doesn't match provided domain type 'ChildDomain'",
    ):
        # `ChildSchema` is not the same as `ParentSchema._domain_cls`
        class _InvalidFactory(
            JSONToDomainFactory[common.ChildDomain, common.ParentSchema]
        ):
            first_name = "Billy"
            second_name = "Jim"


def test_raises_when_json_to_domain_factory_data_fails_schema_validation() -> None:
    with pytest.raises(
        FactoryError,
        match=r"Failed to define '_InvalidFactory' : Schema failed to validate data : {'first_name': \['Missing data for required field.'\]}",
    ):
        # `first_name` is not defined on the factory, so schema validation will fail
        class _InvalidFactory(
            JSONToDomainFactory[common.ChildDomain, common.ChildSchema]
        ):
            second_name = "Jim"


def test_raises_when_json_to_domain_factory_data_does_not_match_domain() -> None:
    @dataclass
    class _TempDomain:
        first_name: str

    class _TempSchema(common.BaseSchema):
        _domain_cls = _TempDomain
        first_name = fields.String()
        second_name = fields.String()

    with pytest.raises(
        FactoryError,
        match=r"Failed to define '_InvalidFactory' : Failed to create Domain object : .* got an unexpected keyword argument 'second_name'",
    ):
        # `second_name` is not defined on `_TempDomain`, so domain object creation will fail
        class _InvalidFactory(JSONToDomainFactory[_TempDomain, _TempSchema]):
            first_name = "Billy"
            second_name = "Jim"
