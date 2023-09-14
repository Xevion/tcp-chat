import logging

from shared import logging_config


def test_configure_sets_root_level_and_a_stream_handler():
    logging_config.configure(level=logging.DEBUG)
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)


def test_configure_writes_to_a_logfile(tmp_path):
    logfile = tmp_path / 'app.log'
    logging_config.configure(level=logging.INFO, logfile=str(logfile))
    logging.getLogger('test').info('hello-from-test')
    for handler in logging.getLogger().handlers:
        handler.flush()
    assert 'hello-from-test' in logfile.read_text()


def test_configure_does_not_stack_handlers_on_repeated_calls():
    logging_config.configure()
    logging_config.configure()
    root = logging.getLogger()
    stream_only = [
        h
        for h in root.handlers
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler)
    ]
    assert len(stream_only) == 1
