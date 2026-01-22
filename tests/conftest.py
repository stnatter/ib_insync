
import pytest

import ib_insync as ibi


@pytest.fixture(scope='session')
async def ib():
    ib = ibi.IB()
    await ib.connectAsync()
    yield ib
    ib.disconnect()
