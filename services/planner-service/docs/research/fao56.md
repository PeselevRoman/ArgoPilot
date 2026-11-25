# FAO-56 research note: daily drip-irrigation planner for tomato and bell pepper

Source: FAO Irrigation and Drainage Paper 56 (Allen, Pereira, Raes, Smith, 1998), fetched from fao.org (URLs in "Sources"). Scope: Chapters 5, 6, 8, Annex 8, plus the Chapter 7 tables that the scope items point to (Table 17, Table 19, Table 20, Eq. 75). Equation images (GIFs) were read directly from fao.org. Anything computed by the note author is marked "derived". Terms are defined on first use.

## Summary

- Daily crop water need is `ETc = Kc x ETo`. ETo (reference evapotranspiration) is the water use of a standard well-watered grass surface. Kc (crop coefficient) is a dimensionless ratio that depends on crop and growth stage (FAO-56, Ch. 5, Eq. 56; Ch. 6, Eq. 58).
- Kc follows a curve built from three values (Kc ini, Kc mid, Kc end) and four stage lengths, joined by straight lines (FAO-56, Ch. 6, "Construction of the Kc curve"; Eq. 66).
- The soil is a "bucket" (the root zone). Its capacity is TAW, the stress threshold is RAW = p x TAW, and the daily state is the depletion Dr. Irrigation is triggered when Dr reaches RAW, and the net depth is at most Dr, so nothing percolates (FAO-56, Ch. 8, Eq. 82, 83, 85, 88).
- Water stress scales ET by Ks, which is 1 while Dr <= RAW and falls linearly to 0 at Dr = TAW (FAO-56, Ch. 8, Eq. 84).
- The source recommends the dual coefficient (Kcb + Ke) for micro-irrigation such as drip (FAO-56, Ch. 5, Table 10). Annex 8 is a worked daily spreadsheet using that dual method. The single-Kc approach in Ch. 6 is the "time-averaged" simplification.

## 1. From ETo and Kc to crop water need, and drip irrigation

**ETc under standard conditions.** `ETc = Kc ETo`, in mm/day (FAO-56, Ch. 5, Eq. 56; repeated as Eq. 58 in Ch. 6). "Standard conditions" means crops grown in large fields under excellent agronomic and soil water conditions, with no limit from water shortage, density, disease, weeds, insects or salinity. ETc is then "the upper envelope of crop evapotranspiration" (FAO-56, Ch. 5, "Crop coefficient approach"). When something does limit ET, the result is corrected to `ETc adj` (FAO-56, Ch. 5, same section; Part C).

**What Kc contains.** Kc integrates four differences from reference grass: crop height, albedo of the crop-soil surface, canopy resistance, and evaporation from soil (FAO-56, Ch. 5, "Crop coefficient approach"). Climate effects are mostly inside ETo, so Kc "varies predominately with the specific crop characteristics" and standard values can be transferred between locations (FAO-56, Ch. 5).

**Single versus dual coefficient.**
- Single Kc: soil evaporation and transpiration are combined into one time-averaged Kc. The source says it is used for weekly or longer periods "although calculations may proceed on a daily time step", and that it suits surface and set sprinkler systems with intervals of several days (FAO-56, Ch. 5, "Single crop coefficient approach").
- Dual: `Kc = Kcb + Ke` (FAO-56, Ch. 5, Eq. 57). Kcb is the basal coefficient (transpiration, dry soil surface, adequate root-zone water). Ke is the soil evaporation coefficient, large after wetting and falling to 0 as the surface dries. Kcb + Ke cannot exceed Kc max (FAO-56, Ch. 5).
- Table 10 lists "irrigation scheduling for high frequency water application (microirrigation and automated sprinkler irrigation)" and "real time irrigation scheduling" under the dual column, and "basic irrigation schedules" and "irrigation management" under single (FAO-56, Ch. 5, Table 10). The dual method needs daily data and a computer (same table).

**Net irrigation need.** The source never writes the formula "net irrigation = ETc - effective rain" as a stand-alone equation in Ch. 5, 6 or 8. The same idea is implemented through the root-zone balance: rain and irrigation reduce depletion, ETc increases it (FAO-56, Ch. 8, Eq. 85). Ch. 8 states "Irrigation is required when rainfall is insufficient to compensate for the water lost by evapotranspiration", and sets the net irrigation depth limit `Ii <= Dr,i` (FAO-56, Ch. 8, "Forecasting or allocating irrigations"). "Effective rainfall" is not defined in these chapters. Ch. 8 only says daily rain below about 0.2 ETo "is normally entirely evaporated and can usually be ignored" (FAO-56, Ch. 8, "Precipitation (P), runoff (RO) and irrigation (I)").

**Drip / localized irrigation passages.**
- Wetted fraction fw: "for a trickle irrigation system, the fraction of the surface wetted, fw, may be only 0.4" (FAO-56, Ch. 6, "Adjustment for partial wetting by irrigation"). Table 20: Trickle irrigation fw = "0.3... 0.4"; precipitation, sprinkler, basin and border = 1.0 (FAO-56, Ch. 7, Table 20).
- Kc ini with partial wetting: `Kc ini = fw x Kc ini (Table or Fig.)` (FAO-56, Ch. 6, Eq. 60). The infiltrated depth used to choose Fig. 29 vs Fig. 30 is `Iw = I / fw` (FAO-56, Ch. 6, Eq. 61), where I is the depth over the whole field. Where rain and irrigation both occur, fw is the average weighted by infiltrated depth (same section).
- Worked example: trickle, every 2 days, 12 mm over the field, fw = 0.4, ETo = 4 mm/day gives Iw = 30 mm, Kc ini = 1.05 by Eq. 59, 0.4 x 1.05 = 0.42, ETc = 1.7 mm/day (FAO-56, Ch. 6, Example 26).
- The source gives this adjustment only for the initial stage. For Kc mid, Ch. 6 gives no fw factor. It does say that where irrigation is more frequent than every 3 days and the tabulated Kc mid is below 1.0, Kc mid "can be replaced by approximately 1.1-1.3" (especially if fw > 0.3) (FAO-56, Ch. 6, "Adjustment for frequency of wetting"). Not applicable to pepper (1.05) or tomato (1.15), whose values already exceed 1.0.
- Dual method and drip: `few = min(1 - fc, fw)` (FAO-56, Ch. 7, Eq. 75), where fc is the fraction of soil covered by vegetation. The source notes that for drip "the majority of soil wetted... may be beneath the canopy" and that fw "may need to be reduced to about one-half to one-third of that given in Table 20", with a general approach `fw x [1 - (2/3) fc]` (FAO-56, Ch. 7, "few: calculation procedure"). Note this is Ch. 7, outside the stated scope, but it is the only drip-specific rule for later stages.
- Table 12 footnote 16 allows -0.10 on Kc for pineapple under drip beneath plastic mulch. It is crop-specific, not a general drip rule (FAO-56, Ch. 6, Table 12, fn 16).

## 2. Tomato and bell pepper: Kc, stages, height, roots, depletion

### 2.1 Table 12 (single Kc) and Table 17 (basal Kcb), values as printed

Table 12, "Single (time-averaged) crop coefficients, Kc, and mean maximum plant heights for non stressed, well-managed crops in subhumid climates (RHmin ~ 45%, u2 ~ 2 m/s)" (FAO-56, Ch. 6, Table 12):

| Row | Kc ini | Kc mid | Kc end | Max. height h (m) |
|---|---|---|---|---|
| b. Solanum family (group row) | 0.6 | 1.15 | 0.80 | (blank) |
| Sweet Peppers (bell) | (blank) | 1.05 (fn 2) | 0.90 | 0.7 |
| Tomato | (blank) | 1.15 (fn 2) | 0.70-0.90 | 0.6 |

- Kc ini is printed only on the group row, so 0.6 applies to both crops. The group row also prints 1.15 and 0.80, which are not the pepper or tomato values (FAO-56, Ch. 6, Table 12). The "Kc ini" column carries footnote 1 (the footnote text says these are "general values for Kc ini under typical irrigation management"; the footnote marker sits on the column heading image, so the link is inferred).
- Footnote 1: "For frequent wettings such as with high frequency sprinkle irrigation or daily rainfall, these values may increase substantially and may approach 1.0 to 1.2. Kc ini ... is more accurately estimated using Figures 29 and 30, or Equation 7-3 in Annex 7, or using the dual Kcb ini + Ke." (FAO-56, Ch. 6, Table 12, fn 1).
- Footnote 2: "Beans, Peas, Legumes, Tomatoes, Peppers and Cucumbers are sometimes grown on stalks reaching 1.5 to 2 meters in height. In such cases, increased Kc values need to be taken. For green beans, peppers and cucumbers, 1.15 can be taken, and for tomatoes, dry beans and peas, 1.20. Under these conditions h should be increased also." (FAO-56, Ch. 6, Table 12, fn 2; the source prints "stalks", likely meaning stakes).
- Tomato Kc end is a range, "0.70-0.90", with no rule printed for choosing within it.

Table 17, "Basal crop coefficients, Kcb" (dual approach; same climate basis) (FAO-56, Ch. 7, Table 17):

| Row | Kcb ini | Kcb mid | Kcb end |
|---|---|---|---|
| b. Solanum family (group row) | 0.15 | 1.10 | 0.70 |
| Sweet Peppers (bell) | (blank) | 1.00 (fn 2) | 0.80 |
| Tomato | (blank) | 1.10 (fn 2) | 0.60-0.80 |

- Table 17 footnote 1: values "represent conditions having a dry soil surface... intended for use with the dual Kcb ini + Ke approach, only." Footnote 2 is the same stalks note with Kcb values 1.10 (peppers) and 1.15 (tomatoes) (FAO-56, Ch. 7, Table 17, fn 1-2).

### 2.2 Stage lengths, Table 11 (days), as printed

Columns: Init (Lini), Dev (Ldev), Mid (Lmid), Late (Llate), Total, Plant date, Region (FAO-56, Ch. 6, Table 11).

| Crop | Lini | Ldev | Lmid | Llate | Total | Plant date | Region |
|---|---|---|---|---|---|---|---|
| Sweet peppers (bell) | 25/30 | 35 | 40 | 20 | 125 | April/June | Europe and Medit. |
| Sweet peppers (bell) | 30 | 40 | 110 | 30 | 210 | October | Arid Region |
| Tomato | 30 | 40 | 40 | 25 | 135 | January | Arid Region |
| Tomato | 35 | 40 | 50 | 30 | 155 | Apr/May | Calif., USA |
| Tomato | 25 | 40 | 60 | 30 | 155 | Jan | Calif. Desert, USA |
| Tomato | 35 | 45 | 70 | 30 | 180 | Oct/Nov | Arid Region |
| Tomato | 30 | 40 | 45 | 30 | 145 | April/May | Mediterranean |

- Table 11 footnote *: lengths "are indicative of general conditions, but may vary substantially from region to region, with climate and cropping conditions, and with crop variety. The user is strongly encouraged to obtain appropriate local information." The text adds the values are "only a general guide" (FAO-56, Ch. 6, Table 11 and "Length of growth stages").
- The pepper row "25/30" has two initial values with one total (125, which matches 30+35+40+20; derived). The source does not explain the slash.
- The first pepper row total (125) and all tomato totals equal the sum of the four stages (derived check).

### 2.3 Maximum root depth and depletion fraction p, Table 22

Table 22, "Ranges of maximum effective rooting depth (Zr), and soil water depletion fraction for no stress (p), for common crops" (FAO-56, Ch. 8, Table 22):

| Crop | Max root depth Zr (m) (fn 1) | p (fn 2, for ETc ~ 5 mm/day) |
|---|---|---|
| Sweet Peppers (bell) | 0.5-1.0 | 0.30 |
| Tomato | 0.7-1.5 | 0.40 |

- Footnote 1: "The larger values for Zr are for soils having no significant layering or other characteristics that can restrict rooting depth. The smaller values for Zr may be used for irrigation scheduling and the larger values for modeling soil water stress or for rainfed conditions."
- Footnote 2: p applies for ETc ~ 5 mm/day and is adjusted by `p = p(Table 22) + 0.04 (5 - ETc)`, ETc in mm/day (FAO-56, Ch. 8, Table 22 fn 2; "Readily available water"). The adjusted p is limited to `0.1 <= p <= 0.8` (same section).
- Soil texture: for fine textured soils the Table 22 p "can be reduced by 5-10%", for coarse soils "increased by 5-10%" (FAO-56, Ch. 8, "Readily available water (RAW)").
- Example 36 uses Zr ~ 0.8 m and p = 0.40 for tomato (FAO-56, Ch. 8, Example 36).

### 2.4 Climate adjustment of Kc mid and Kc end (Ch. 6)

Table 12 values are for a "sub-humid climate with average daytime minimum relative humidity (RHmin) ~ 45% and ... wind speeds averaging 2 m/s" (FAO-56, Ch. 5, "Climate"). RHmin is the daily minimum relative humidity. u2 is wind speed at 2 m height.

- Kc mid: `Kc mid = Kc mid(Tab) + [0.04 (u2 - 2) - 0.004 (RHmin - 45)] (h/3)^0.3` (FAO-56, Ch. 6, Eq. 62). Limits: 1 <= u2 <= 6 m/s (mid-season mean), 20 <= RHmin <= 80 % (mid-season mean), 0.1 < h < 10 m (mean height in mid-season).
- Kc end: same bracket and (h/3)^0.3 term added to Kc end(Tab) (FAO-56, Ch. 6, Eq. 65), using late-season means of u2 and RHmin. It "is only applied when the tabulated values for Kc end exceed 0.45"; below 0.45 no adjustment (FAO-56, Ch. 6, text after Eq. 65). Both tomato and pepper Kc end exceed 0.45, so it applies.
- The source says the equation is "not strongly sensitive": "changing 0.04 per 1 m/s change in u2 and per 10% change in RHmin for a 3 m tall crop" (FAO-56, Ch. 6, after Eq. 64).
- RHmin from dewpoint: `RHmin = 100 e0(Tdew) / e0(Tmax)` (FAO-56, Ch. 6, Eq. 63). When dewpoint is unavailable use Tmin in place of Tdew: `RHmin = 100 e0(Tmin) / e0(Tmax)` (FAO-56, Ch. 6, Eq. 64). In arid and semi-arid climates subtract 2 degC from Tmin first (Ch. 6 footnote citing Annex 6, Eq. 6-6). Without data, use Table 15 (wind) and Table 16 (RHmin by climate: arid 20, semi-arid 30, sub-humid 45, humid 70, very humid 80) (FAO-56, Ch. 6).
- Derived illustration, not from the source: tomato with h = 0.6, u2 = 3, RHmin = 35 gives (0.04 x 1 - 0.004 x (-10)) x (0.2)^0.3 = 0.08 x 0.617 = about 0.049, so Kc mid about 1.20. Verify this against the equation before relying on it.

### 2.5 Kc ini from wetting events (Ch. 5 and 6)

- Kc ini is high when the soil is wet from irrigation or rain and low when dry. It depends on wetting interval, ETo and wetting depth (FAO-56, Ch. 6, "Crop coefficient for the initial stage"). It "can vary between 0.1 and 1.15".
- Table 9 (medium wetting events 10-40 mm, medium textured soil): weekly wetting gives 0.8 / 0.6 / 0.4 / 0.3 for ETo low (1-3), moderate (3-5), high (5-7), very high (>7 mm/day); "less than weekly" gives ranges 1.2-0.8, 1.1-0.6, 1.0-0.4, 0.9-0.3 (FAO-56, Ch. 5, Table 9). The "longer than once per week" row has footnote (*) that intervals may be too large for full transpiration.
- Light wetting (<= 10 mm per event; rain, micro-irrigation, centre pivot): use Fig. 29 for all soil types (FAO-56, Ch. 6, "Light wetting events"). Heavy (>= 40 mm): Fig. 30a (coarse) or 30b (fine and medium) (FAO-56, Ch. 6). In between: `Kc ini = Kc ini(Fig.29) + [(I - 10)/(40 - 10)] [Kc ini(Fig.30) - Kc ini(Fig.29)]` (FAO-56, Ch. 6, Eq. 59, as printed in Example 25). Then multiply by fw (Eq. 60, Section 1).
- The figure curves are graphs. They were not digitized here; only the example read-offs above (Examples 24-26) are verified. Annex 7 (Eq. 7-3 numerical procedure) was not read in detail.
- Classification of rain depths: very light <= 3 mm, light 5 mm, medium >= 10 mm, heavy >= 40 mm (FAO-56, Ch. 6, Table 13).

### 2.6 Kc curve construction (Ch. 5 and 6)

- Growth stages: initial (planting to ~10% ground cover), development (10% to effective full cover), mid-season (full cover to start of maturity), late season (maturity to harvest) (FAO-56, Ch. 5, "Crop growth stages").
- Three steps: choose stage lengths and the three Kc values; adjust for wetting frequency and climate; "construct a curve by connecting straight line segments through each of the four growth stages", with horizontal lines through Kc ini (initial) and Kc mid (mid-season), a diagonal from Kc ini to Kc mid across development, and from Kc mid to Kc end across the late season (FAO-56, Ch. 6, "Annual crops"; Fig. 25, Fig. 34).
- Numerical form: `Kc,i = Kc,prev + [(i - sum(Lprev)) / Lstage] (Kc,next - Kc,prev)`. In initial and mid-season Kc is constant at the stage value. In development and late season it is linear between the previous and next stage values (FAO-56, Ch. 6, Eq. 66). Here i is the day number within the season.
- ETc is the product of the daily Kc and ETo (FAO-56, Ch. 6, "Calculating ETc").
- Example: dry beans, Kc values 0.15, 1.19, 0.35 and stage lengths 25, 25, 30, 20 (FAO-56, Ch. 6, Box 15).

## 3. The soil bucket (Ch. 8)

Definitions (FAO-56, Ch. 8, "Total available water (TAW)"):
- Field capacity (FC): water a well-drained soil holds against gravity, "the amount of water remaining when downward drainage has markedly decreased". Wilting point (WP): "the water content at which plants will permanently wilt". Water contents theta are in m3/m3.
- Root-zone depletion Dr: "water shortage relative to field capacity", so Dr = 0 at field capacity (FAO-56, Ch. 8, "Water stress coefficient (Ks)").

Equations (FAO-56, Ch. 8):
- Eq. 82: `TAW = 1000 (theta_FC - theta_WP) Zr` (mm; Zr in m). Typical theta values per soil: Table 19 (FAO-56, Ch. 7, Table 19), e.g. loam FC 0.20-0.30, WP 0.07-0.17, (FC-WP) 0.13-0.18; sandy loam FC 0.18-0.28, WP 0.06-0.16. Only the rows above were verified from the text extract; the table has more soil types.
- Eq. 83: `RAW = p TAW`. Stress begins when `Dr > RAW`. p "normally varies from 0.30 for shallow rooted plants at high rates of ETc (> 8 mm d-1) to 0.70 for deep rooted plants at low rates of ETc (< 3 mm d-1)"; 0.50 is commonly used.
- Eq. 84: for `Dr > RAW`, `Ks = (TAW - Dr) / ((1 - p) TAW) = (TAW - Dr) / (TAW - RAW)`. For `Dr <= RAW`, Ks = 1.
- Eq. 80 (dual): `ETc adj = (Ks Kcb + Ke) ETo`. Eq. 81 (single): `ETc adj = Ks Kc ETo`. The source says Eq. 80 is "generally more valid" because Ks affects only transpiration, but Eq. 81 "will provide reasonable results" where soil evaporation is small.
- Eq. 85 (daily balance, end of day i): `Dr,i = Dr,i-1 - (P - RO)i - Ii - CRi + ETc,i + DPi`. P = precipitation, RO = runoff, I = net irrigation depth that infiltrates, CR = capillary rise, DP = deep percolation, all mm.
- Eq. 86: `0 <= Dr,i <= TAW`.
- Eq. 87 (initial depletion): `Dr,i-1 = 1000 (theta_FC - theta_i-1) Zr`, with theta the average root-zone water content. "Following heavy rain or irrigation, the user can assume that the root zone is near field capacity, i.e., Dr,i-1 ~ 0."
- Eq. 88 (deep percolation): after heavy rain or irrigation, `DPi = (Pi - ROi) + Ii - ETc,i - Dr,i-1 >= 0`. While Dr,i > 0, "the soil will not drain and DPi = 0". Water above field capacity is assumed lost the same day, after that day's ET.
- Simplifications stated: CR "can normally be assumed to be zero when the water table is more than about 1 m below the bottom of the root zone"; runoff is predicted with standard hydrology methods and is not given (FAO-56, Ch. 8, "Soil water balance").
- Irrigation rules: irrigate "before or at the moment when the readily available soil water is depleted (Dr,i <= RAW)"; to avoid deep percolation "the net irrigation depth should be smaller than or equal to the root zone depletion (Ii <= Dr,i)" (FAO-56, Ch. 8, "Forecasting or allocating irrigations").
- Growing root zone: when Zr grows, the new subsoil water content must be accounted for, `Dr,i = Dr,i-1 + 1000 (theta_FC - theta_sub,i-1) dZr` (as printed in Example 38 footnote 5; the example assumes the subsoil is at field capacity).
- Worked example, Ks only: tomato, Zr = 0.8 m, p = 0.40, theta_FC 0.32, theta_WP 0.12, TAW = 160 mm, RAW = 64 mm, initial Dr = 55 mm, ETo = 5, Kc = 1.2, no rain or irrigation, 10 days. Dr at end of day 1 and 2 = 61.0 and 67.0; Ks on day 3 = 0.97; day 10 Ks = 0.62 and end Dr = 104.5 (FAO-56, Ch. 8, Example 37).
- Worked example, RAW: tomato with Zr = 0.8 m gives TAW 72 / 136 / 96 mm and RAW 29 / 54 / 38 mm on loamy sand / silt / silty clay (FAO-56, Ch. 8, Example 36).

## 4. Annex 8: day-by-day scheduling

Annex 8 is a spreadsheet (Fig. 8.1, formulas in Box 8.1) for dry edible beans using the dual method of Ch. 7. It is a verification example, "intended only to demonstrate how to apply the soil evaporation equations during scheduling of irrigations. The procedure ... and the assumptions used may not always be appropriate" (FAO-56, Annex 8, closing text). Column letters below are from Box 8.1. Box 8.1 was converted from HTML and has visible typos (e.g., "L14", "AU 5"), and the equation labels are not cleanly aligned to cells, so equation numbers below are taken from the annex footnotes where stated and otherwise marked "per Box 8.1 label".

**Inputs** (boxed cells; FAO-56, Annex 8, Box 8.1 and Fig. 8.1): plant date 22 May; Lini 25, Ldev 25, Lmid 30, Llate 20; Kcb ini 0.15, Kcb mid 1.10, Kcb end 0.25 (Table 17); max height 0.4 m; Kc min 0.15; fw (irrigation) 0.5; REW 8 mm; TEW 22 mm; initial De 18 mm; initial fw 1; Rootmin 0.2 m; Rootmax 0.8 m; available water 160 mm/m; MAD 70% during the initial stage and 45% afterwards. Daily inputs: Tmax, u2, Tdew, ETo, and P - RO. REW and TEW are the readily and total evaporable water of the top soil layer (Ch. 7, Table 19), used for Ke.

**Assumptions** (FAO-56, Annex 8, intro): all irrigation and rain occur early in the morning; the decision to irrigate is based on depletion at the end of the previous day; all drainage from excess rain happens the day of the rain; runoff is zero; the net irrigation depth retained equals exactly the previous day's depletion ("perfect knowledge... or that all irrigations are adequate or excessive"); p equals MAD (footnote 11).

**Order of calculation, one row per day** (FAO-56, Annex 8, Box 8.1 and footnotes):
1. Date to day of year J. Climate inputs give RHmin from Tdew and Tmax (Eq. 63; columns I, J, K).
2. Kcb(J): constant at Kcb ini before Jdev; linear from Kcb ini to adjusted Kcb mid across development; constant through mid-season; linear from Kcb mid to adjusted Kcb end across the late season (Eq. 66 per footnote 2; column O). Kcb mid and Kcb end are adjusted with the Eq. 62-type correction using mid-season average u2 and RHmin (Box 8.1 label "Eq. 70", Ch. 7; cells J5 and J6; Kcb end is only adjusted if >= 0.45). Result: 1.10 becomes 1.13 and 0.25 becomes 0.23 (FAO-56, Annex 8, Fig. 8.1: u2 1.98 m/s, RHmin 29%).
3. Crop height proportional to Kcb/Kcb mid times max height, never decreasing (footnote 3; column P). Kc max from the Ch. 7 formula (Eq. 72, column Q).
4. Wet-soil evaporation, using the Ch. 7 equations: fc (Eq. 76, S), fw from the last wetting (footnote 5, T), few = min(1 - fc, fw) (Eq. 75, U), Kr (Eq. 74, W), Ke = min(Kr (Kc max - Kcb), few Kc max) (Eq. 71, X), E = Ke ETo (Y), evaporation-layer depletion De (Eq. 77, AA) and its drainage DPe (Eq. 79, Z). The depletion De at the start of the day is the previous day's end value less rain and irrigation, floored at 0 (footnote 6).
5. Kc = Kcb + Ke and ETc = Kc ETo (Eq. 69; AB, AC; footnote 7). This is the unstressed ETc.
6. Root depth: `Zr,i = Zr min + (Zr max - Zr min) (Kcb,i - Kcb ini) / (Kcb mid - Kcb ini)` for J < Jmid, and `Zr max` for J >= Jmid (Annex Eq. 8-1, 8-2; AE). Roots never shrink (footnote 8). The annex also gives a time-based alternative, `Zr min + (Zr max - Zr min)(J - Jstart)/(Jmax - Jstart)` (Annex Eq. 8-3), and says Zr min for annuals "can be estimated as 0.15 to 0.20 m".
7. RAW = MAD x Zr x available water (mm/m), with MAD = 70% in the initial stage and 45% after (column AF; MAD used as p; Eq. 83 and footnote 10). Cell AF never decreases day to day (MAX with previous row).
8. First-estimate depletion (AG): `Dr = Dr,prev end - (P - RO) - I(prev-day decision) + ETc` using Eq. 85 with drainage = 0 and unstressed ETc (footnote 9; column AG).
9. Irrigation trigger (AH): if the day is within the irrigation window (from planting up to the midpoint of the late season, "no irrigation... during the last one-half of the late-season period") and `AG > RAW`, then net irrigation needed = AG; otherwise 0 (footnote 10; Box 8.1, AH formula). "Irrigation that is needed is presumed applied at the beginning of the next day" (FAO-56, Annex 8, Fig. 8.1 header). The depth is divided by fw for the evaporation calculation (R, footnote 4), so the wetted-area depth is I/fw.
10. Deep percolation (AI), per Box 8.1 label Eq. 88: `max(P - RO + I(applied) - ETc - Dr,prev, 0)`.
11. Ks (AJ): if AG > RAW, `Ks = (TAW - AG) / (TAW - RAW)` where TAW = Zr x available water; else 1 (Eq. 84; footnote 11).
12. Adjusted Kc (AK): `Ks Kcb + Ke` (Eq. 80). Corrected ending depletion (AL): previous corrected depletion minus rain minus irrigation, plus Kc adj x ETo, plus DP (Eq. 85 again, footnote 9). Cumulative wind and RHmin (AO, AP) accumulate for the mid-season averages.

**Printed worked numbers, first irrigation** (FAO-56, Annex 8, Fig. 8.1, rows 14-26; read from the figure image):
- 15 May (row 14, J = 135): Zr = 0.20 m, RAW = 22.4 mm, ending depletion 19.6 mm, Ks 1.00, Kc adj 0.46.
- Row 21 (J = 142, the 22 May date; the figure's first irrigation): ending depletion 25.3 mm exceeds RAW 22.4 mm, so Net irrigation needed = 25.3 mm. Ks that day = 0.70, Kc adj 0.23, corrected ending depletion 25.1 mm.
- Next day: net irrigation / fw = 50.6 mm (= 25.3 / 0.5, derived check), evaporation-layer deep percolation DPe = 29.67 mm, depletion falls to 3.7 mm, Ks = 1.00, Kc adj 0.76.
- "Small amount of stress on the day prior to irrigation" is expected because irrigation waits until depletion has exceeded RAW the previous day (FAO-56, Annex 8, text).

**Deep percolation handling.** Any excess water over the depletion, from rain or irrigation, is removed the same day (Eq. 88). Because the irrigation depth equals the previous depletion, the spreadsheet generally yields DP = 0 for irrigation days and positive DP only from excess rain (FAO-56, Annex 8, assumptions; Fig. 8.1 column AI is blank in the rows read). The printed rows read here show no root-zone DP value.

## Gaps and caveats

**Not verified or not fully read**
- Equation images were read as pictures (Eq. 59, 61, 62, 64, 65, 66, 84, Annex 8-1, 8-3). Eq. 60 and Eq. 63 were not opened as images; their forms are taken from the page text (Eq. 60) and from the Annex 8 spreadsheet formula and Ch. 6 text (Eq. 63). All other equation numbers are from the page text. Fig. 29, Fig. 30, Fig. 32 (additive Kc mid adjustment chart), Fig. 41, 42 curves are images and were not digitized.
- Annex 7 (Eq. 7-3 for Kc ini) and Chapter 7 beyond Tables 17, 19, 20 and Eq. 75 were not read. The Ch. 7 equations quoted in step 4 of Annex 8 (Eq. 69-79) are identified only by Box 8.1 labels and cell formulas, not by reading Ch. 7. Eq. 70 is attributed to the Kcb mid correction by the Annex 8 text ("using Equation 70 of Chapter 7"), not verified in Ch. 7.
- Only the first 13 data rows of Fig. 8.1 were viewed. The annex text refers to the last irrigation on day 225 and the full season, but later rows were not read.
- Table 19: only the rows through "Silt" were extracted from the text conversion; clay-type rows were not recorded.
- The source has no explicit stand-alone "net irrigation requirement = ETc - effective rain" formula in the chapters in scope, and does not define effective rainfall (see Section 1).
- The Table 11 "25/30" slash and the Table 12 Kc ini footnote marker are not explained in the text.

**Outdated or in tension with later FAO guidance (author knowledge, not verified in the source)**
- The source dates from 1998. It was not compared here with later FAO work (for example FAO Irrigation and Drainage Paper 66 for Aquacrop, or updated Kc tables by Pereira et al. 2021). Treat any claim that newer tables supersede Table 12 or 17 as unverified until checked.
- The source itself says Table 12 values are "only approximations", that Kc ini "should always" be refined, and that local stage lengths should replace Table 11 (FAO-56, Ch. 6, Table 12 text and Table 11 text).
- Tension inside the source: Ch. 5 Table 10 puts drip in the dual (Kcb + Ke) column, while Ch. 6 provides the single-Kc approach with an fw correction only for Kc ini. A drip planner using single Kc must choose how to handle Kc during development, mid-season and late season, because the chapter gives no rule for it.

**Implementer decisions (not settled by the source)**
- Single Kc (Ch. 6) versus dual (Ch. 7 plus Annex 8) for drip. Source says dual for high-frequency micro-irrigation (Table 10).
- Which stage-length row to use from Table 11, and whether to replace it with local data; the pepper "25/30" initial value.
- Tomato Kc end within 0.70-0.90 (Kcb end 0.60-0.80). Whether to use the staked-crop values in footnote 2 (1.20 or 1.15 for tomato Kc mid; 1.15 or 1.10 for pepper) and a taller h.
- Zr within the Table 22 range (smaller for scheduling per footnote 1), and whether Zr grows with time (Annex Eq. 8-1 to 8-3). Whether to adjust p for ETc (limits 0.1-0.8) and for soil texture.
- Initial depletion (Eq. 87, or assume 0 after wetting), and how to handle rain: the source suggests ignoring rain below about 0.2 ETo and gives no runoff method; CR set to 0 only if the water table is deeper than about 1 m below the root zone.
- fw for the emitter layout (Table 20 gives 0.3-0.4 for trickle) and whether to apply the drip shading reduction (one-half to one-third, or `fw [1 - (2/3) fc]`) in the dual method.
- Irrigation trigger policy: Annex 8 irrigates the next morning once end-of-day Dr exceeds RAW and refills exactly the depletion. A planner may want a safety margin or an irrigation depth cap; the source only requires `I <= Dr` and irrigation "before or at" Dr = RAW.
- Time of day for irrigation and rain (Annex 8 assumes early morning; Example 38 gives both variants for Dr start).

## Sources

All fetched from fao.org on 2026-11-16:
- https://www.fao.org/3/x0490E/x0490e00.htm (index)
- https://www.fao.org/3/x0490E/x0490e0a.htm (Chapter 5)
- https://www.fao.org/3/x0490E/x0490e0b.htm (Chapter 6)
- https://www.fao.org/3/x0490E/x0490e0c.htm (Chapter 7; Tables 17, 19, 20, Eq. 75 only)
- https://www.fao.org/3/x0490E/x0490e0e.htm (Chapter 8)
- https://www.fao.org/3/x0490E/x0490e0p.htm (Annex 8)
- Equation and figure images read from https://www.fao.org/4/x0490e/ : x0490e2b, 2c, 2d, 2f, 2i, 2k, 2w, 5z, 60, 7e, 7f, 7g (.gif). x0490e7e, 7f and 7g are the Fig. 8.1 spreadsheet image segments (Fig. 8.1 is not embedded in the annex page; these were found by file name and match the Box 8.1 columns).
