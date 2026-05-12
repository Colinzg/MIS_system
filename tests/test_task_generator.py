"""任务生成子系统单元测试."""
import pytest
from app import create_app
from models import db
from models.region import Region
from models.flight import Flight
from models.aircraft_resource import AircraftResource
from services.task_generator import TaskGenerator


@pytest.fixture
def app():
    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def sample_data(app):
    with app.app_context():
        r = Region(code="A01", name="测试区")
        db.session.add(r)
        db.session.flush()

        db.session.add(AircraftResource(aircraft_type="A320", required_vehicle_type="FUEL", quantity=1))
        db.session.add(AircraftResource(aircraft_type="A320", required_vehicle_type="BAG", quantity=2))
        db.session.flush()

        f = Flight(flight_no="TEST001", airline="测试航", aircraft_type="A320",
                   scheduled_at="2026-01-01 10:00", region_id=r.id)
        db.session.add(f)
        db.session.commit()
        yield {"flight": f}


class TestTaskGenerator:
    def test_generate_creates_tasks(self, sample_data):
        result = TaskGenerator.generate_for_flight(sample_data["flight"].id)
        assert result["tasks_created"] == 3  # FUEL x1 + BAG x2
        assert len(result["errors"]) == 0

    def test_generate_no_rules(self, app):
        with app.app_context():
            r = Region(code="B02", name="无规则区")
            db.session.add(r)
            db.session.flush()
            f = Flight(flight_no="NORULE", airline="测试", aircraft_type="B737",
                       scheduled_at="2026-01-01 10:00", region_id=r.id)
            db.session.add(f)
            db.session.commit()

            result = TaskGenerator.generate_for_flight(f.id)
            assert result["tasks_created"] == 0
            assert len(result["errors"]) == 1
