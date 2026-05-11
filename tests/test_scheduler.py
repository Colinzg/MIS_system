"""调度逻辑单元测试."""
import pytest
from app import create_app
from models import db
from models.region import Region
from models.vehicle import Vehicle
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
    """插入一组最小可用数据用于测试."""
    with app.app_context():
        r = Region(code="A01", name="测试区")
        db.session.add(r)
        db.session.flush()

        v = Vehicle(plate="京T-TEST1", type="FUEL", status="IDLE", region_id=r.id)
        db.session.add(v)
        db.session.flush()

        f = Flight(flight_no="TEST001", airline="测试航", scheduled_at="2026-01-01 10:00",
                   region_id=r.id)
        db.session.add(f)
        db.session.commit()

        yield {"region": r, "vehicle": v, "flight": f}


class TestScheduler:
    """Scheduler 核心逻辑测试."""

    def test_schedule_returns_dict(self, sample_data):
        """调用 schedule_for_flight 应返回 dict."""
        scheduler = Scheduler()
        result = scheduler.schedule_for_flight(sample_data["flight"].id)
        assert isinstance(result, dict)
        assert "tasks" in result

    def test_schedule_nonexistent_flight(self):
        """调度不存在的航班应抛出 ValueError."""
        scheduler = Scheduler()
        with pytest.raises(ValueError):
            scheduler.schedule_for_flight(9999)
