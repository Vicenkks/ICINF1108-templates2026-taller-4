"""Validación de DTOs de mascotas, sin HTTP ni base de datos."""

import pytest
from pydantic import ValidationError

from app.pets.schemas import CreatePetDto, UpdatePetDto

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("dto_class", [CreatePetDto, UpdatePetDto])
@pytest.mark.parametrize("field", ["name", "species"])
@pytest.mark.parametrize("value", ["", "a" * 51, "<b>Michi</b>", 123])
def test_invalid_text(dto_class, field, value, pet_payload):
    with pytest.raises(ValidationError) as error:
        dto_class(**pet_payload(**{field: value}))
    assert error.value.errors()[0]["loc"] == (field,)


@pytest.mark.parametrize("dto_class", [CreatePetDto, UpdatePetDto])
@pytest.mark.parametrize("age", [-1, 101, 1.5, True, "3"])
def test_invalid_age(dto_class, age, pet_payload):
    with pytest.raises(ValidationError) as error:
        dto_class(**pet_payload(age=age))
    assert "La edad" in str(error.value)


@pytest.mark.parametrize("dto_class", [CreatePetDto, UpdatePetDto])
@pytest.mark.parametrize("age", [0, 100, None])
@pytest.mark.parametrize("length", [1, 50])
def test_valid_boundaries(dto_class, age, length):
    dto = dto_class(name="a" * length, species="b" * length, age=age)
    assert dto.age == age
    assert len(dto.name) == length
    assert len(dto.species) == length


def test_create_age_optional():
    assert CreatePetDto(name="Michi", species="gato").age is None


@pytest.mark.parametrize("field", ["name", "species"])
@pytest.mark.parametrize("missing", [True, False])
def test_create_required_text(field, missing, pet_payload):
    data = pet_payload(**{field: None})
    if missing:
        del data[field]
    with pytest.raises(ValidationError) as error:
        CreatePetDto(**data)
    assert error.value.errors()[0]["loc"] == (field,)


@pytest.mark.parametrize("dto_class", [CreatePetDto, UpdatePetDto])
def test_extra_fields_forbidden(dto_class, pet_payload):
    with pytest.raises(ValidationError) as error:
        dto_class(**pet_payload(extra="no permitido"))
    assert error.value.errors()[0]["type"] == "extra_forbidden"


def test_update_optional_fields():
    assert UpdatePetDto().model_dump() == dict.fromkeys(["name", "species", "age"])
    assert (
        UpdatePetDto(name=None, species=None, age=None).model_dump(exclude_none=True)
        == {}
    )
    assert UpdatePetDto(age=0).model_dump(exclude_unset=True) == {"age": 0}
