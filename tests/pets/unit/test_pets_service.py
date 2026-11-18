"""Lógica de PetsService con repositorio en memoria y sesión simulada."""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.pets.schemas import CreatePetDto, UpdatePetDto
from app.pets.service import PetsService

pytestmark = pytest.mark.unit


@pytest.fixture
def service(fake_pets_repository):
    service = PetsService(MagicMock())
    service.repository = fake_pets_repository
    service.students_service = MagicMock()
    service.students_service.get_or_404.return_value = SimpleNamespace(id=uuid4())
    return service


@pytest.fixture
def student_id(service):
    return service.students_service.get_or_404.return_value.id


def test_list_filters_by_student(service, student_id, make_pet_model):
    assert service.find_all_for_student(str(student_id)).items == []
    pet = make_pet_model(student_id)
    make_pet_model(uuid4())
    result = service.find_all_for_student(str(student_id))
    assert result.total == 1
    assert result.items[0].id == pet.id
    service.students_service.get_or_404.assert_called_with(str(student_id))


def test_create(service, student_id, pet_payload):
    result = service.create(str(student_id), CreatePetDto(**pet_payload()))
    assert result.studentId == student_id
    assert result.name == "Firulais"
    assert result.species == "perro"
    assert result.age == 3
    assert service.repository.find_by_id(result.id) is not None
    service.db.commit.assert_called_once()


@pytest.mark.parametrize("operation", ["create", "update"])
def test_duplicate_name(service, student_id, make_pet_model, pet_payload, operation):
    make_pet_model(student_id)
    other = make_pet_model(student_id, name="Michi")
    with pytest.raises(HTTPException) as error:
        if operation == "create":
            service.create(str(student_id), CreatePetDto(**pet_payload()))
        else:
            service.update(
                str(student_id), str(other.id), UpdatePetDto(name="Firulais")
            )
    assert error.value.status_code == 409
    assert "name" in error.value.detail["errors"]
    assert other.name == "Michi"
    assert len(service.repository.pets) == 2
    service.db.commit.assert_not_called()


def test_same_name_different_student(service, student_id, make_pet_model, pet_payload):
    make_pet_model(uuid4())
    result = service.create(str(student_id), CreatePetDto(**pet_payload()))
    assert result.studentId == student_id
    service.db.commit.assert_called_once()


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"name": "Firulais"},
        {"age": None},
        {"age": 0},
        {"name": "Michi", "species": "gato"},
    ],
)
def test_update(service, student_id, make_pet_model, changes):
    pet = make_pet_model(student_id)
    result = service.update(str(student_id), str(pet.id), UpdatePetDto(**changes))
    assert result.name == changes.get("name", "Firulais")
    assert result.species == changes.get("species", "perro")
    assert result.age == (0 if changes.get("age") == 0 else 3)
    service.db.commit.assert_called_once()


def test_delete(service, student_id, make_pet_model):
    pet = make_pet_model(student_id)
    result = service.delete(str(student_id), str(pet.id))
    assert result.id == pet.id
    assert service.repository.pets == []
    service.db.commit.assert_called_once()


@pytest.mark.parametrize("operation", ["update", "delete"])
@pytest.mark.parametrize("kind", ["missing", "invalid", "other_student"])
def test_pet_not_found(service, student_id, make_pet_model, operation, kind):
    pet = make_pet_model(uuid4())
    pet_id = {
        "missing": str(uuid4()),
        "invalid": "no-uuid",
        "other_student": str(pet.id),
    }[kind]
    args = [str(student_id), pet_id]
    if operation == "update":
        args.append(UpdatePetDto(name="Michi"))
    with pytest.raises(HTTPException) as error:
        getattr(service, operation)(*args)
    assert error.value.status_code == 404
    assert error.value.detail == "Mascota no encontrada"
    assert service.repository.pets == [pet]
    assert pet.name == "Firulais"
    service.db.commit.assert_not_called()


@pytest.mark.parametrize(
    "operation", ["find_all_for_student", "create", "update", "delete"]
)
def test_student_not_found(service, operation, pet_payload):
    service.students_service.get_or_404.side_effect = HTTPException(
        404, "Estudiante no encontrado"
    )
    args = [str(uuid4())]
    if operation == "create":
        args.append(CreatePetDto(**pet_payload()))
    elif operation in ("update", "delete"):
        args.append(str(uuid4()))
        if operation == "update":
            args.append(UpdatePetDto(name="Michi"))
    with pytest.raises(HTTPException) as error:
        getattr(service, operation)(*args)
    assert error.value.status_code == 404
    assert error.value.detail == "Estudiante no encontrado"
    assert service.repository.pets == []
    service.db.commit.assert_not_called()
