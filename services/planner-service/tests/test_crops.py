import dataclasses

import pytest

from crops import CROPS, Crop, UnknownCrop, get_crop


def test_tomato_values():
    c = get_crop("tomato")
    assert (c.kc_ini, c.kc_mid, c.kc_end) == (0.6, 1.15, 0.80)
    assert c.stage_days == (30, 40, 45, 30)
    assert c.root_depth_m == 0.7
    assert c.p == 0.40


def test_bell_pepper_values():
    c = get_crop("bell-pepper")
    assert (c.kc_ini, c.kc_mid, c.kc_end) == (0.6, 1.05, 0.90)
    assert c.stage_days == (30, 35, 40, 20)
    assert c.root_depth_m == 0.5
    assert c.p == 0.30


def test_stage_lengths_are_positive_integers():
    for crop in CROPS.values():
        assert len(crop.stage_days) == 4
        assert all(isinstance(d, int) and d > 0 for d in crop.stage_days)


def test_kc_values_and_p_are_in_range():
    for crop in CROPS.values():
        assert crop.kc_ini > 0 and crop.kc_mid > 0 and crop.kc_end > 0
        assert 0.1 <= crop.p <= 0.8
        assert crop.root_depth_m > 0


def test_unknown_crop_raises_with_its_id():
    with pytest.raises(UnknownCrop) as info:
        get_crop("wheat")
    assert info.value.crop_id == "wheat"


def test_crop_is_immutable():
    crop = get_crop("tomato")
    with pytest.raises(dataclasses.FrozenInstanceError):
        crop.p = 0.9
    assert isinstance(crop, Crop)
