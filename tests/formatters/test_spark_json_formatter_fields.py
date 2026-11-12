"""Tests for the fields SparkJsonFormatter adds to and leaves out of its output."""

import io
import json
import logging
from pathlib import Path

from logspark.Filters import PathNormalizationFilter
from logspark.Formatters import SparkJsonFormatter
from logspark.Handlers import SparkJsonHandler
from logspark.Types.Options import PathResolutionSetting
from logspark.Types.SparkRecordAttrs import SparkRecordAttrs

_FMT = "%(name)s %(levelname)s %(message)s %(filename)s"


def _record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        "test", logging.INFO, "/project/pkg/module.py", 7, "hello", None, None
    )
    for name, value in extra.items():
        setattr(record, name, value)
    return record


def _spark(filepath: str) -> SparkRecordAttrs:
    return SparkRecordAttrs(
        filename=Path(filepath).name,
        filepath=Path(filepath),
        lineno=7,
        function="f",
        uri=None,
        exc_type=None,
        exc_value=None,
    )


class TestDroppedFields:
    def test_color_message_is_left_out_by_default(self):
        record = _record(color_message="\x1b[1mhello\x1b[0m", other=1)
        out = json.loads(SparkJsonFormatter(fmt=_FMT).format(record))
        assert "color_message" not in out
        assert out["other"] == 1

    def test_the_record_keeps_the_dropped_attribute(self):
        record = _record(color_message="\x1b[1mhello\x1b[0m")
        SparkJsonFormatter(fmt=_FMT).format(record)
        assert record.color_message == "\x1b[1mhello\x1b[0m"

    def test_an_empty_drop_list_keeps_everything(self):
        record = _record(color_message="coloured")
        out = json.loads(SparkJsonFormatter(fmt=_FMT, drop_fields=()).format(record))
        assert out["color_message"] == "coloured"

    def test_a_custom_drop_list_replaces_the_default(self):
        record = _record(color_message="coloured", secret="s", kept=1)
        out = json.loads(SparkJsonFormatter(fmt=_FMT, drop_fields=["secret"]).format(record))
        assert "secret" not in out
        assert out["color_message"] == "coloured"
        assert out["kept"] == 1

    def test_reserved_attrs_passed_by_the_caller_are_kept_reserved(self):
        record = _record(color_message="coloured", mine="m", kept=1)
        formatter = SparkJsonFormatter(fmt=_FMT, reserved_attrs=["mine"])
        out = json.loads(formatter.format(record))
        assert "mine" not in out
        assert "color_message" not in out
        assert out["kept"] == 1

    def test_the_handler_drops_color_message(self):
        stream = io.StringIO()
        logger = logging.getLogger("test.json_fields.handler")
        logger.handlers = [SparkJsonHandler(stream=stream)]
        logger.propagate = False
        logger.setLevel(logging.INFO)
        logger.info("started", extra={"color_message": "\x1b[32mstarted\x1b[0m"})
        out = json.loads(stream.getvalue())
        assert out["message"] == "started"
        assert "color_message" not in out


class TestFilepath:
    def test_no_filepath_without_spark_attributes(self):
        out = json.loads(SparkJsonFormatter(fmt=_FMT).format(_record()))
        assert "filepath" not in out

    def test_the_resolved_path_is_written_in_posix_form(self):
        record = _record(spark=_spark("pkg/module.py"))
        out = json.loads(SparkJsonFormatter(fmt=_FMT).format(record))
        assert out["filepath"] == "pkg/module.py"
        assert out["filename"] == "module.py"

    def test_a_filepath_from_the_log_call_wins(self):
        record = _record(spark=_spark("pkg/module.py"), filepath="from-extra")
        out = json.loads(SparkJsonFormatter(fmt=_FMT).format(record))
        assert out["filepath"] == "from-extra"
        assert record.filepath == "from-extra"

    def test_the_added_filepath_does_not_stay_on_the_record(self):
        record = _record(spark=_spark("pkg/module.py"))
        SparkJsonFormatter(fmt=_FMT).format(record)
        assert not hasattr(record, "filepath")

    def test_spark_attributes_never_reach_the_output(self):
        record = _record(spark=_spark("pkg/module.py"), _spark_exc=True)
        out = json.loads(SparkJsonFormatter(fmt=_FMT).format(record))
        assert "spark" not in out
        assert "_spark_exc" not in out

    def test_path_normalization_filter_feeds_the_relative_path(self, tmp_path: Path):
        source = tmp_path / "pkg" / "module.py"
        record = logging.LogRecord("test", logging.INFO, str(source), 7, "hello", None, None)
        path_filter = PathNormalizationFilter(resolution_mode=PathResolutionSetting.RELATIVE)
        path_filter.project_root = tmp_path
        path_filter.filter(record)
        out = json.loads(SparkJsonFormatter(fmt=_FMT).format(record))
        assert out["filepath"] == "pkg/module.py"
