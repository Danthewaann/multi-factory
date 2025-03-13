from typing import Any
import pytest

from tests import common


@pytest.fixture
def child_dict() -> dict[str, Any]:
    return {"first_name": "Billy", "second_name": "Jim"}


@pytest.fixture
def parent_dict(child_dict: dict[str, Any]) -> dict[str, Any]:
    return {"first_name": "Jim", "second_name": "Jim", "children": [child_dict]}


@pytest.fixture
def parent_with_single_child_dict(child_dict: dict[str, Any]) -> dict[str, Any]:
    return {"first_name": "Jim", "second_name": "Jim", "child": child_dict}


@pytest.fixture
def child_domain() -> common.ChildDomain:
    return common.ChildDomain(first_name="Billy", second_name="Jim")


@pytest.fixture
def parent_domain(child_domain: common.ChildDomain) -> common.ParentDomain:
    return common.ParentDomain(
        first_name="Jim", second_name="Jim", children=[child_domain]
    )


@pytest.fixture
def parent_with_single_child_domain(
    child_domain: common.ChildDomain,
) -> common.ParentWithSingleChildDomain:
    return common.ParentWithSingleChildDomain(
        first_name="Jim", second_name="Jim", child=child_domain
    )
