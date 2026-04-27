import sys

import pytest

sys.path.append("../src")
from pytosql.expr import Param, col, query, table


def test_query():
    string, parameters = (
        query.select(col.id, col.name)
        .from_(table.employees)
        .where(col.id == Param(2), col.name == Param(""))
        .prepare()
    )
    assert string == "select id, name\nfrom employees\nwhere (id = ?) and (name = ?)\n"
    assert parameters == (2, "")
