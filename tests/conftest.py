
import pytest
import pytest_asyncio

import ib_insync as ibi


@pytest_asyncio.fixture(scope='session', loop_scope='session')
async def ib():
    ib = ibi.IB()
    try:
        await ib.connectAsync(port=7947)
    except (ConnectionRefusedError, TimeoutError):
        pytest.skip("IB Gateway/TWS not running")
    yield ib
    ib.disconnect()
