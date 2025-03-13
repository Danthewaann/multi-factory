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

# Quick start

Imagine you have the following code to represent a `User` in your application:

```python
from typing import Any
from enum import Enum
from uuid import UUID
from datetime import datetime
from dataclasses import dataclass
from marshmallow import Schema, fields, post_load


class Gender(Enum):
    MALE = 1
    FEMALE = 2
    OTHER = 3


class UserSchema(Schema):
    id = fields.UUID()
    first_name = fields.String()
    last_name = fields.String()
    age = fields.Integer()
    birthday = fields.DateTime()
    gender = fields.Enum(Gender)

    @post_load
    def to_domain(self, incoming_data: dict[str, Any], **kwargs: Any) -> User:
        return User(**incoming_data)


@dataclass
class User:
    id: UUID
    first_name: str
    last_name: str
    age: int
    birthday: datetime
    gender: Gender
```

The above code will be used in a `POST /users` HTTP API endpoint, where the request body will contain a `JSON` representation of the `User` class that will need
to be validated and de-serialized by the `UserSchema` class. The `UserSchema` class will also pass the validated data into the `User` class so it is easier to
use and pass around your application.

To be able to test this `POST /users` endpoint, you will need to define factories to generate data for this `User` class in multiple formats for use in tests.

You write the following code to define multiple independent factories to achieve this:

```python
import factory
from uuid import uuid4


class UserDictFactory(factory.Factory):
    class Meta:
        model = dict

    id = uuid4()
    first_name = "Bob"
    last_name = "Dylan"
    age = 21
    birthday = datetime(year=2000, month=1, day=1, hour=0)
    gender = Gender.MALE


class UserJSONFactory(factory.Factory):
    class Meta:
        model = dict

    id = str(uuid4())
    first_name = "Bob"
    last_name = "Dylan"
    age = 21
    birthday = datetime(year=2000, month=1, day=1, hour=0).isoformat()
    gender = Gender.MALE.name


class UserDomainFactory(factory.Factory):
    class Meta:
        model = User

    id = uuid4()
    first_name = "Bob"
    last_name = "Dylan"
    age = 21
    birthday = datetime(year=2000, month=1, day=1, hour=0)
    gender = Gender.MALE
```

Having to write 3 factories here adds more work that what should be necessary.
It also increases the risk of these 3 factories getting out of sync if a change is made to one of them and not the other 2.

With `multi-factory`, we can do the following instead:

```python
from multi_factory import JSONToDomainFactory


class UserFactory(JSONToDomainFactory[User, UserSchema]):
    id = uuid4()
    first_name = "Bob"
    last_name = "Dylan"
    age = 21
    birthday = datetime(year=2000, month=1, day=1, hour=0)
    gender = Gender.MALE
```

This `UserFactory` combines the 3 factories above into a single factory. This means you only need to define the test data once, which requires less maintenance
that having the same data defined in multiple factories.

When you invoke this `UserFactory` you will have access to the 3 different formats for the same data:

```python
>>> result = UserFactory()
>>> result
JSONToDomainFactoryResult(
    base={
        'id': UUID('96a43fc4-069a-4882-a388-24033299496f'), 
        'first_name': 'Bob', 
        'last_name': 'Dylan', 
        'age': 21, 
        'birthday': datetime.datetime(2000, 1, 1, 0, 0), 
        'gender': <Gender.MALE: 1>
    }, 
    json={
        'id': '96a43fc4-069a-4882-a388-24033299496f', 
        'first_name': 'Bob', 
        'last_name': 'Dylan', 
        'age': 21, 
        'birthday': '2000-01-01T00:00:00', 
        'gender': 'MALE'
    }, 
    domain=User(
        id=UUID('96a43fc4-069a-4882-a388-24033299496f'), 
        first_name='Bob', 
        last_name='Dylan', 
        age=21, 
        birthday=datetime.datetime(2000, 1, 1, 0, 0), 
        gender=<Gender.MALE: 1>
    )
)
```
