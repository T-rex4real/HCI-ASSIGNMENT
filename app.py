"""Human Perception & Performance Tester  (Tkinter)

An experimenter panel on the left controls three visual variables
(contrast, size, brightness). The stage on the right runs two tasks:

  1. Identification - what do you see in an ambiguous figure?
  2. Target Hitting - click targets of different sizes and distances (Fitts' Law).

After each block the participant rates ease of use (1-5) and every trial is
appended to results.csv (see logger.py).

Run with:  python app.py
"""

import math
import random
import time
import tkinter as tk
from tkinter import messagebox

import figures
import logger
import themes

# The clock is a module-level name so that tests can replace it.
now = time.perf_counter

# ---- Stage layout ------------------------------------------------------------
CANVAS_W, CANVAS_H = 900, 480

# ---- Target Hitting settings -------------------------------------------------
DISTANCES = [150, 300, 500]     # px from the start button to the target centre
TARGET_SIZES = [20, 40, 80]     # target diameter in px
REPEATS = 2                     # repeats of every distance x size combination
PRACTICE_TRIALS = 2             # warm-up trials that are NOT logged
START_RADIUS = 40               # radius of the GO button
START_MARGIN = 70               # GO button distance from the left/right edge
BETWEEN_TRIALS_MS = 400         # pause after a successful hit

# ---- Identification settings -------------------------------------------------
NECKER = "Necker cube"
RUBIN = "Rubin's vase"
FIGURE_NAMES = [NECKER, RUBIN]
FIGURE_CHOICES = {
    NECKER: ["Front face is lower-left", "Front face is upper-right",
             "Flat pattern of lines", "Can't tell"],
    RUBIN: ["A vase", "Two faces", "Both (it switched)", "Can't tell"],
}

RATING_LABELS = ["1\nVery difficult", "2", "3", "4", "5\nVery easy"]


class App:
    """The whole application: experimenter controls, stage and the two tasks."""

    def __init__(self, root):
        self.root = root
        root.title("Human Perception & Performance Tester")
        root.resizable(False, False)
        root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Experimenter settings
        self.participant_var = tk.StringVar()
        self.contrast_var = tk.StringVar(value="High")
        self.size_var = tk.StringVar(value="Medium")
        self.brightness_var = tk.IntVar(value=themes.BRIGHTNESS_DEFAULT)
        self.ratio_var = tk.StringVar()
        self.status_var = tk.StringVar()

        # Run state
        self.mode = "idle"            # idle | ident | fitts | rating
        self.cond = None              # visual condition frozen for the current block
        self.block_rows = []          # rows waiting for the ease-of-use rating
        self.t0 = 0.0                 # start time of the current trial
        self.control_widgets = []     # widgets locked while a test is running

        # Identification state
        self.ident_queue = []
        self.ident_trial = 0
        self.current_figure = None

        # Target Hitting state
        self.trials = []
        self.trial_index = -1
        self.real_trials_done = 0
        self.fitts_state = None       # await_start | await_target | between
        self.geom = None
        self.misses = 0

        self._build_controls()
        self._build_stage()
        self.apply_theme()
        self.set_status("Enter a participant ID, choose a visual condition, "
                        "then start a task.")

    # ------------------------------------------------------------------ layout
    def _build_controls(self):
        """Experimenter panel (always uses the normal system colours)."""
        panel = tk.Frame(self.root, padx=10, pady=10)
        panel.pack(side="left", fill="y")

        tk.Label(panel, text="Experimenter panel", font=("Arial", 14, "bold")
                 ).pack(anchor="w", pady=(0, 8))

        box = tk.LabelFrame(panel, text="Participant ID", padx=8, pady=6)
        box.pack(fill="x", pady=4)
        entry = tk.Entry(box, textvariable=self.participant_var, width=18)
        entry.pack(anchor="w")
        self.control_widgets.append(entry)

        box = tk.LabelFrame(panel, text="Contrast", padx=8, pady=6)
        box.pack(fill="x", pady=4)
        for level in themes.CONTRAST_LEVELS:
            rb = tk.Radiobutton(box, text=level, value=level,
                                variable=self.contrast_var,
                                command=self.apply_theme)
            rb.pack(anchor="w")
            self.control_widgets.append(rb)
        tk.Label(box, textvariable=self.ratio_var, fg="#444444"
                 ).pack(anchor="w", pady=(4, 0))

        box = tk.LabelFrame(panel, text="Size (text and figure)", padx=8, pady=6)
        box.pack(fill="x", pady=4)
        for level in themes.SIZE_LEVELS:
            rb = tk.Radiobutton(box, text=level, value=level,
                                variable=self.size_var,
                                command=self.apply_theme)
            rb.pack(anchor="w")
            self.control_widgets.append(rb)

        box = tk.LabelFrame(panel, text="Brightness (%)", padx=8, pady=6)
        box.pack(fill="x", pady=4)
        scale = tk.Scale(box, from_=themes.BRIGHTNESS_MIN,
                         to=themes.BRIGHTNESS_MAX, orient="horizontal",
                         length=180, variable=self.brightness_var,
                         command=lambda _value: self.apply_theme())
        scale.pack()
        self.control_widgets.append(scale)

        box = tk.LabelFrame(panel, text="Tasks", padx=8, pady=6)
        box.pack(fill="x", pady=4)
        for text, command in (("Start Identification Task", self.start_identification),
                              ("Start Target Hitting Task", self.start_fitts)):
            btn = tk.Button(box, text=text, command=command, width=24)
            btn.pack(pady=3)
            self.control_widgets.append(btn)

        tk.Label(panel, text="Settings are locked while a task is running.\n"
                             "Results are saved to results.csv",
                 fg="#444444", justify="left").pack(anchor="w", pady=(10, 0))

    def _build_stage(self):
        """Stimulus canvas (themed) plus a status/answer bar (normal colours)."""
        stage = tk.Frame(self.root, padx=6, pady=10)
        stage.pack(side="left")

        self.canvas = tk.Canvas(stage, width=CANVAS_W, height=CANVAS_H,
                                highlightthickness=1,
                                highlightbackground="#888888")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        bar = tk.Frame(stage, height=110)
        bar.pack(fill="x", pady=(8, 0))
        bar.pack_propagate(False)
        tk.Label(bar, textvariable=self.status_var, font=("Arial", 12),
                 anchor="w", justify="left", wraplength=CANVAS_W
                 ).pack(fill="x")
        self.button_row = tk.Frame(bar)
        self.button_row.pack(fill="x", pady=(6, 0))

    # ------------------------------------------------------- small UI helpers
    def set_status(self, text):
        self.status_var.set(text)

    def set_controls_enabled(self, enabled):
        state = "normal" if enabled else "disabled"
        for widget in self.control_widgets:
            widget.configure(state=state)

    def clear_buttons(self):
        for child in self.button_row.winfo_children():
            child.destroy()

    def show_buttons(self, labels, callback):
        """Replace the answer buttons with one button per label."""
        self.clear_buttons()
        for label in labels:
            tk.Button(self.button_row, text=label, font=("Arial", 12),
                      padx=10, command=lambda lb=label: callback(lb)
                      ).pack(side="left", padx=4)

    def check_participant(self):
        if not self.participant_var.get().strip():
            messagebox.showwarning("Participant ID",
                                   "Please enter a participant ID first.")
            return False
        return True

    # ------------------------------------------------------ visual condition
    def condition(self):
        """Read the experimenter settings into one dictionary."""
        contrast = self.contrast_var.get()
        size = self.size_var.get()
        brightness = int(self.brightness_var.get())
        fg, bg = themes.get_colours(contrast, brightness)
        return {
            "contrast": contrast,
            "size": size,
            "brightness": brightness,
            "fg": fg,
            "bg": bg,
            "ratio": themes.contrast_ratio(fg, bg),
            "font": themes.SIZE_LEVELS[size]["font"],
            "figure": themes.SIZE_LEVELS[size]["figure"],
        }

    def apply_theme(self):
        """Apply contrast / size / brightness to the stage and redraw it."""
        c = self.condition()
        self.ratio_var.set(f"Text/background ratio: {c['ratio']:.1f}:1")
        self.render_stage()

    # ---------------------------------------------------------------- drawing
    def render_stage(self):
        """Clear the canvas and draw whatever the current mode needs."""
        # During a block the condition is frozen; otherwise follow the controls.
        c = self.cond if self.mode != "idle" and self.cond else self.condition()
        self.canvas.delete("all")
        self.canvas.configure(bg=c["bg"])

        if self.mode == "idle":
            self._draw_text(c, 40, "Visual condition preview", bold=True)
            self._draw_text(c, 110, "The quick brown fox jumps over the lazy dog.")
            self._draw_figure(c, NECKER, CANVAS_W / 2, 330)
        elif self.mode == "ident":
            self._draw_text(c, 45, "What do you see in this picture? "
                                   "Choose an answer below.")
            self._draw_figure(c, self.current_figure, CANVAS_W / 2, CANVAS_H / 2 + 50)
        elif self.mode == "fitts":
            self._draw_fitts(c)
        elif self.mode == "rating":
            self._draw_text(c, CANVAS_H / 2, "Thank you! Please rate how easy "
                                             "that was using the buttons below.")

    def _draw_text(self, c, y, text, bold=False):
        font = ("Arial", c["font"], "bold") if bold else ("Arial", c["font"])
        self.canvas.create_text(CANVAS_W / 2, y, text=text, fill=c["fg"],
                                font=font, width=CANVAS_W - 80, justify="center")

    def _draw_figure(self, c, name, cx, cy):
        size = c["figure"]
        fg, bg = c["fg"], c["bg"]
        if name == NECKER:
            width = max(2, size // 50)
            for (x1, y1), (x2, y2) in figures.necker_cube_lines(cx, cy, size):
                self.canvas.create_line(x1, y1, x2, y2, fill=fg, width=width,
                                        capstyle="round")
        else:  # Rubin's vase: dark block with a light vase-shaped hole
            self.canvas.create_rectangle(*figures.vase_frame(cx, cy, size),
                                         fill=fg, outline=fg)
            self.canvas.create_polygon(figures.vase_polygon(cx, cy, size),
                                       fill=bg, outline=bg)

    def _draw_fitts(self, c):
        g = self.geom
        self._draw_text(c, 40, "Click GO, then click the circle as fast and "
                               "accurately as you can.")
        if self.fitts_state == "await_start":
            r = START_RADIUS
            self.canvas.create_oval(g["sx"] - r, g["sy"] - r, g["sx"] + r,
                                    g["sy"] + r, fill=c["fg"], outline=c["fg"])
            self.canvas.create_text(g["sx"], g["sy"], text="GO", fill=c["bg"],
                                    font=("Arial", c["font"], "bold"))
        elif self.fitts_state == "await_target":
            r = g["w"] / 2
            self.canvas.create_oval(g["tx"] - r, g["sy"] - r, g["tx"] + r,
                                    g["sy"] + r, fill=c["fg"], outline=c["fg"])

    # ------------------------------------------------------------ result rows
    def base_row(self, task_type, trial):
        """Fields shared by every logged row."""
        c = self.cond
        return {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "participant": self.participant_var.get().strip(),
            "task_type": task_type,
            "trial": trial,
            "visual_condition": f"{c['contrast']} contrast | {c['size']} size | "
                                f"{c['brightness']}% brightness",
            "contrast": c["contrast"],
            "size": c["size"],
            "brightness_pct": c["brightness"],
            "contrast_ratio": round(c["ratio"], 2),
        }

    def save_rows(self):
        """Append the finished block to the CSV, offering a retry on failure."""
        while True:
            try:
                logger.log_rows(self.block_rows)
                return True
            except OSError as error:
                again = messagebox.askretrycancel(
                    "Could not save results",
                    f"{error}\n\nIf results.csv is open in Excel, close it and "
                    "press Retry.")
                if not again:
                    return False

    # ----------------------------------------------------------- block ending
    def finish_block(self):
        """Ask for the ease-of-use rating, then save the block."""
        self.mode = "rating"
        self.render_stage()
        self.set_status("How easy was this task?  1 = very difficult ... "
                        "5 = very easy")
        self.show_buttons(RATING_LABELS, self.on_rating)

    def on_rating(self, label):
        rating = int(label[0])
        for row in self.block_rows:
            row["ease_1to5"] = rating
        saved = self.save_rows()
        count = len(self.block_rows)
        self.block_rows = []
        self.mode = "idle"
        self.clear_buttons()
        self.set_controls_enabled(True)
        self.apply_theme()
        if saved:
            self.set_status(f"Saved {count} rows to results.csv. Change the "
                            "visual condition and run another test.")
        else:
            self.set_status("The results of the last block were NOT saved.")

    # -------------------------------------------------- Task 1: Identification
    def start_identification(self):
        if not self.check_participant():
            return
        self.cond = self.condition()
        self.mode = "ident"
        self.block_rows = []
        self.ident_queue = random.sample(FIGURE_NAMES, len(FIGURE_NAMES))
        self.ident_trial = 0
        self.set_controls_enabled(False)
        self.show_next_figure()

    def show_next_figure(self):
        if not self.ident_queue:
            self.finish_block()
            return
        self.current_figure = self.ident_queue.pop(0)
        self.ident_trial += 1
        self.render_stage()
        self.set_status(f"Picture {self.ident_trial} of {len(FIGURE_NAMES)}: "
                        "choose what you see.")
        self.show_buttons(FIGURE_CHOICES[self.current_figure],
                          self.on_ident_answer)
        self.t0 = now()

    def on_ident_answer(self, choice):
        elapsed = now() - self.t0
        row = self.base_row("Identification", self.ident_trial)
        row.update(stimulus=self.current_figure, time_sec=round(elapsed, 3),
                   response=choice)
        self.block_rows.append(row)
        self.clear_buttons()
        self.show_next_figure()

    # ------------------------------------------- Task 2: Target Hitting (Fitts)
    def start_fitts(self):
        if not self.check_participant():
            return
        self.cond = self.condition()
        self.mode = "fitts"
        self.block_rows = []

        combos = [(d, w) for d in DISTANCES for w in TARGET_SIZES]
        real = combos * REPEATS
        random.shuffle(real)
        practice = random.sample(combos, PRACTICE_TRIALS)
        self.trials = ([(d, w, True) for d, w in practice] +
                       [(d, w, False) for d, w in real])
        self.trial_index = -1
        self.real_trials_done = 0
        self.set_controls_enabled(False)
        self.clear_buttons()
        self.next_fitts_trial()

    def next_fitts_trial(self):
        self.trial_index += 1
        if self.trial_index >= len(self.trials):
            self.finish_block()
            return
        distance, width, is_practice = self.trials[self.trial_index]

        # The start button alternates randomly between the left and right edge.
        sy = CANVAS_H // 2 + 30
        if random.random() < 0.5:
            sx, tx = START_MARGIN, START_MARGIN + distance
        else:
            sx, tx = CANVAS_W - START_MARGIN, CANVAS_W - START_MARGIN - distance
        self.geom = {"sx": sx, "sy": sy, "tx": tx, "d": distance, "w": width,
                     "practice": is_practice}
        self.misses = 0
        self.fitts_state = "await_start"

        if is_practice:
            self.set_status(f"Practice {self.trial_index + 1} of "
                            f"{PRACTICE_TRIALS} (not recorded)")
        else:
            total = len(self.trials) - PRACTICE_TRIALS
            self.set_status(f"Trial {self.real_trials_done + 1} of {total}")
        self.render_stage()

    def on_canvas_click(self, event):
        """Handle every click on the stage (only the Target Hitting task uses it)."""
        if self.mode != "fitts":
            return
        g = self.geom
        if self.fitts_state == "await_start":
            if math.hypot(event.x - g["sx"], event.y - g["sy"]) <= START_RADIUS:
                self.fitts_state = "await_target"
                self.render_stage()          # the target appears
                self.t0 = now()              # timer starts when it is visible
        elif self.fitts_state == "await_target":
            if math.hypot(event.x - g["tx"], event.y - g["sy"]) <= g["w"] / 2:
                self.record_hit(now() - self.t0)
            else:
                self.misses += 1

    def record_hit(self, elapsed):
        g = self.geom
        self.fitts_state = "between"
        if not g["practice"]:
            self.real_trials_done += 1
            row = self.base_row("Target Hitting", self.real_trials_done)
            row.update(distance_px=g["d"], target_size_px=g["w"],
                       time_sec=round(elapsed, 3), misses=self.misses,
                       response="hit")
            self.block_rows.append(row)
        self.render_stage()                  # target disappears
        self.root.after(BETWEEN_TRIALS_MS, self.next_fitts_trial)

    # ---------------------------------------------------------------- closing
    def on_close(self):
        if self.mode != "idle" and not messagebox.askyesno(
                "Quit", "A test is still running and its results will not be "
                        "saved. Quit anyway?"):
            return
        self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
