"""Shared engine for the acceptance controls; native CI opts into the same cases."""

import os

import pytest

from heschema.schema import SchemaEngine


@pytest.fixture(scope='module')
def validation_engine():
    engine = SchemaEngine('blaze' if os.getenv('HESCHEMA_TEST_BLAZE') else 'jsonschema')
    yield engine
    engine.close()


# Windows asyncio socket exhaustion guard (Issue 5)
if os.name == 'nt':
    import socket
    import time
    _orig_socketpair = socket.socketpair

    def _safe_socketpair(family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0):
        for _ in range(15):
            try:
                lsock = socket.socket(family, type, proto)
                lsock.bind(('127.0.0.1', 0))
                lsock.listen(1)
                addr = lsock.getsockname()
                csock = socket.socket(family, type, proto)
                csock.connect(addr)
                ssock, _ = lsock.accept()
                lsock.close()
                return ssock, csock
            except OSError:
                try:
                    lsock.close()
                except Exception:
                    pass
                time.sleep(0.01)
        return _orig_socketpair(family, type, proto)

    socket.socketpair = _safe_socketpair

