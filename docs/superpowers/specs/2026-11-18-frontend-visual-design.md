# frontend: visual design plan

Made with the `frontend-design` skill (`.claude/skills/frontend-design/SKILL.md`) for the design in `2026-11-18-frontend-design.md`. This is a plan to approve before the UI is built (plan Task 7 to 8). It decides the look only; behaviour and data are in the design document. Decisions are recorded in `docs/judgment-log-p2.md`, not here.

## Subject, audience, job

- **Subject:** a drip-irrigation planner for a small grower.
- **Audience:** a grower standing in a field, on a phone, often in bright sun, wearing gloves or with dirty hands. Reads one answer, then maybe the week.
- **Primary job:** answer "should I water this plot today, and for how long?" at arm's length, in one second.

## Colour (base palette)

Colour carries meaning: blue is water to apply, amber is "this number rests on an old forecast", red is "something failed". No colour is used for decoration. Contrast values are against the stated background and meet WCAG AA (4.5:1 for text).

| Name | Hex | Role | Contrast |
|---|---|---|---|
| Dew | `#F4F8F9` | page background | |
| Ink | `#14262E` | body text, headings | 14.6:1 on Dew |
| Drip | `#0A6C9B` | the "water" colour: today's slab when watering, markers of irrigation days | 5.4:1 on Dew; white on Drip 5.8:1 |
| Furrow | `#566B73` | secondary text, labels, rules (rules use Furrow at 30% opacity) | 5.2:1 on Dew |
| Sun | `#8A5200` on `#FFEFCC` | stale warning text and tint | 5.6:1 |
| Fault | `#A82018` on `#FDE6E3` | error text and tint | 6.1:1 |

Light theme only. A grower in sun needs light; the page sets `color-scheme: light` so a phone in dark mode does not make a half-dark page. (My call, easy to reverse.)

## Type

Two families, clearly different, both from Google Fonts through `next/font` (self-hosted at build time):

- **Bricolage Grotesque** (variable, heavy weights, slightly condensed at large sizes): the recommendation, page titles and plot names. It has character at large size and stays sturdy in sunlight.
- **Atkinson Hyperlegible Next**: everything else. It was designed by the Braille Institute for low-vision legibility; its letterforms are made to tell apart similar characters (1, l, I, 0, O), which matters for numbers read at a glance in glare. If this family is not in this Next.js version's font list, use Atkinson Hyperlegible and note it.

Scale (ratio about 1.25, base 16 px, line length under 70 characters, sentence case everywhere):

| Use | Size | Weight / family |
|---|---|---|
| Recommendation | fluid, 40 px at 375 px wide up to 72 px | Bricolage 800, line-height 1.02, tracking -0.02em |
| Page title (farm and plot names) | 25 to 31 px | Bricolage 700 |
| Day action ("45 minutes") | 20 px | Atkinson 700 |
| Body | 16 px, line-height 1.5 | Atkinson 400 |
| Labels, small values | 14 px | Atkinson 400 and 700 |

Numbers use tabular figures so columns of minutes and litres line up.

## Layout

One column, **left-aligned** throughout (a ragged right edge is easier to scan in motion than centred text), at most 40 rem wide on a large screen. No grid of cards.

**Idea:** the top of the plot page is one full-width slab that is the whole answer. When the plot needs water, the slab is solid Drip blue with white type. When it does not, it is Dew with a Furrow outline and Ink type. The state is readable from arm's length before a word is read. The seven days below it are a **timeline**: a vertical line with one marker per day, because the content really is a sequence of consecutive days. Irrigation days have a filled blue marker; days without irrigation a hollow one.

Plot page at 375 px (the slab and the first row are visible without scrolling, NFR-2.8):

```
┌───────────────────────────────┐
│ AgroPilot   Registry up       │  thin status line, one row,
│ Weather up  Planner up        │  text + a shape, never colour only
├───────────────────────────────┤
│ North block                   │  Bricolage 700, plot name
│ Tomato, 1 000 m²              │  Furrow
│                               │
│█████████████████████████████ █│  slab: Drip blue, white text
│█ Water for                   █│
│█ 38 minutes                  █│  Bricolage 800, ~40 px
│█                             █│
│█ 1 000 litres, today         █│  Atkinson 16 px
│█████████████████████████████ █│
│                               │
│ ⚠ Old forecast (amber panel)  │  only when today is stale
│                               │
│ The next days                 │
│ ●─ Tomorrow, Fri 20 Nov       │  filled marker: water
│ │   45 minutes   2 700 litres │
│ │   Evapotranspiration 3.1 mm │  small labelled values,
│ │   Kc 0.8   Soil water 112 mm│  label above value
│ ○─ Sat 21 Nov                 │  hollow marker: no irrigation
│ │   No irrigation             │
│ ...                           │
└───────────────────────────────┘
```

Same page when nothing is needed: the slab becomes an outlined Dew panel reading "No irrigation today", with the bucket level beneath it.

Same page on an error: the slab is replaced by a Fault-tinted panel with the title from `describeError` (for example "The weather service is not available") and the one-line instruction. No plan below it.

Plot page at desktop width (about 1000 px): the same single column, left-aligned at the left of a 40 rem column, with generous empty space on the right. The page does not stretch the seven days into a wide table. (Rejected: a two-column layout with the slab on the left and the timeline on the right. It would put the answer and the days side by side, but it makes the phone layout, the one that matters, an afterthought.)

Home page (`/`) at 375 px:

```
┌───────────────────────────────┐
│ AgroPilot   Registry up ...   │
├───────────────────────────────┤
│ Your plots                    │  Bricolage 700
│                               │
│ North farm                    │  Bricolage 700, 25 px
│ ───────────────────────────── │  hairline
│ North block        tomato     │  each plot is a full-width link,
│ East block         tomato     │  at least 48 px tall
│                               │
│ South farm                    │
│ ───────────────────────────── │
│ Greenhouse         bell pepper│
└───────────────────────────────┘
```

Plots are ruled rows, not cards: the farm is a heading and its plots are a list under it, which is exactly the content's structure.

## Principles

1. **One memorable thing:** the answer slab. Everything else is quiet.
2. **Colour is information.** Water blue, stale amber and error red are never used for anything else, and none of them is the only carrier of meaning: stale has the words "Old forecast", an error has words, status has "up" and "down" next to a shape.
3. **Structure follows content.** The days are a timeline because they are a sequence. The farms are headings because they group plots. No decoration without a job.
4. **Hit targets of at least 48 px** and visible keyboard focus (a 3 px Drip outline with an offset).
5. **No motion** except what the browser does by default. `prefers-reduced-motion` is respected by having none to reduce.
6. **Copy from the grower's side:** "Water for 38 minutes", "No irrigation today", "Old forecast". It says what happened and what to do, in sentence case, without apology.

## Review against the brief

I checked the plan against the skill's list of common generated-page defaults, and changed these:

- **First draft used Geist (the scaffold's font) and shadcn's grey neutrals.** Both are the template defaults. Replaced with Bricolage Grotesque and Atkinson Hyperlegible Next, and a palette taken from the job (water, sun, fault).
- **First draft showed the soil bucket as a bar.** Rejected: a bar needs the bucket's full size, which the planner does not return, and working it out in the frontend would be an irrigation calculation (rule 12). The bucket level is a plain labelled number.
- **First draft was a stack of identical rounded cards for the seven days** (the "SaaS-card kit"). Replaced with a timeline of ruled rows, whose markers carry the irrigation state.
- **Avoided on purpose:** cream-and-terracotta, near-black with one acid accent, a broadsheet look, all-caps eyebrow labels, strings joined with middle dots, arrows on links, gradient washes, a shadow under everything. The corner radius is one small value (6 px), used only on the slab and the notices.
- **What still reads as a template:** a light page with blue as the accent is common. It is kept because the colour has a job here (blue means water to apply), and because the slab's solid fill is a bolder move than the usual blue button.

## For the builder

- Tokens live in `src/app/globals.css` as the shadcn CSS variables: `--background` Dew, `--foreground` Ink, `--primary` Drip, `--muted-foreground` Furrow, `--destructive` Fault, plus two extra variables for Sun and its tint, and one for Fault's tint. Remove the `.dark` variant block.
- Use shadcn `Button` for the back link and the retry button. Everything else is plain elements with Tailwind classes. Add no other shadcn component unless a test needs it.
- Day labels come from the date string only (never the server clock): "Today" for the first day, "Tomorrow" for the second, then weekday, day and month. Format with `Intl.DateTimeFormat` using `timeZone: "UTC"` on the parsed date, so no day shifts.
- The status line uses text ("up", "down", "checking") plus a shape (a filled circle for up, a cross for down, a hollow circle for checking), never colour alone.

## Amendment (2026-11-20): what is clickable and what is not

The first build made the blue answer panel look like a button, and the real links look like plain text. Changes, made with the `frontend-design` skill and approved by the learner:

- **One look for everything you can press, used for nothing else.** Ink (`--primary`, `#14262E`): filled with white text for an action ("Try again"), an outlined white group with a chevron on each row to go somewhere (the plots), underlined with a chevron for a link ("Back to all plots"). Pressed and hovered rows use `--pressed` (`#DCE8EC`).
- **Blue means water only.** `--water` (`#0A6C9B`) is used by the answer panel and the irrigation markers, not by links, buttons, the focus outline or the status dots. The focus outline is now Ink.
- **Passive things stay flat:** farm names, plan rows, the status line (the "up" dot is Ink), and the answer panel (no border, shadow or chevron).
- **The wordmark is plain text.** A "Back to all plots" link at the top of the plot page replaces it, and the red error panel has no button of its own.
