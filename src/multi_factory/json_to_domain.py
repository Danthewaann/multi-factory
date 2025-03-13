from __future__ import annotations

import datetime
import json
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from types import NoneType
from typing import (
    Any,
    Generic,
)
from uuid import UUID

from multi_factory.base import BaseFactory
from marshmallow import ValidationError

from multi_factory.errors import (
    DomainCreationError,
    JSONSerialisationError,
    SchemaValidationError,
)
from multi_factory.meta import (
    get_generic_args,
    get_origin_cls,
    has_domain_cls,
    has_schema_cls,
    inject_meta_and_excludes,
    resolve_attribute,
    validate_factory,
)
from multi_factory.types import DomainT, EnumConversionMap, SchemaT

from factory.base import FactoryMetaClass as _FactoryMetaClass
from multi_factory.errors import FactoryError
from multi_factory.types import Schema


class JSONToDomainFactoryMetaClass(_FactoryMetaClass):  # type: ignore[misc]
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
            return super().__new__(mcs, class_name, bases, attrs)  # type: ignore[no-any-return]

        model_cls = dict
        enum_conversion_map = enum_conversion_map or {}
        schema: Schema | None = None

        # Get the meta, schema and enum_conversion_map attributes from the parent factory
        # (if this new factory is a subclass of another factory class)
        base_meta = resolve_attribute(name="_meta", bases=bases)
        base_schema: Schema | None = resolve_attribute(name="_schema", bases=bases)
        base_enum_conversion_map: EnumConversionMap = resolve_attribute(
            name="_enum_conversion_map", bases=bases, default={}
        )

        # If the parent factory is abstract we must obtain `domain_cls` and `schema_cls` from the new factory class
        domain_cls: type[Any] | type[None] = NoneType
        if base_meta and base_meta.abstract:
            _, domain_cls, schema_cls = get_generic_args(attrs=attrs)
            domain_cls = get_origin_cls(domain_cls)

            # Make sure that `domain_cls` and `schema_cls` are provided
            if not has_domain_cls(domain_cls) or not has_schema_cls(schema_cls):
                raise FactoryError(
                    f"Failed to define '{class_name}' : Must provide generic domain and schema types"
                )

            # The `schema_cls` is valid, so create an instance of it
            schema = schema_cls()

        inject_meta_and_excludes(
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
        result = validate_factory(new_factory_cls)

        # Make sure that the `domain_cls` that `schema_cls` uses is the same as the provided `domain_cls` for this factory
        assert isinstance(result, JSONToDomainFactoryResult)
        if has_domain_cls(domain_cls) and not isinstance(result.domain, domain_cls):
            raise FactoryError(
                f"Failed to define '{class_name}' : Schema domain type '{result.domain.__class__.__name__}' doesn't match provided domain type '{domain_cls.__name__}'"
            )

        return new_factory_cls  # type: ignore[no-any-return]


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
            domain = cls._schema.load(deepcopy(raw_json))
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
