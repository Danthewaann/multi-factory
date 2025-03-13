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
