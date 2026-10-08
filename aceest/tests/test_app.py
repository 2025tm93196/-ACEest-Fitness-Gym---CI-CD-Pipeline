import pytest

from app import calculate_bmi, calculate_calories, create_app, PROGRAMS


@pytest.fixture
def client(tmp_path):
    app = create_app(str(tmp_path / "test.db"))
    app.config["TESTING"] = True
    return app.test_client()


def add(client, **over):
    payload = {"name": "Arjun", "program": "Beginner (BG)", "weight": 70,
               "height": 175, "age": 25}
    payload.update(over)
    return client.post("/clients", json=payload)


# ---- pure logic ----
@pytest.mark.parametrize("program,weight,expected", [
    ("Fat Loss (FL) - 3 day", 80, 1760),
    ("Fat Loss (FL) - 5 day", 80, 1920),
    ("Muscle Gain (MG) - PPL", 70, 2450),
    ("Beginner (BG)", 60, 1560),
])
def test_calories(program, weight, expected):
    assert calculate_calories(weight, program) == expected


def test_calories_invalid():
    with pytest.raises(ValueError):
        calculate_calories(70, "Nope")
    with pytest.raises(ValueError):
        calculate_calories(0, "Beginner (BG)")


@pytest.mark.parametrize("h,w,cat", [
    (180, 50, "Underweight"), (175, 70, "Normal"),
    (170, 80, "Overweight"), (165, 95, "Obese"),
])
def test_bmi_categories(h, w, cat):
    assert calculate_bmi(h, w)[1] == cat


def test_bmi_value_and_invalid():
    assert calculate_bmi(175, 70)[0] == 22.9
    with pytest.raises(ValueError):
        calculate_bmi(0, 70)


# ---- API ----
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.get_json() == {"status": "ok"}


def test_programs(client):
    assert set(client.get("/programs").get_json()) == set(PROGRAMS)


def test_create_and_get_client(client):
    r = add(client)
    assert r.status_code == 201 and r.get_json()["calories"] == 1820
    got = client.get("/clients/Arjun").get_json()
    assert got["program"] == "Beginner (BG)" and got["height"] == 175


def test_create_requires_name_and_program(client):
    assert add(client, name="").status_code == 400
    assert add(client, program="Bogus").status_code == 400


def test_create_invalid_weight(client):
    assert add(client, weight=-5).status_code == 400


def test_save_client_updates_existing(client):
    add(client)
    add(client, weight=80)
    assert len(client.get("/clients").get_json()) == 1
    assert client.get("/clients/Arjun").get_json()["calories"] == 2080


def test_get_missing_client(client):
    assert client.get("/clients/Ghost").status_code == 404


def test_delete_client(client):
    add(client)
    assert client.delete("/clients/Arjun").status_code == 200
    assert client.delete("/clients/Arjun").status_code == 404


def test_bmi_endpoint(client):
    add(client)
    r = client.get("/clients/Arjun/bmi").get_json()
    assert r["bmi"] == 22.9 and r["category"] == "Normal"
    assert client.get("/clients/Ghost/bmi").status_code == 404


def test_bmi_missing_height(client):
    add(client, height=None)
    assert client.get("/clients/Arjun/bmi").status_code == 400


def test_progress_flow(client):
    add(client)
    assert client.post("/clients/Arjun/progress", json={"adherence": 80}).status_code == 201
    client.post("/clients/Arjun/progress", json={"adherence": 90})
    data = client.get("/clients/Arjun/progress").get_json()
    assert [d["adherence"] for d in data] == [80, 90]


@pytest.mark.parametrize("bad", [-1, 101, "x", None])
def test_progress_validation(client, bad):
    add(client)
    assert client.post("/clients/Arjun/progress", json={"adherence": bad}).status_code == 400


def test_progress_unknown_client(client):
    assert client.post("/clients/Ghost/progress", json={"adherence": 50}).status_code == 404


def test_workout_flow(client):
    add(client)
    r = client.post("/clients/Arjun/workouts",
                    json={"workout_type": "Strength", "duration_min": 45, "date": "2026-01-02"})
    assert r.status_code == 201
    w = client.get("/clients/Arjun/workouts").get_json()
    assert w[0]["workout_type"] == "Strength" and w[0]["duration_min"] == 45


def test_workout_validation(client):
    add(client)
    assert client.post("/clients/Arjun/workouts", json={"workout_type": "Yoga"}).status_code == 400
    assert client.post("/clients/Ghost/workouts", json={"workout_type": "Cardio"}).status_code == 404
