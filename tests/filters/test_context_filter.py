"""Tests for ContextFilter and bound_context."""

import asyncio
import io
import json
import logging
import threading

import pytest

from logspark.Filters import ContextFilter, bound_context, get_bound_context
from logspark.Handlers import SparkJsonHandler


def _record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord("test", logging.INFO, "file.py", 1, "hello", None, None)
    for name, value in extra.items():
        setattr(record, name, value)
    return record


class TestBoundContext:
    def test_nothing_is_bound_outside_a_block(self):
        assert dict(get_bound_context()) == {}

    def test_fields_are_bound_inside_the_block_and_gone_after(self):
        with bound_context(request_id="r-1"):
            assert dict(get_bound_context()) == {"request_id": "r-1"}
        assert dict(get_bound_context()) == {}

    def test_inner_block_adds_fields_and_wins_on_the_same_name(self):
        with bound_context(request_id="r-1", user="a"):
            with bound_context(user="b", tool="t"):
                assert dict(get_bound_context()) == {
                    "request_id": "r-1",
                    "user": "b",
                    "tool": "t",
                }
            assert dict(get_bound_context()) == {"request_id": "r-1", "user": "a"}

    def test_bindings_are_restored_when_the_block_raises(self):
        with pytest.raises(RuntimeError):
            with bound_context(request_id="r-1"):
                raise RuntimeError("boom")
        assert dict(get_bound_context()) == {}

    def test_the_view_is_read_only(self):
        with bound_context(request_id="r-1"):
            with pytest.raises(TypeError):
                get_bound_context()["request_id"] = "other"  # type: ignore[index]

    def test_a_thread_does_not_see_another_threads_binding(self):
        seen: dict[str, object] = {}

        def read() -> None:
            seen.update(get_bound_context())

        with bound_context(request_id="r-1"):
            thread = threading.Thread(target=read)
            thread.start()
            thread.join()
        assert seen == {}

    def test_asyncio_tasks_keep_their_own_bindings(self):
        async def worker(request_id: str) -> object:
            with bound_context(request_id=request_id):
                await asyncio.sleep(0)
                return get_bound_context()["request_id"]

        async def run() -> list[object]:
            return list(await asyncio.gather(worker("r-1"), worker("r-2")))

        assert asyncio.run(run()) == ["r-1", "r-2"]


class TestContextFilter:
    def test_always_keeps_the_record(self):
        assert ContextFilter().filter(_record()) is True

    def test_copies_bound_fields_onto_the_record(self):
        record = _record()
        with bound_context(request_id="r-1", attempt=2):
            ContextFilter().filter(record)
        assert record.request_id == "r-1"
        assert record.attempt == 2

    def test_leaves_the_record_alone_when_nothing_is_bound(self):
        record = _record()
        before = dict(record.__dict__)
        ContextFilter().filter(record)
        assert record.__dict__ == before

    def test_a_field_from_the_log_call_wins_over_a_bound_field(self):
        record = _record(request_id="from-extra")
        with bound_context(request_id="bound"):
            ContextFilter().filter(record)
        assert record.request_id == "from-extra"

    @pytest.mark.parametrize("name", ["name", "msg", "args", "message", "asctime", "getMessage"])
    def test_a_reserved_name_is_written_under_the_prefix(self, name: str):
        record = _record()
        original = getattr(record, name, None)
        with bound_context(**{name: "bound"}):
            ContextFilter().filter(record)
        assert getattr(record, f"ctx_{name}") == "bound"
        assert getattr(record, name, None) == original

    def test_the_prefix_can_be_chosen(self):
        record = _record()
        with bound_context(name="bound"):
            ContextFilter(clash_prefix="field_").filter(record)
        assert record.field_name == "bound"

    def test_an_empty_prefix_is_refused(self):
        with pytest.raises(ValueError, match="clash_prefix"):
            ContextFilter(clash_prefix="")

    def test_bound_fields_reach_the_json_output_through_a_handler_filter(self):
        stream = io.StringIO()
        handler = SparkJsonHandler(stream=stream)
        handler.addFilter(ContextFilter())
        logger = logging.getLogger("test.context_filter.json")
        logger.handlers = [handler]
        logger.propagate = False
        logger.setLevel(logging.INFO)

        with bound_context(request_id="r-1"):
            logger.info("inside")
        logger.info("outside")

        inside, outside = (json.loads(line) for line in stream.getvalue().splitlines())
        assert inside["request_id"] == "r-1"
        assert "request_id" not in outside
