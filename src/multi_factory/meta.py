from __future__ import annotations


from types import NoneType
from typing import (
    Any,
    TypeGuard,
    get_args,
    get_origin,
)

from factory.base import FactoryOptions

from multi_factory.errors import (
    DomainCreationError,
    FactoryError,
    JSONSerialisationError,
    ModelCreationError,
    SchemaValidationError,
)
from multi_factory.types import EnumConversionMap, Schema


class BaseMeta:
    model: type[Any]
    exclude: tuple[str, ...] = ()
    abstract: bool = False


def get_generic_args(
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


def inject_meta_and_excludes(
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
        exclude += base_meta.exclude

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


def validate_factory(new_factory_cls: type[Any]) -> Any:
    """Validate that `new_factory_cls` can be instantiated without any errors.

    Raises:
        FactoryError: if `new_factory_cls` fails to be instantiated
    """
    try:
        return new_factory_cls.build()
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


def get_origin_cls(generic_or_regular_cls: type[Any]) -> type[Any]:
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


def has_domain_cls(domain_cls: type[Any] | type[None]) -> TypeGuard[type[Any]]:
    return not issubclass(domain_cls, NoneType)


def has_schema_cls(
    schema_cls: type[Schema] | type[None],
) -> TypeGuard[type[Schema]]:
    return not issubclass(schema_cls, NoneType)


def resolve_attribute(name: str, bases: tuple[type[Any]], default: Any = None) -> Any:
    """Find the first definition of an attribute according to MRO order."""
    for base in bases:
        if hasattr(base, name):
            return getattr(base, name)
    return default
