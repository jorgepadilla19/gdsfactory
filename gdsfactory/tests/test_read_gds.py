# from pprint import pprint

import jsondiff
from pytest_regressions.data_regression import DataRegressionFixture

import gdsfactory as gf


def test_read_gds_hash() -> gf.Component:
    gdspath = gf.CONFIG["gdsdir"] / "straight.gds"
    c = gf.read.from_gds(gdspath)
    assert (
        c.hash_geometry() == "8f0e7c4660c98d810082e85203013134614611bf"
    ), c.hash_geometry()
    return c


def test_read_gds_with_settings(data_regression: DataRegressionFixture) -> None:
    gdspath = gf.CONFIG["gdsdir"] / "straight.gds"
    c = gf.read.from_gds(gdspath)
    data_regression.check(c.to_dict)


def test_read_gds_equivalent():
    """Ensures we can load it from GDS + YAML and get the same component settings"""
    c1 = gf.c.straight(length=1.234)
    gdspath = gf.CONFIG["gdsdir"] / "straight.gds"
    c2 = gf.read.from_gds(gdspath)

    d1 = c1.to_dict
    d2 = c2.to_dict

    # d1.pop('cells')
    # d2.pop('cells')
    # c1.pprint
    # c2.pprint

    d = jsondiff.diff(d1, d2)

    # pprint(d1)
    # pprint(d2)
    # pprint(d)
    assert len(d) == 0, d


def test_mix_cells_from_gds_and_from_function():
    """Ensures not duplicated cell names.
    when cells loaded from GDS and have the same name as a function
    with @cell decorator
    """
    gdspath = gf.CONFIG["gdsdir"] / "straight.gds"
    c = gf.Component("test_mix_cells_from_gds_and_from_function")
    c << gf.c.straight(length=1.234)
    c << gf.read.from_gds(gdspath)
    c.write_gds()


def _write():
    c1 = gf.c.straight(length=1.234)
    gdspath = gf.CONFIG["gdsdir"] / "straight.gds"
    c1.write_gds_with_metadata(gdspath=gdspath)
    c1.show()
    c1.pprint


if __name__ == "__main__":
    # test_read_gds_equivalent()
    # c = test_read_gds_hash()
    # test_mix_cells_from_gds_and_from_function()

    # _write()
    # test_load_component_gds()
    # test_read_gds_with_settings()
    # test_read_gds_equivalent()

    c1 = gf.c.straight(length=1.234)
    gdspath = gf.CONFIG["gdsdir"] / "straight.gds"

    c2 = gf.read.from_gds(gdspath)
    d1 = c1.to_dict_config
    d2 = c2.to_dict_config
    dd1 = c1.to_dict
    dd2 = c2.to_dict
    d = jsondiff.diff(dd1, dd2)
    print(d)