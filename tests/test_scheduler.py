"""调度逻辑单元测试."""
import pytest
from app import create_app
from models import db
from models.region import Region
from models.gate import Gate
from models.vehicle import VehicleInfo, VehicleStatus
from models.flight import Flight
from models.task import Task
from services.scheduler import Scheduler


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
    """插入一组最小可用数据用于测试 (A320 廊桥机位)."""
    with app.app_context():
        r = Region(code="A01", name="测试区")
        db.session.add(r)
        db.session.flush()

        g = Gate(code="A01", region_id=r.id, has_jet_bridge=True)
        db.session.add(g)
        db.session.flush()

        vi = VehicleInfo(plate_number="京T-TEST1", vehicle_type="GPU",
                         brand_model="TLD GPU-140", region="A")
        db.session.add(vi)
        vs = VehicleStatus(plate_number="京T-TEST1", current_status="IDLE")
        db.session.add(vs)
        db.session.flush()

        f = Flight(flight_no="TEST001", airline="测试航", aircraft_type="A320",
                   scheduled_at="2026-01-01 10:00", gate_id=g.id, region_id=r.id)
        db.session.add(f)
        db.session.flush()

        t = Task(flight_id=f.id, task_type="GPU", status="PENDING")
        db.session.add(t)
        db.session.commit()

        yield {"region": r, "gate": g, "flight": f, "task": t}


class TestScheduler:
    def test_schedule_returns_dict(self, sample_data):
        scheduler = Scheduler()
        result = scheduler.schedule_for_flight(sample_data["flight"].id)
        assert isinstance(result, dict)
        assert "tasks" in result

    def test_schedule_nonexistent_flight(self, app):
        with app.app_context():
            scheduler = Scheduler()
            with pytest.raises(ValueError):
                scheduler.schedule_for_flight(9999)
