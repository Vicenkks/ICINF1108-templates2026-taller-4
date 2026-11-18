"""Datos y repositorio en memoria para probar mascotas sin PostgreSQL."""

from uuid import uuid4

import pytest

from app.pets.models import PetModel
from app.shared.datetimes import utc_now


class FakePetsRepository:
    def __init__(self):
        self.pets = []

    def find_all_by_student(self, student_id):
        return [pet for pet in self.pets if pet.studentId == student_id]

    def find_by_id(self, pet_id):
        return next((pet for pet in self.pets if pet.id == pet_id), None)

    def find_by_student_and_name(self, student_id, name):
        return next(
            (
                pet
                for pet in self.pets
                if pet.studentId == student_id and pet.name == name
            ),
            None,
        )

    def add(self, pet):
        # Simula los valores que SQLAlchemy asigna durante flush.
        pet.id = uuid4()
        pet.createdAt = pet.updatedAt = utc_now()
        self.pets.append(pet)
        return pet

    def delete(self, pet):
        self.pets.remove(pet)


@pytest.fixture
def fake_pets_repository():
    return FakePetsRepository()


@pytest.fixture
def pet_payload():
    def build(**overrides):
        return {"name": "Firulais", "species": "perro", "age": 3, **overrides}

    return build


@pytest.fixture
def make_pet_model(fake_pets_repository, pet_payload):
    def build(student_id, **overrides):
        return fake_pets_repository.add(
            PetModel(studentId=student_id, **pet_payload(**overrides))
        )

    return build


@pytest.fixture
def create_student(auth_client):
    def create():
        suffix = uuid4().hex[:8]
        response = auth_client.post(
            "/api/students",
            json={
                "name": "Ana Pérez",
                "username": f"ana_{suffix}",
                "email": f"ana_{suffix}@example.com",
                "age": 21,
            },
        )
        assert response.status_code == 201, response.text
        return response.json()["data"]

    return create


@pytest.fixture
def pets_url(create_student):
    return f"/api/students/{create_student()['id']}/pets"
