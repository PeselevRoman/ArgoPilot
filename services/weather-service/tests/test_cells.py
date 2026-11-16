from cache import cell_centre, cell_of


def test_cell_of_rounds_down_to_tenths():
    assert cell_of(31.25, 34.79) == (312, 347)


def test_exact_tenth_belongs_to_its_own_cell():
    assert cell_of(31.3, 34.7) == (313, 347)
    assert cell_of(0.3, 0.7) == (3, 7)
    assert cell_of(1.1, 1.1) == (11, 11)


def test_negative_values_round_toward_minus_infinity():
    assert cell_of(-0.05, -0.05) == (-1, -1)
    assert cell_of(-0.1, -0.1) == (-1, -1)
    assert cell_of(-0.11, -0.11) == (-2, -2)


def test_points_in_one_cell_share_it():
    assert cell_of(31.2, 34.7) == cell_of(31.29, 34.79)


def test_adjacent_points_in_different_cells():
    assert cell_of(31.29, 34.7) != cell_of(31.3, 34.7)
    assert cell_of(31.2, 34.69) != cell_of(31.2, 34.7)


def test_centre_is_cell_origin_plus_half_a_tenth():
    lat, lon = cell_centre((312, 347))
    assert lat == 31.25
    assert lon == 34.75


def test_centre_is_clamped_at_the_edges():
    assert cell_centre(cell_of(90, 180)) == (90.0, 180.0)
    lat, lon = cell_centre(cell_of(-90, -180))
    assert lat >= -90
    assert lon >= -180
