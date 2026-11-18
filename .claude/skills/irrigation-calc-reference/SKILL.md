---
name: irrigation-calc-reference
description: Use when writing, changing, reviewing or testing the irrigation numbers of planner-service (crop coefficient Kc, crop water use, soil bucket, irrigation depth, litres, run minutes), or when explaining them. Holds the formulas, the units, the stated approximations and three hand-calculated cases. Follow it exactly; never invent or adjust an irrigation number.
---

# irrigation-calc-reference

The single source of the planner's formulas. `services/planner-service/engine.py` follows this file, and every irrigation number in a plan comes from that engine. No AI model computes or adjusts an irrigation number (CLAUDE.md rule 12).

The research behind it, with the FAO-56 chapter or table for every claim, is `services/planner-service/docs/research/fao56.md`. The crop numbers are in `services/planner-service/crops.py` (provisional, pending the instructor's answers). FAO-56 means FAO Irrigation and Drainage Paper 56 (Allen et al., 1998).

## Method: single crop coefficient

`ETc = Kc × ET0` (FAO-56 Ch. 5, Eq. 56; Ch. 6, Eq. 58), with one Kc per day from the crop curve (Ch. 6). The dual coefficient (Kcb + Ke) and everything in Chapter 7 are out of scope: `weather-service` provides only ET0 and rain. This is an approximation; FAO-56 names the dual method as better suited to drip.

## Units

| Quantity | Unit |
|---|---|
| ET0, ETc, rain, depletion, bucket level, irrigation depth (`irrigation_mm`, internal: it is not in the plan) | mm of water, a depth |
| 1 mm of depth over 1 m² | 1 litre |
| `litres` | litres of water for the whole plot |
| Emitter flow `flow_lph` | litres per hour per emitter |
| `run_minutes` | minutes to run the system |
| Soil water capacity | mm of water per metre of soil depth (`available_water_mm_per_m`, the registry's soil value) |
| Root depth `Zr` | metres |
| Kc, `p` | dimensionless |

## Formulas

**1. Day number.** `i = (date − planting_date) in days + 1`, never less than 1 (the planting day is day 1; a planting date after the date counts as day 1).

**2. Kc for day `i`** (FAO-56 Ch. 6, Eq. 66). Stage lengths `L_ini, L_dev, L_mid, L_late` (days), values `Kc_ini, Kc_mid, Kc_end`:

| Day `i` | Kc |
|---|---|
| `i ≤ L_ini` | `Kc_ini` |
| `L_ini < i ≤ L_ini + L_dev` | `Kc_ini + (i − L_ini) / L_dev × (Kc_mid − Kc_ini)` |
| next `L_mid` days | `Kc_mid` |
| next `L_late` days, up to `i = L_ini + L_dev + L_mid + L_late` | `Kc_mid + (i − (L_ini + L_dev + L_mid)) / L_late × (Kc_end − Kc_mid)` |
| later days (a plot past its season) | `Kc_end` |

At the end of development `Kc = Kc_mid`; on the last day of the season `Kc = Kc_end`.

**3. Crop water use.** `ETc = Kc × ET0` (mm for the day).

**4. The bucket** (FAO-56 Ch. 8, Eq. 82 and 83).
`TAW = soil_mm_per_m × Zr` (mm; total available water, the bucket size).
`RAW = p × TAW` (mm; the part the crop can use before it is stressed).
The state is the depletion `Dr`: how many mm the bucket is below full. The level is `TAW − Dr`. Day 1 starts with `Dr = 0` (full; FAO-56 Eq. 87 note, assumption).

**5. One day** (Ch. 8, Eq. 85 and the rule `I ≤ Dr`), starting from `Dr_start` (the previous day's `Dr_end`):
1. `Dr_after_rain = max(0, Dr_start − rain)`. Water above full is lost.
2. If `Dr_after_rain + ETc > RAW`, the level would fall below the threshold today, so irrigate in the morning: `irrigation_mm = Dr_after_rain` (refill exactly the depletion, never more) and `Dr_end = ETc`.
   Otherwise `irrigation_mm = 0` and `Dr_end = Dr_after_rain + ETc`.
   Exactly at the threshold does not irrigate.
3. `Dr_end = min(Dr_end, TAW)` (Eq. 86). Report `bucket_mm = TAW − Dr_end`. `Dr_end` is the next day's `Dr_start`.

**6. From depth to litres and minutes.**
`litres = irrigation_mm × area_m2`.
Each emitter serves `row_spacing_m × emitter_spacing_m` m². So `run_minutes = irrigation_mm × row_spacing_m × emitter_spacing_m ÷ flow_lph × 60`. The plot area cancels: it affects litres, not minutes.

**7. Rounding.** Compute everything in full precision. Round only in the response: 2 decimals for `et0_mm`, `litres`, `run_minutes`, `bucket_mm`; 3 decimals for `kc`. `irrigation_mm` is internal and is not returned. Never round between days.

## Stated approximations

- Single Kc (no soil-evaporation split, no cover fraction).
- No climate adjustment of `Kc_mid` and `Kc_end` (FAO-56 Eq. 62 and 65 need wind and humidity).
- No wetted-fraction (`fw`) adjustment of `Kc_ini` for drip (FAO-56 Eq. 60); it affects only the first weeks after planting.
- No drip application-efficiency factor: net depth and applied depth are the same (the course's worked example: `litres` is exactly depth × area).
- All forecast rain counts (no 0.2 × ET0 threshold, no runoff).
- The bucket is full at the start of the plan, because the planner has no irrigation history.
- A plot past its season keeps `Kc_end`.
- `Zr` is fixed for the whole season; FAO's adjustment of `p` for ETc and for soil texture is not applied.
- Each emitter serves `row_spacing × emitter_spacing` m². This is not from FAO-56; the course's worked example confirms it (1000 m², rows 1.5 m, emitters 0.4 m, 1.0 L/h, 6900 L → 248 minutes).

## Crop values (provisional; `crops.py` is the source of truth)

| Crop | `Kc_ini` | `Kc_mid` | `Kc_end` | Stage days (ini / dev / mid / late) | `Zr` | `p` |
|---|---|---|---|---|---|---|
| `tomato` | 0.6 | 1.15 | 0.80 | 30 / 40 / 45 / 30 | 0.7 m | 0.40 |
| `bell-pepper` | 0.6 | 1.05 | 0.90 | 30 / 35 / 40 / 20 | 0.5 m | 0.30 |

Soils (registry catalogue, mm of water per metre): sand 83, loam 175, clay-loam 200.

## Three hand-calculated cases

The inputs are fixed here. The expected results are the learner's own hand calculations, day by day, re-checked independently, and the engine's tests use them (accuracy within 0.5%). The same data is in `services/planner-service/tests/cases.py`. Never edit an expected value to make the engine pass: if the engine and a hand result differ, find which one is wrong.

All three: forecast of 7 days starting on the start date, `stale` false.

### Case 1: tomato in mid-season, with irrigation

- Crop `tomato`, soil sand (83 mm/m), so `TAW = 58.1`, `RAW = 23.24`.
- Planting 2026-08-01, start date 2026-10-20 (day number 81, in the mid stage).
- Area 1000 m², row spacing 1.5 m, emitter spacing 0.4 m, flow 2.0 L/h.
- ET0 per day: 5.0, 5.5, 6.0, 6.0, 5.5, 5.0, 5.0. Rain 0 every day.

Expected results (the learner's hand calculation; the day number is in the first column):

| Day | Date | `kc` | `et0_mm` | rain | `irrigation_mm` | `litres` | `run_minutes` | `bucket_mm` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 81 | 2026-10-20 | 1.15 | 5.0 | 0 | 0 | 0 | 0 | 52.35 |
| 82 | 2026-10-21 | 1.15 | 5.5 | 0 | 0 | 0 | 0 | 46.025 |
| 83 | 2026-10-22 | 1.15 | 6.0 | 0 | 0 | 0 | 0 | 39.125 |
| 84 | 2026-10-23 | 1.15 | 6.0 | 0 | 18.975 | 18975 | 341.55 | 51.2 |
| 85 | 2026-10-24 | 1.15 | 5.5 | 0 | 0 | 0 | 0 | 44.875 |
| 86 | 2026-10-25 | 1.15 | 5.0 | 0 | 0 | 0 | 0 | 39.125 |
| 87 | 2026-10-26 | 1.15 | 5.0 | 0 | 18.975 | 18975 | 341.55 | 52.35 |


### Case 2: rain delays an irrigation

- Same as Case 1, but rain 10.0 mm on day 3 and 0 on every other day.

Expected results (the learner's hand calculation):

| Day | Date | `kc` | `et0_mm` | rain | `irrigation_mm` | `litres` | `run_minutes` | `bucket_mm` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 81 | 2026-10-20 | 1.15 | 5.0 | 0 | 0 | 0 | 0 | 52.35 |
| 82 | 2026-10-21 | 1.15 | 5.5 | 0 | 0 | 0 | 0 | 46.025 |
| 83 | 2026-10-22 | 1.15 | 6.0 | 10 | 0 | 0 | 0 | 49.125 |
| 84 | 2026-10-23 | 1.15 | 6.0 | 0 | 0 | 0 | 0 | 42.225 |
| 85 | 2026-10-24 | 1.15 | 5.5 | 0 | 0 | 0 | 0 | 35.9 |
| 86 | 2026-10-25 | 1.15 | 5.0 | 0 | 22.2 | 22200 | 399.6 | 52.35 |
| 87 | 2026-10-26 | 1.15 | 5.0 | 0 | 0 | 0 | 0 | 46.6 |

Rain on day 3 refills the bucket, which delays the first irrigation from day 84 (as in Case 1) to day 86, and then the refill is 22.2 mm.


### Case 3: bell pepper in the development stage

- Crop `bell-pepper`, soil sand (83 mm/m), so `TAW = 41.5`, `RAW = 12.45`.
- Planting 2026-09-20, start date 2026-10-25 (day number 36, in the development stage, so Kc is between `Kc_ini` and `Kc_mid` and changes every day).
- Area 400 m², row spacing 1.2 m, emitter spacing 0.3 m, flow 2.0 L/h.
- ET0 4.0 every day. Rain 0 every day.

Expected results (the learner's hand calculation; Kc is `0.6 + (i − 30) ÷ 35 × 0.45` for day number `i`, rising by 0.0128571429 a day):

| Day | Date | `kc` | `et0_mm` | rain | `irrigation_mm` | `litres` | `run_minutes` | `bucket_mm` |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 36 | 2026-10-25 | 0.6771428571 | 4.0 | 0 | 0 | 0 | 0 | 38.79142857 |
| 37 | 2026-10-26 | 0.69 | 4.0 | 0 | 0 | 0 | 0 | 36.03142857 |
| 38 | 2026-10-27 | 0.7028571429 | 4.0 | 0 | 0 | 0 | 0 | 33.22 |
| 39 | 2026-10-28 | 0.7157142857 | 4.0 | 0 | 0 | 0 | 0 | 30.35714286 |
| 40 | 2026-10-29 | 0.7285714286 | 4.0 | 0 | 11.14285714 | 4457.142857 | 120.3428571 | 38.58571429 |
| 41 | 2026-10-30 | 0.7414285714 | 4.0 | 0 | 0 | 0 | 0 | 35.62 |
| 42 | 2026-10-31 | 0.7542857143 | 4.0 | 0 | 0 | 0 | 0 | 32.60285714 |

