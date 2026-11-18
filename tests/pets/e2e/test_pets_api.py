"""Recorridos HTTP de mascotas con autenticación y PostgreSQL real."""

from uuid import UUID, uuid4

import pytest

from app.pets.models import PetModel

pytestmark = pytest.mark.e2e


def create_pet(client, url, payload):
    response = client.post(url, json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


@pytest.mark.parametrize("method", ["GET", "POST", "PATCH", "DELETE"])
def test_requires_session(client, method, pet_payload):
    url = f"/api/students/{uuid4()}/pets"
    if method in ("PATCH", "DELETE"):
        url += f"/{uuid4()}"
    response = client.request(method, url, json=pet_payload())
    assert response.status_code == 401
    assert response.json()["success"] is False
    assert response.json()["data"] is None
    assert response.json()["error"]


def test_empty_list(auth_client, pets_url):
    response = auth_client.get(pets_url)
    assert response.status_code == 200
    assert response.json()["data"] == {"total": 0, "items": []}


def test_create(auth_client, pets_url, pet_payload, db_session):
    response = auth_client.post(pets_url, json=pet_payload())
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["code"] == 201
    assert body["message"] == "Recurso creado"
    data = body["data"]
    assert data["name"] == "Firulais"
    assert data["species"] == "perro"
    assert data["age"] == 3
    assert data["studentId"] == pets_url.split("/")[3]
    assert data["createdAt"].endswith("Z")
    assert data["updatedAt"].endswith("Z")
    stored = db_session.get(PetModel, UUID(data["id"]))
    assert stored.name == data["name"]
    assert str(stored.studentId) == data["studentId"]


def test_create_without_age(auth_client, pets_url):
    pet = create_pet(auth_client, pets_url, {"name": "Michi", "species": "gato"})
    assert pet["age"] is None


def test_list_is_scoped_to_student(auth_client, pets_url, create_student, pet_payload):
    first = create_pet(auth_client, pets_url, pet_payload())
    second = create_pet(auth_client, pets_url, pet_payload(name="Michi"))
    other_url = f"/api/students/{create_student()['id']}/pets"
    create_pet(auth_client, other_url, pet_payload())
    response = auth_client.get(pets_url)
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 2
    assert {pet["id"] for pet in data["items"]} == {first["id"], second["id"]}


@pytest.mark.parametrize(
    "changes",
    [
        {"name": "Michi", "species": "gato", "age": 0},
        {},
        {"name": "Firulais"},
        {"age": None},
    ],
)
def test_update(auth_client, pets_url, pet_payload, changes):
    pet = create_pet(auth_client, pets_url, pet_payload())
    response = auth_client.patch(f"{pets_url}/{pet['id']}", json=changes)
    assert response.status_code == 200
    assert response.json()["message"] == "Recurso actualizado"
    expected = {
        **pet,
        **{key: value for key, value in changes.items() if value is not None},
    }
    data = response.json()["data"]
    for field in ("id", "studentId", "name", "species", "age", "createdAt"):
        assert data[field] == expected[field]
    assert auth_client.get(pets_url).json()["data"]["items"] == [data]


def test_delete(auth_client, pets_url, pet_payload, db_session):
    pet = create_pet(auth_client, pets_url, pet_payload())
    response = auth_client.delete(f"{pets_url}/{pet['id']}")
    assert response.status_code == 200
    assert response.json()["message"] == "Recurso eliminado"
    assert response.json()["data"] == pet
    assert auth_client.get(pets_url).json()["data"] == {"total": 0, "items": []}
    assert db_session.get(PetModel, UUID(pet["id"])) is None


@pytest.mark.parametrize("method", ["POST", "PATCH"])
def test_validation_errors(auth_client, pets_url, pet_payload, method):
    url = pets_url
    if method == "PATCH":
        pet = create_pet(auth_client, pets_url, pet_payload())
        url += f"/{pet['id']}"
    response = auth_client.request(
        method, url, json={"name": "", "species": "<b>gato</b>", "age": -1}
    )
    assert response.status_code == 400
    assert response.json()["message"] == "Error de validación"
    assert set(response.json()["errors"]) == {"name", "species", "age"}


def test_missing_fields(auth_client, pets_url):
    response = auth_client.post(pets_url, json={})
    assert response.status_code == 400
    assert set(response.json()["errors"]) == {"name", "species"}


@pytest.mark.parametrize("method", ["POST", "PATCH"])
def test_extra_fields(auth_client, pets_url, pet_payload, method):
    url = pets_url
    if method == "PATCH":
        pet = create_pet(auth_client, pets_url, pet_payload())
        url += f"/{pet['id']}"
    response = auth_client.request(method, url, json=pet_payload(extra="no"))
    assert response.status_code == 400


@pytest.mark.parametrize("method", ["POST", "PATCH"])
def test_duplicate_name_rolls_back(auth_client, pets_url, pet_payload, method):
    create_pet(auth_client, pets_url, pet_payload())
    other = create_pet(auth_client, pets_url, pet_payload(name="Michi"))
    before = auth_client.get(pets_url).json()["data"]
    url = pets_url if method == "POST" else f"{pets_url}/{other['id']}"
    response = auth_client.request(method, url, json=pet_payload())
    assert response.status_code == 409
    assert (
        response.json()["errors"]["name"]["message"]
        == "Ya tienes una mascota con ese nombre"
    )
    assert auth_client.get(pets_url).json()["data"] == before


@pytest.mark.parametrize("method", ["GET", "POST", "PATCH", "DELETE"])
@pytest.mark.parametrize("student_id", [str(uuid4()), "no-uuid"])
def test_student_not_found(auth_client, pet_payload, method, student_id):
    url = f"/api/students/{student_id}/pets"
    if method in ("PATCH", "DELETE"):
        url += f"/{uuid4()}"
    response = auth_client.request(method, url, json=pet_payload())
    assert response.status_code == 404
    assert response.json()["message"] == "Estudiante no encontrado"


@pytest.mark.parametrize("method", ["PATCH", "DELETE"])
@pytest.mark.parametrize("kind", ["missing", "invalid", "other_student"])
def test_pet_not_found(
    auth_client, pets_url, create_student, pet_payload, method, kind
):
    other_url = f"/api/students/{create_student()['id']}/pets"
    pet = create_pet(auth_client, other_url, pet_payload())
    pet_id = {
        "missing": str(uuid4()),
        "invalid": "no-uuid",
        "other_student": pet["id"],
    }[kind]
    response = auth_client.request(
        method, f"{pets_url}/{pet_id}", json={"name": "Nuevo"}
    )
    assert response.status_code == 404
    assert response.json()["message"] == "Mascota no encontrada"
    assert auth_client.get(other_url).json()["data"]["items"] == [pet]
