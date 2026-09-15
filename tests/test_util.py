import datetime as dt
from collections import namedtuple
from dataclasses import dataclass, field

import pytest

from ib_insync.util import (
    dataclassAsDict,
    dataclassAsTuple,
    dataclassNonDefaults,
    dataclassRepr,
    dataclassUpdate,
    formatIBDatetime,
    formatSI,
    isNan,
    parseIBDatetime,
    tree,
)


@dataclass
class Point:
    x: int = 0
    y: int = 0
    label: str = ''


@dataclass
class Bag:
    items: list = field(default_factory=list)
    value: float = 0.0


def test_formatIBDatetime():
    t = dt.datetime(2026, 9, 15, 12, 30, 45, tzinfo=dt.UTC)
    assert formatIBDatetime(t) == '20260915 12:30:45 UTC'
    endOfDay = dt.datetime(
        2026, 9, 15, 23, 59, 59).astimezone(dt.UTC)
    assert formatIBDatetime(dt.date(2026, 9, 15)) == endOfDay.strftime(
        '%Y%m%d %H:%M:%S UTC')
    assert formatIBDatetime(None) == ''
    assert formatIBDatetime('') == ''
    assert formatIBDatetime('20260915') == '20260915'


def test_parseIBDatetime():
    assert parseIBDatetime('20260915') == dt.date(2026, 9, 15)
    assert parseIBDatetime('0') == dt.datetime(1970, 1, 1, tzinfo=dt.UTC)
    assert parseIBDatetime('2026-09-15 10:30:00.0') == dt.datetime(  # noqa: DTZ001
        2026, 9, 15, 10, 30)
    t = parseIBDatetime('20260915 10:30:00 Europe/Amsterdam')
    assert str(t.tzinfo) == 'Europe/Amsterdam'
    assert (t.year, t.hour) == (2026, 10)


def test_tree():
    assert tree({'d': dt.date(2026, 9, 15), 'l': [1, 'x']}) == {
        'd': '2026-09-15', 'l': [1, 'x']}
    assert tree(Point(x=1)) == {'Point': {'x': 1}}
    assert tree(Point()) == {'Point': {}}
    Nt = namedtuple('Nt', 'a b')
    assert tree(Nt(1, 'x')) == {'a': 1, 'b': 'x'}


def test_dataclass_helpers():
    p = Point(x=1)
    assert dataclassAsDict(p) == {'x': 1, 'y': 0, 'label': ''}
    assert dataclassAsTuple(p) == (1, 0, '')
    assert dataclassNonDefaults(p) == {'x': 1}
    assert dataclassRepr(p) == 'Point(x=1)'
    dataclassUpdate(p, Point(x=2, y=3), label='p')
    assert (p.x, p.y, p.label) == (2, 3, 'p')
    for func in (dataclassAsDict, dataclassAsTuple, dataclassNonDefaults):
        with pytest.raises(TypeError):
            func(1)


def test_dataclassNonDefaults_skips_nan_and_empty_list():
    assert dataclassNonDefaults(Bag(value=float('nan'))) == {}
    assert dataclassNonDefaults(Bag(items=[1])) == {'items': [1]}


def test_isNan():
    assert isNan(float('nan'))
    assert not isNan(1.0)
    assert not isNan(0)


def test_formatSI():
    assert formatSI(0) == '0 '
    assert formatSI(1234567) == '1.23 M'
    assert formatSI(-1234567) == '-1.23 M'
    assert formatSI(0.5) == '500 m'
