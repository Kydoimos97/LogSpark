import logging


from lorem_text import lorem


def test_dump_all_env_vars():
    import os
    import sys

    # print("\n=== ALL ENVIRONMENT VARIABLES ===")
    #
    # for key in sorted(os.environ):
    #     if key != 'PATH' and key != 'PSMODULEPATH':
    #         print(f"{key:32} = {os.environ[key]!r}")
    #
    # print("\n=== STDIO ===")
    # print(f"stdout.isatty(): {sys.stdout.isatty()}")
    # print(f"stdin.isatty():  {sys.stdin.isatty()}")
    # print(f"stderr.isatty(): {sys.stderr.isatty()}")

    try:
        import shutil
        print("\n=== shutil.get_terminal_size ===")
        print(shutil.get_terminal_size())
    except Exception as e:
        print("shutil.get_terminal_size error:", repr(e))

    # Force pytest to always show output
    assert True

    from rich.logging import RichHandler
    from logspark.Handlers.Rich.SparkRichHandler import SparkRichHandler
    logger = logging.getLogger("testlogger")
    logger.setLevel(logging.DEBUG)
    logger.addHandler(RichHandler())
    handler2 = logging.StreamHandler()
    handler2.setLevel(logging.DEBUG)
    logger.addHandler(handler2)
    logger.addHandler(SparkRichHandler())
    logger.info(lorem.paragraph())
    logger.info(lorem.sentence())

    assert True

