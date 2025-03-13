from __future__ import annotations

from types import NoneType
from typing import Any, Generic

from factory.base import BaseFactory as _BaseFactory

from multi_factory.errors import ModelCreationError
from multi_factory.meta import (
    get_generic_args,
    get_origin_cls,
    inject_meta_and_excludes,
    resolve_attribute,
    validate_factory,
)
from multi_factory.types import BaseT, DomainT, SchemaT
from factory.base import FactoryMetaClass as _FactoryMetaClass


class FactoryMetaClass(_FactoryMetaClass):  # type: ignore[misc]
    """Factory metaclass that uses `BaseT` for `Meta.model` and updates `Meta.exclude` for sub factory classes."""

    # This is here only for type hinting reasons when you create an instance of
    # a factory directly e.g. ShopFactory() -> Any
    def __call__(cls, **kwargs: Any) -> Any:  # noqa U100
        return super().__call__(**kwargs)

    def __new__(
        mcs,
        class_name: str,
        bases: tuple[type[Any]],
        attrs: dict[str, Any],
        exclude: str | tuple[str, ...] = (),
        abstract: bool = False,
    ) -> type[Any]:
        """Record attributes as a pattern for later instance construction.

        This is called when a new Factory subclass is defined; it will collect
        attribute declaration from the class definition.

        Args:
            class_name: the name of the class being created
            bases: the parents of the class being created
            attrs: the attributes as defined in the class definition
            exclude: attributes to exclude when creating instances of the model
            abstract: True if the class is abstract (shouldn't be created directly), defaults to False

        Returns:
            A new `Factory` class
        """
        # If the factory class is abstract just create and return it here
        if abstract:
            return super().__new__(mcs, class_name, bases, attrs)  # type: ignore[no-any-return]

        # Get the meta attribute from the parent factory
        # (if this new factory is a subclass of another factory class)
        base_meta = resolve_attribute(name="_meta", bases=bases)
        model_cls, *_ = get_generic_args(attrs=attrs)
        model_cls = get_origin_cls(model_cls)

        # If `base_meta` is found, we use it's `model` attribute for `model_cls`
        if base_meta and model_cls is NoneType:
            model_cls = base_meta.model

        inject_meta_and_excludes(
            attrs=attrs, model_cls=model_cls, exclude=exclude, base_meta=base_meta
        )

        # Create the new factory class
        new_factory_cls = super().__new__(mcs, class_name, bases, attrs)

        # Verify that the factory can create the defined model
        validate_factory(new_factory_cls)

        return new_factory_cls  # type: ignore[no-any-return]


class BaseFactory(_BaseFactory, Generic[BaseT, DomainT, SchemaT]):  # type: ignore[misc]
    @classmethod
    def build(cls, **kwargs: Any) -> BaseT:
        try:
            base: BaseT = super().build(**kwargs)
        except Exception as e:
            raise ModelCreationError(str(e)) from None

        return cls._process(base=base)

    @classmethod
    def create(cls, **kwargs: Any) -> BaseT:
        try:
            base: BaseT = super().create(**kwargs)
        except Exception as e:
            raise ModelCreationError(str(e)) from None

        return cls._process(base=base)

    @classmethod
    def build_batch(cls, size: int, **kwargs: Any) -> list[BaseT]:
        return super().build_batch(size, **kwargs)  # type: ignore[no-any-return]

    @classmethod
    def create_batch(cls, size: int, **kwargs: Any) -> list[BaseT]:
        return super().create_batch(size, **kwargs)  # type: ignore[no-any-return]

    @classmethod
    def _process(cls, base: BaseT) -> BaseT:
        return base


class Factory(
    BaseFactory[BaseT, None, None], metaclass=FactoryMetaClass, abstract=True
):
    """Factory class for generating a single base model.

    Args:
        exclude (str | tuple[str, ...]): attributes to exclude when creating instances of the model, defaults to `()`
    """
