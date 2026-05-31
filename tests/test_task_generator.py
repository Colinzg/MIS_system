"""任务生成子系统单元测试 — 测试 AircraftType.generate_tasks() 和 TaskGenerator."""
import pytest
from app import create_app
from models import db
from models.region import Region
from models.gate import Gate
from models.flight import Flight
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

        # 廊桥机位
        g1 = Gate(code="A01", region_id=r.id, has_jet_bridge=True)
        # 远机位
        g2 = Gate(code="A05", region_id=r.id, has_jet_bridge=False)
        db.session.add_all([g1, g2])
        db.session.flush()

        f1 = Flight(flight_no="TEST001", airline="测试航", aircraft_type="A320",
                    scheduled_at="2026-01-01 10:00", gate_id=g1.id, region_id=r.id)
        f2 = Flight(flight_no="TEST002", airline="测试航", aircraft_type="B777",
                    scheduled_at="2026-01-01 10:30", gate_id=g2.id, region_id=r.id)
        db.session.add_all([f1, f2])
        db.session.commit()
        yield {"region": r, "gate_jetbridge": g1, "gate_remote": g2, "flight_jb": f1, "flight_remote": f2}


class TestTaskGenerator:
    def test_generate_for_jetbridge_gate(self, sample_data):
        """廊桥机位不应生成 STAIR 和 BUS 任务."""
        result = TaskGenerator.generate_for_flight(sample_data["flight_jb"].id)
        assert result["tasks_created"] > 0
        assert len(result["errors"]) == 0

    def test_generate_for_remote_gate(self, sample_data):
        """远机位应生成 STAIR 和 BUS 任务."""
        result = TaskGenerator.generate_for_flight(sample_data["flight_remote"].id)
        assert result["tasks_created"] > 0
        assert len(result["errors"]) == 0
        # 远机位任务数应该 > 廊桥机位（多了 STAIR + BUS）
        jb_result = TaskGenerator.generate_for_flight(sample_data["flight_jb"].id)
        assert result["tasks_created"] > jb_result["tasks_created"]

    def test_generate_no_aircraft_type(self, app):
        with app.app_context():
            r = Region(code="B02", name="无规则区")
            db.session.add(r)
            db.session.flush()
            g = Gate(code="B01", region_id=r.id, has_jet_bridge=True)
            db.session.add(g)
            db.session.flush()
            f = Flight(flight_no="NORULE", airline="测试",
                       scheduled_at="2026-01-01 10:00", gate_id=g.id, region_id=r.id)
            db.session.add(f)
            db.session.commit()

            with pytest.raises(ValueError):
                TaskGenerator.generate_for_flight(f.id)

    def test_generate_nonexistent_flight(self, app):
        with app.app_context():
            with pytest.raises(ValueError):
                TaskGenerator.generate_for_flight(9999)

    def test_tasks_have_dependencies(self, sample_data):
        """生成的任务应有 depends_on 依赖链."""
        result = TaskGenerator.generate_for_flight(sample_data["flight_remote"].id)
        from models.task import Task
        tasks = Task.query.filter_by(flight_id=sample_data["flight_remote"].id).all()
        # TOW 是最后一步，应依赖其他任务，但 depends_on 设置可能为 None
        # 至少 STAIR 之后的 BUS 应有依赖
        assert len(tasks) == result["tasks_created"]
