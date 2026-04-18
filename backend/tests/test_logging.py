import json
import logging

from app.core.logging import configure_logging, fingerprint_text, mask_identifier


def test_configure_logging_sets_application_loggers_to_info() -> None:
    configure_logging()

    app_logger = logging.getLogger("app")
    api_logger = logging.getLogger("promoflow.api")

    assert app_logger.level == logging.INFO
    assert api_logger.level == logging.INFO
    assert any(
        handler.get_name() == "promoflow.console" for handler in app_logger.handlers
    )
    assert any(
        handler.get_name() == "promoflow.console" for handler in api_logger.handlers
    )


def test_application_logs_are_rendered_as_structured_json() -> None:
    configure_logging()
    logger = logging.getLogger("app.test.logging")
    handler = logging.getLogger("app").handlers[0]

    record = logger.makeRecord(
        name=logger.name,
        level=logging.INFO,
        fn=__file__,
        lno=10,
        msg="bot_reply_sent chat_id=oc_123456 answer_len=20",
        args=(),
        exc_info=None,
    )

    payload = json.loads(handler.format(record))

    assert payload["logger"] == "app.test.logging"
    assert payload["level"] == "INFO"
    assert payload["message"] == "bot_reply_sent chat_id=oc***56 answer_len=20"
    assert "timestamp" in payload


def test_json_messages_preserve_fields_and_stack_traces() -> None:
    configure_logging()
    logger = logging.getLogger("app.test.logging")
    handler = logging.getLogger("app").handlers[0]

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        import sys

        record = logger.makeRecord(
            name=logger.name,
            level=logging.ERROR,
            fn=__file__,
            lno=32,
            msg=json.dumps(
                {
                    "message": "search_timing",
                    "query_parse_ms": 1.2,
                    "query": "门店开业视频",
                },
                ensure_ascii=False,
            ),
            args=(),
            exc_info=sys.exc_info(),
        )

    payload = json.loads(handler.format(record))

    assert payload["message"] == "search_timing"
    assert payload["query_parse_ms"] == 1.2
    assert payload["query"] == "[redacted]"
    assert payload["exc_info"] == "RuntimeError"
    assert "RuntimeError: boom" in payload["stack_trace"]


def test_logging_helpers_mask_and_fingerprint_sensitive_values() -> None:
    assert mask_identifier("oc_123456") == "oc***56"
    assert mask_identifier("abcd") == "***"
    assert fingerprint_text("门店开业视频")
    assert len(fingerprint_text("门店开业视频") or "") == 12
