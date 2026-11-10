# Human Perception & Performance Tester

A Tkinter application for testing how visual conditions (contrast, size, brightness) affect human performance on two tasks.

## Files

| File | Purpose |
| --- | --- |
| `app.py` | The GUI application (run this) |
| `themes.py` | Contrast palettes, size presets, brightness and contrast-ratio maths |
| `figures.py` | Shapes of the two ambiguous figures (Necker cube, Rubin's vase) |
| `logger.py` | CSV logging to `results.csv` |
| `analyze.py` | Summarises `results.csv` for the report and saves charts |

## Running it

Requires Python 3.8+ with Tkinter (included in the python.org installers; on Debian/Ubuntu run `sudo apt install python3-tk`). Charts in `analyze.py` need `matplotlib` (optional: `pip install matplotlib`).

```
python app.py          # run the tests; results are appended to results.csv
python analyze.py      # summarise results.csv (also writes analysis_output/)
```

## How it works

**Experimenter panel (left)** sets the visual condition. Settings lock while a task is running.

- **Contrast**: High (black on white, 21:1), Medium (grey on white, 4.5:1), Low (light grey on white, 1.8:1). Grey only, so only luminance changes.
- **Size**: Small / Medium / Large change the font size and the ambiguous-figure size (an approximation of visual angle).
- **Brightness**: a 30-100% slider multiplies the text and background colours, like dimming a screen.

**Identification task**: shows two ambiguous figures in random order (a Necker cube and Rubin's vase). The participant picks what they see. The response and the time to answer are logged.

**Target Hitting task (Fitts' Law)**: the participant clicks GO, then clicks a circular target as fast as possible. Distance (150, 300, 500 px) and target size (20, 40, 80 px) are crossed, with 2 repeats each (18 logged trials, in random order) after 2 unlogged practice trials. Time runs from the target appearing until it is hit. Clicks that miss are counted in `misses`.

After each block the participant rates ease of use from 1 to 5, and the rating is saved on every row of that block.

## CSV columns

`timestamp, participant, task_type, trial, visual_condition, contrast, size, brightness_pct, contrast_ratio, stimulus, distance_px, target_size_px, time_sec, misses, response, ease_1to5`

`task_type` is `Identification` or `Target Hitting`. Columns that do not apply to a task are left empty.

## Suggested data-collection protocol

For each participant (aim for at least 2, who are not the developer):

1. Target Hitting at High, Medium and Low contrast (Medium size, 100% brightness).
2. Target Hitting at Small size and at about 40% brightness (High contrast).
3. Identification at High, Medium and Low contrast, then Small size and 40% brightness.

That is about 8 Target Hitting blocks (about 1-2 minutes each) and 5 short Identification blocks, so roughly 15-20 minutes per person. Note any observations (squinting, hesitation, comments) for the report.
