import pandas as pd
from spc_app.spc_engine.utils import subgroup_rows


def test_returns_list_of_lists():
    frame = pd.DataFrame({"subgroup": [1, 1, 2, 2], "value": [10.0, 11.0, 12.0, 13.0]})
    assert subgroup_rows(frame) == [[10.0, 11.0], [12.0, 13.0]]


def test_sorts_by_subgroup_index():
    frame = pd.DataFrame({"subgroup": [2, 1, 2, 1], "value": [20.0, 10.0, 21.0, 11.0]})
    result = subgroup_rows(frame)
    assert result[0] == [10.0, 11.0]
    assert result[1] == [20.0, 21.0]


def test_single_subgroup():
    frame = pd.DataFrame({"subgroup": [1, 1, 1], "value": [5.0, 6.0, 7.0]})
    assert subgroup_rows(frame) == [[5.0, 6.0, 7.0]]
