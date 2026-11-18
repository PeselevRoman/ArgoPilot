"""The crop table: FAO-56 values for the crops the planner knows.

These values are our judgment calls (the instructor said to apply judgment and that
values can be changed later). Each one that is a choice, not a printed number, says so.
Not applied (documented approximations): the climate adjustment of Kc mid and
Kc end (needs wind and humidity), and FAO's ETc adjustment of p.
Sources are in docs/research/fao56.md (sections 2.1 to 2.3).
"""

from dataclasses import dataclass


# A frozen dataclass is like a C# readonly struct or a record: the fields are
# set once in the constructor, and assigning to one later raises
# dataclasses.FrozenInstanceError. A shared table must not change by accident.
@dataclass(frozen=True)
class Crop:
    kc_ini: float
    kc_mid: float
    kc_end: float
    stage_days: tuple[int, int, int, int]  # initial, development, mid, late
    root_depth_m: float
    p: float


class UnknownCrop(Exception):
    def __init__(self, crop_id: str) -> None:
        super().__init__(f"unknown crop: {crop_id}")
        self.crop_id = crop_id


CROPS: dict[str, Crop] = {
    "tomato": Crop(
        # Kc, FAO-56 Table 12. Kc_ini 0.6 is the Solanum group row (the
        # tomato row leaves it blank): a choice, not a printed tomato value.
        kc_ini=0.6,
        # Table 12: Kc mid 1.15 (printed value).
        kc_mid=1.15,
        # Table 12: Kc end printed as the range 0.70-0.90; 0.80 is the middle
        # of that range (a choice).
        kc_end=0.80,
        # Table 11, tomato, Mediterranean: 30 / 40 / 45 / 30 days.
        stage_days=(30, 40, 45, 30),
        # Table 22: the range's lower end, 0.7 m (the table's note says
        # smaller values suit scheduling): a choice.
        root_depth_m=0.7,
        # Table 22: p = 0.40 (printed value, no ETc adjustment applied).
        p=0.40,
    ),
    "bell-pepper": Crop(
        # Table 12, Solanum group row for Kc_ini (the pepper row is blank): a choice.
        kc_ini=0.6,
        # Table 12: Kc mid 1.05 (printed value).
        kc_mid=1.05,
        # Table 12: Kc end 0.90 (printed value).
        kc_end=0.90,
        # Table 11, pepper, Europe and Mediterranean: 30 / 35 / 40 / 20 days.
        # The initial stage is printed "25/30"; read as 30 (a choice).
        stage_days=(30, 35, 40, 20),
        # Table 22: the range's lower end, 0.5 m (smaller suits scheduling): a choice.
        root_depth_m=0.5,
        # Table 22: p = 0.30 (printed value, no ETc adjustment applied).
        p=0.30,
    ),
}


def get_crop(crop_id: str) -> Crop:
    try:
        return CROPS[crop_id]
    except KeyError:
        raise UnknownCrop(crop_id) from None
