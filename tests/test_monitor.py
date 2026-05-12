"""进度监控子系统单元测试."""
import pytest
from app import create_app
from models import db
from models.region import Region
from models.flight import Flight
from services.monitor import Monitor


@pytest.fixture
def app():
    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


class TestMonitor:
    def test_unassigned_tasks_empty(self, app):
        with app.app_context():
            result = Monitor.check_unassigned_tasks()
            assert isinstance(result, list)

    def test_flight_progress(self, app):
        with app.app_context():
            r = Region(code="A01", name="测试区")
            db.session.add(r)
            db.session.flush()
            f = Flight(flight_no="TEST001", airline="测试航",
                       scheduled_at="2026-01-01 10:00", region_id=r.id)
            db.session.add(f)
            db.session.commit()
            progress = Monitor.get_flight_progress(f.id)
            assert progress["total"] == 0
            assert progress["progress_pct"] == 0
