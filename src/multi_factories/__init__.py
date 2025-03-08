from __future__ import annotations

import datetime
import json
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from types import NoneType
from typing import (
    Any,
    Callable,
    Generic,
    Protocol,
    TypeGuard,
    TypeVar,
    get_args,
    get_origin,
)
from uuid import UUID

import factory
from factory.base import (
    BaseFactory as _BaseFactory,
    FactoryMetaClass as _FactoryMetaClass,
    FactoryOptions,
)
from marshmallow import ValidationError


class Schema(Protocol):
    _domain_cls: type


BaseT = TypeVar("BaseT")
DomainT = TypeVar("DomainT", bound="Any | None")
SchemaT = TypeVar("SchemaT", bound="Schema | None")

EnumConversionMap = dict[type[Enum], Callable[[Enum], Any]]


@dataclass
class JSONToDomainFactoryResult(Generic[DomainT]):
    """Factory result object that contains 3 attributes.

    - base   (the bare `dict` object that is created using the declared fields on the factory class as is)
    - json   (the JSON serialisable version of the `base` attribute)
    - domain (the Domain object that is created by passing the `json` attribute into a Marshmallow schema
              to validate and unserialise into an instance of `DomainT`)
    """

    base: dict[str, Any]
    json: dict[str, Any]
    domain: DomainT


class BaseMeta:
    model: type[Any]
    exclude: tuple[str, ...] = ()
    abstract: bool = False


class FactoryMetaClass(_FactoryMetaClass):
    """Factory metaclass that uses `BaseT` for `Meta.model` and updates `Meta.exclude` for sub factory classes."""

    # This is here only for type hinting reasons when you create an instance of
    # a factory directly e.g. ShopFactory() -> Any
    def __call__(cls, **kwargs: Any) -> Any:  # noqa U100
        return super().__call__(**kwargs)  # type: ignore

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
            return super().__new__(mcs, class_name, bases, attrs)

        # Get the meta attribute from the parent factory
        # (if this new factory is a subclass of another factory class)
        base_meta = _resolve_attribute(name="_meta", bases=bases)
        model_cls, *_ = _get_generic_args(attrs=attrs)
        model_cls = _get_origin_cls(model_cls)

        # If `base_meta` is found, we use it's `model` attribute for `model_cls`
        if base_meta and model_cls is NoneType:
            model_cls = base_meta.model

        _inject_meta_and_excludes(
            attrs=attrs, model_cls=model_cls, exclude=exclude, base_meta=base_meta
        )

        # Create the new factory class
        new_factory_cls = super().__new__(mcs, class_name, bases, attrs)

        # Verify that the factory can create the defined model
        _validate_factory(new_factory_cls)

        return new_factory_cls


class JSONToDomainFactoryMetaClass(_FactoryMetaClass):
    """JSONToDomainFactory metaclass that uses `dict` for `Meta.model` and updates `Meta.exclude` for sub factory classes."""

    # This is here only for type hinting reasons when you create an instance of
    # a factory directly e.g. ShopFactory() -> FactoryResult[Any]
    def __call__(cls, **kwargs: Any) -> JSONToDomainFactoryResult[Any]:  # noqa U100
        return super().__call__(**kwargs)  # type: ignore

    def __new__(
        mcs,
        class_name: str,
        bases: tuple[type[Any]],
        attrs: dict[str, Any],
        exclude: str | tuple[str, ...] = (),
        enum_conversion_map: EnumConversionMap | None = None,
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
            enum_conversion_map: enum type to callable map that handles how to convert enum values into a JSON serialisable form
            abstract: True if the class is abstract (shouldn't be created directly), defaults to False

        Returns:
            A new `JSONToDomainFactory` class
        """
        # If the factory class is abstract just create and return it here
        if abstract:
            return super().__new__(mcs, class_name, bases, attrs)

        model_cls = dict
        enum_conversion_map = enum_conversion_map or {}
        schema: Schema | None = None

        # Get the meta, schema and enum_conversion_map attributes from the parent factory
        # (if this new factory is a subclass of another factory class)
        base_meta = _resolve_attribute(name="_meta", bases=bases)
        base_schema: Schema | None = _resolve_attribute(name="_schema", bases=bases)
        base_enum_conversion_map: EnumConversionMap = _resolve_attribute(
            name="_enum_conversion_map", bases=bases, default={}
        )

        # If the parent factory is abstract we must obtain `domain_cls` and `schema_cls` from the new factory class
        if base_meta and base_meta.abstract:
            _, domain_cls, schema_cls = _get_generic_args(attrs=attrs)
            domain_cls = _get_origin_cls(domain_cls)

            # Make sure that `domain_cls` and `schema_cls` are provided
            if not _has_domain_cls(domain_cls) or not _has_schema_cls(schema_cls):
                raise FactoryError(
                    f"Failed to define '{class_name}' : Must provide generic domain and schema types"
                )

            # Make sure that the `domain_cls` that `schema_cls` uses is the same as the provided `domain_cls` for this factory
            if schema_cls._domain_cls is not domain_cls:
                raise FactoryError(
                    f"Failed to define '{class_name}' : Schema domain type '{schema_cls._domain_cls.__name__}' doesn't match provided domain type '{domain_cls.__name__}'"
                )

            # The `schema_cls` is valid, so create an instance of it
            schema = schema_cls()

        _inject_meta_and_excludes(
            attrs=attrs,
            model_cls=model_cls,
            schema=schema,
            exclude=exclude,
            enum_conversion_map=enum_conversion_map,
            base_meta=base_meta,
            base_schema=base_schema,
            base_enum_conversion_map=base_enum_conversion_map,
        )

        # Create the new factory class
        new_factory_cls = super().__new__(mcs, class_name, bases, attrs)

        # Verify that the factory can create the defined model, json and domain forms
        _validate_factory(new_factory_cls)

        return new_factory_cls


class BaseFactory(_BaseFactory, Generic[BaseT, DomainT, SchemaT]):
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
        return super().build_batch(size, **kwargs)

    @classmethod
    def create_batch(cls, size: int, **kwargs: Any) -> list[BaseT]:
        return super().create_batch(size, **kwargs)

    @classmethod
    def _process(cls, base: BaseT) -> BaseT:
        return base


class JSONToDomainFactory(
    BaseFactory[JSONToDomainFactoryResult[DomainT], DomainT, SchemaT],
    metaclass=JSONToDomainFactoryMetaClass,
    abstract=True,
):
    """Factory class for generating a dict base model that gets converted into JSON serialisable dict and domain object forms.

    Args:
        exclude (str | tuple[str, ...]): attributes to exclude when creating instances of the model, defaults to `()`
        enum_conversion_map (EnumConversionMap | None): enum type to callable map that handles how to convert enum
                                                        values into a JSON serialisable form, defaults to `None`
    """

    _schema: SchemaT
    _enum_conversion_map: EnumConversionMap

    @classmethod
    def _process(cls, base: Any) -> JSONToDomainFactoryResult[DomainT]:
        try:
            raw_json = json.loads(json.dumps(base, default=cls._json_serialise))
        except Exception as e:
            raise JSONSerialisationError(str(e)) from None

        try:
            # We create a deepcopy of `raw_json` in case if the schema mutates the `raw_json` dict
            domain = cls._schema.load(deepcopy(raw_json))  # type: ignore
        except ValidationError as e:
            raise SchemaValidationError(str(e)) from None
        except Exception as e:
            raise DomainCreationError(str(e)) from None

        return JSONToDomainFactoryResult(base=base, json=raw_json, domain=domain)

    @classmethod
    def _json_serialise(cls, value: Any) -> Any:
        """Convert the provided `value` into a JSON serialisable form.

        Raises:
            TypeError: if we fail to convert `value`
        """
        if isinstance(value, (datetime.date, datetime.datetime)):
            return value.isoformat()
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, Enum):
            enum_type = type(value)

            # if `value` is in the enum conversion map,
            # use it's mapped callable to convert it into some JSON serialisable form
            if enum_type in cls._enum_conversion_map:
                return cls._enum_conversion_map[enum_type](value)

            # Just use the name for `value` by default if no conversion mapping
            # was provided for `value`
            return value.name

        raise TypeError(f"Failed to JSON encode value : {value}")


class Factory(
    BaseFactory[BaseT, None, None], metaclass=FactoryMetaClass, abstract=True
):
    """Factory class for generating a single base model.

    Args:
        exclude (str | tuple[str, ...]): attributes to exclude when creating instances of the model, defaults to `()`
    """


class SQLAlchemyModelFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        sqlalchemy_session_persistence = None

    @classmethod
    def _create(cls, model_class: Any, *args: Any, **kwargs: Any):  # type: ignore[no-untyped-def]
        """Create an instance of the model, and save it to the database."""
        session = cls._meta.sqlalchemy_session  # type: ignore[attr-defined]

        if session is None:
            raise RuntimeError("No session provided.")

        if cls._meta.sqlalchemy_get_or_create:  # type: ignore[attr-defined]
            return cls._get_or_create(model_class, session, args, kwargs)  # type: ignore[attr-defined]

        # overrides the default behaviour which calls `cls._save(model_class, session, args, kwargs)`.
        # `_save()` adds the model instance to a session and then selectively devices to persist or not based on `sqlalchemy_session_persistence`
        # however adding it to the session causes conflicts when running multiple tests using the same fixture.
        # see: https://github.com/FactoryBoy/factory_boy/blob/37f962720814dff42d7a6a848ccfd200fc7f5ae2/factory/alchemy.py#L101-L111
        return model_class(*args, **kwargs)


class SQLAlchemyModelFactoryV2(
    BaseFactory[BaseT, None, None],
    SQLAlchemyModelFactory,
    metaclass=FactoryMetaClass,
    abstract=True,
):
    pass


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


def sub_factory(sub_factory: type[BaseFactory], **kwargs: Any) -> Any:
    """Convenience function that wraps `factory.SubFactory`."""
    return factory.SubFactory(sub_factory, **kwargs)


class FactoryError(Exception):
    """Raised when a factory fails to be defined or called."""


class ModelCreationError(FactoryError):
    """Raised when a factory fails to create the model object."""


class DomainCreationError(FactoryError):
    """Raised when a factory fails to create the domain object."""


class JSONSerialisationError(FactoryError):
    """Raised when a factory fails to JSON serialise the factory model data."""


class SchemaValidationError(FactoryError):
    """Raised when a factory schema fails to validate the JSON serialised factory model data."""


def _get_generic_args(
    attrs: dict[str, Any]
) -> tuple[type[Any], type[Any] | type[None], type[Schema] | type[None]]:
    """Get and introspect the generic type args from `attrs` for a new factory class."""
    model_cls, domain_cls, schema_cls = type(None), type(None), type(None)

    base, *_ = attrs.get("__orig_bases__", (None,))
    base_args = get_args(base)
    num_args = len(base_args)

    if num_args == 1:
        (model_cls,) = base_args
    elif num_args == 2:
        domain_cls, schema_cls = base_args

    return model_cls, domain_cls, schema_cls


def _inject_meta_and_excludes(
    attrs: dict[str, Any],
    model_cls: type[Any],
    schema: Schema | None = None,
    exclude: str | tuple[str, ...] = (),
    enum_conversion_map: EnumConversionMap | None = None,
    base_meta: FactoryOptions | None = None,
    base_schema: Schema | None = None,
    base_enum_conversion_map: EnumConversionMap | None = None,
) -> None:
    """Injects or updates the `Meta` inner class to include `model`, `exclude` and optionally `_schema`."""
    # Get or create the `Meta` inner class of the factory class
    meta = attrs.get("Meta")
    if not meta:
        meta = BaseMeta()

    # Merge `meta.exclude` with the provided `exclude` and `base_meta.exclude`
    if isinstance(exclude, str):
        exclude = (exclude,)
    if hasattr(meta, "exclude"):
        exclude += meta.exclude
    if base_meta and hasattr(base_meta, "exclude"):
        exclude += base_meta.exclude  # type: ignore

    # Bind an instance of `schema` or `base_schema` to the new factory class if provided for later use
    if schema:
        attrs["_schema"] = schema
    elif base_schema:
        attrs["_schema"] = base_schema

    # Bind the enum conversion map to the factory to use for converting enums into a JSON
    # serialisable form if it is provided
    if base_enum_conversion_map is not None and enum_conversion_map is not None:
        enum_conversion_map |= base_enum_conversion_map
    if enum_conversion_map is not None:
        attrs["_enum_conversion_map"] = enum_conversion_map

    # Bind `model_cls` and `exclude` to the inner meta class before the factory class is created
    meta.model = model_cls
    meta.exclude = exclude
    attrs["Meta"] = meta


def _validate_factory(new_factory_cls: type[Any]) -> None:
    """Validate that `new_factory_cls` can be instantiated without any errors.

    Raises:
        FactoryError: if `new_factory_cls` fails to be instantiated
    """
    try:
        new_factory_cls.build()  # type: ignore
    except Exception as e:
        message = f"Failed to define '{new_factory_cls.__name__}' : "
        if isinstance(e, ModelCreationError):
            message += "Failed to create Model object : "
        elif isinstance(e, DomainCreationError):
            message += "Failed to create Domain object : "
        elif isinstance(e, JSONSerialisationError):
            message += "Schema failed to serialise to JSON : "
        elif isinstance(e, SchemaValidationError):
            message += "Schema failed to validate data : "
        else:
            message += "Unknown error occurred : "

        raise FactoryError(f"{message}{str(e)}")


def _get_origin_cls(generic_or_regular_cls: type[Any]) -> type[Any]:
    """Get the origin class from `generic_or_regular_cls`.

    For example:

        - generic_or_regular_cls = dict[str, Any] (generic type)
        - origin_cls             = dict           (dict builtin type)

    Or:
        - generic_or_regular_cls = Shop (class type)
        - origin_cls             = None (origin is `None` as `Shop` isn't a generic type)
    """
    origin_cls = get_origin(generic_or_regular_cls)
    return origin_cls if origin_cls else generic_or_regular_cls


def _has_domain_cls(domain_cls: type[Any] | type[None]) -> TypeGuard[type[Any]]:
    return not issubclass(domain_cls, NoneType)


def _has_schema_cls(
    schema_cls: type[Schema] | type[None],
) -> TypeGuard[type[Schema]]:
    return not issubclass(schema_cls, NoneType)


def _resolve_attribute(name: str, bases: tuple[type[Any]], default: Any = None) -> Any:
    """Find the first definition of an attribute according to MRO order."""
    for base in bases:
        if hasattr(base, name):
            return getattr(base, name)
    return default
