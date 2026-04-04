"""Focused tests for conversion manager queue control."""

from src.core.conversion_manager import ConversionManager
from src.core.job_creation_worker import JobCreationWorker
from src.data.models import ConversionJob, ConversionStatus
from src.data.models import ConversionConfig


class _DummyRepository:
    def __init__(self):
        self.updated_jobs = []

    def update(self, job):
        self.updated_jobs.append((job.id, job.status))


class _DummyJobCreationWorker:
    def __init__(self):
        self.cancelled = False
        self.deleted = False

    def cancel(self):
        self.cancelled = True

    def deleteLater(self):
        self.deleted = True


def test_cancel_all_cancels_job_creation_worker():
    repo = _DummyRepository()
    manager = ConversionManager(repository=repo)
    worker = _DummyJobCreationWorker()
    manager._job_creation_worker = worker

    manager.cancel_all()

    assert worker.cancelled is True
    assert manager._job_creation_cancelled is True


def test_cancelled_job_creation_results_are_discarded_and_marked_cancelled():
    repo = _DummyRepository()
    manager = ConversionManager(repository=repo)
    worker = _DummyJobCreationWorker()
    manager._job_creation_worker = worker
    manager._job_creation_cancelled = True
    emitted_jobs = []
    all_completed = []
    manager.jobs_created.connect(lambda jobs: emitted_jobs.append(jobs))
    manager.all_completed.connect(lambda: all_completed.append(True))

    jobs = [
        ConversionJob(id=1, input_path="/tmp/a.mp4", output_path="/tmp/a_out.mp4"),
        ConversionJob(id=2, input_path="/tmp/b.mp4", output_path="/tmp/b_out.mp4"),
    ]

    manager._on_jobs_created(jobs)

    assert emitted_jobs == []
    assert all_completed == [True]
    assert manager.pending_count == 0
    assert repo.updated_jobs == [
        (1, ConversionStatus.CANCELLED),
        (2, ConversionStatus.CANCELLED),
    ]
    assert worker.deleted is True
    assert manager._job_creation_worker is None
    assert manager._job_creation_cancelled is False


def test_job_creation_worker_emits_partial_jobs_when_cancelled(monkeypatch):
    worker = JobCreationWorker(
        input_paths=["/tmp/a.mp4", "/tmp/b.mp4"],
        output_dir="/tmp/out",
        output_paths={},
        config=ConversionConfig(),
        repository=_DummyRepository(),
    )
    emitted_jobs = []

    monkeypatch.setattr(
        "src.core.job_creation_worker.cleanup_zero_byte_files",
        lambda paths: (paths, []),
    )

    created_count = {"value": 0}

    def fake_create_job(input_path):
        created_count["value"] += 1
        if created_count["value"] == 1:
            worker.cancel()
        return ConversionJob(
            id=created_count["value"],
            input_path=input_path,
            output_path=f"/tmp/out/{created_count['value']}.mp4",
        )

    monkeypatch.setattr(worker, "_create_job", fake_create_job)
    worker.completed.connect(lambda jobs: emitted_jobs.append(jobs))

    worker.run()

    assert len(emitted_jobs) == 1
    assert [job.id for job in emitted_jobs[0]] == [1]
