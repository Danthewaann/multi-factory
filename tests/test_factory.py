from typing import Callable

import pytest
from multi_factory import errors
from multi_factory.base import Factory
from multi_factory.utils import lazy_attribute
from tests import common
from tests.common import ChildDomain, ParentDomain, inject_factory_method


class ChildFactory(Factory[ChildDomain]):
    first_name = "Billy"
    second_name = "Jim"


class ParentFactory(Factory[ParentDomain]):
    first_name = "Jim"
    second_name = "Jim"
    children = lazy_attribute(lambda: [ChildFactory.build()])


@inject_factory_method(ParentFactory)
def test_factory(
    factory_method: Callable[..., common.ParentDomain],
    parent_domain: common.ParentDomain,
) -> None:
    model = factory_method()
    assert model == parent_domain


@inject_factory_method(ParentFactory, batch=True)
def test_factory_batch(
    factory_method: Callable[..., list[common.ParentDomain]],
    parent_domain: common.ParentDomain,
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


def test_raises_when_factory_data_does_match_model() -> None:
    with pytest.raises(
        errors.FactoryError,
        match=r"Failed to define '_InvalidFactory' : Failed to create Model object : ChildDomain.__init__\(\) got an unexpected keyword argument 'other_name'",
    ):
        # `other_name` is not valid property for the `ChildDomain` base model
        class _InvalidFactory(Factory[common.ChildDomain]):
            other_name = "Billy"
