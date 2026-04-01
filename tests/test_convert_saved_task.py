"""Tests for Convert saved-task helpers."""

from src.core.convert_saved_task import (
    ConvertQueueItem,
    ConvertQueueItemStatus,
    build_convert_task_payload,
    detect_existing_outputs,
    load_convert_task_payload,
)


def test_build_convert_task_payload_preserves_queue_order():
    items = [
        ConvertQueueItem(
            item_id="one",
            input_path="/tmp/1.mp4",
            output_path="/tmp/out/1.mp4",
            display_name="one.mp4",
        ),
        ConvertQueueItem(
            item_id="two",
            input_path="/tmp/2.mp4",
            output_path="/tmp/out/2.mp4",
            display_name="two.mp4",
            status=ConvertQueueItemStatus.PROCESSING,
            progress_percent=12.5,
        ),
    ]

    payload = build_convert_task_payload(items, {"output_codec": "h264", "output_dir": "/tmp/out"})
    restored = load_convert_task_payload(payload)

    assert [item["item_id"] for item in payload["items"]] == ["one", "two"]
    assert [item.item_id for item in restored] == ["one", "two"]
    assert payload["config"] == {"output_codec": "h264", "output_dir": "/tmp/out"}
    assert restored[1].status == ConvertQueueItemStatus.PROCESSING
    assert restored[1].progress_percent == 12.5


def test_detect_existing_outputs_marks_non_zero_files_complete(tmp_path):
    output_path = tmp_path / "done.mp4"
    output_path.write_bytes(b"video-bytes")

    item = ConvertQueueItem(
        item_id="done",
        input_path=str(tmp_path / "source.mp4"),
        output_path=str(output_path),
        status=ConvertQueueItemStatus.PENDING,
    )

    updated = detect_existing_outputs([item])

    assert updated[0].status == ConvertQueueItemStatus.COMPLETED
    assert updated[0].progress_percent == 100.0
    assert updated[0].detail == "Already processed"
