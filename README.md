# multi_factory

Define a single factory to generate the same data in multiple formats:

- Base (original data as defined on the factory)
- JSON (original data converted into a Python dict that is JSON serialisable)
- Domain (JSON data that is passed through a `marshmallow` schema that validates it and converts it into a domain object like a `@dataclass`)

# Installation

`multi_factory` can be installed using pip (requires Python >=3.10):

```bash
pip install multi-factory
```

