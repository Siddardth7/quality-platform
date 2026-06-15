import pandas as pd

from spc_app.spc_engine.data_generator import generate_demo_dataset


def test_returns_dataframe():
    df = generate_demo_dataset()
    assert isinstance(df, pd.DataFrame)


def test_has_required_streams():
    df = generate_demo_dataset()
    streams = df["stream"].unique().tolist()
    assert "ply_thickness" in streams
    assert "autoclave_temp" in streams
    assert "hole_diameter" in streams
    assert "reject_proportion" in streams
    assert "surface_defects" in streams


def test_ply_thickness_values_in_range():
    df = generate_demo_dataset()
    ply = df[df["stream"] == "ply_thickness"]
    assert ply["value"].between(0.230, 0.270).all()


def test_autoclave_temp_values_in_range():
    df = generate_demo_dataset()
    temp = df[df["stream"] == "autoclave_temp"]
    assert temp["value"].between(170.0, 190.0).all()


def test_hole_diameter_values_in_range():
    df = generate_demo_dataset()
    dia = df[df["stream"] == "hole_diameter"]
    assert dia["value"].between(9.970, 10.030).all()


def test_required_columns_present():
    df = generate_demo_dataset()
    for col in ["stream", "subgroup", "value", "sample_size"]:
        assert col in df.columns, f"Missing column: {col}"


def test_ply_thickness_subgroup_size_5():
    df = generate_demo_dataset()
    ply = df[df["stream"] == "ply_thickness"]
    counts = ply.groupby("subgroup")["value"].count()
    assert (counts == 5).all()
