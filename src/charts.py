"""Two static charts for the README and portfolio (PNG, light theme).

Colors come from a colorblind-checked categorical palette. Each chart has one dollar
axis, a light grid, and labels in text colors rather than series colors.
"""
import matplotlib

matplotlib.use("Agg")  # no screen needed (works in CI)
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

SURFACE, TEXT, TEXT_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
DOLLARS = FuncFormatter(lambda v, _: f"${v / 1000:,.0f}K" if abs(v) >= 1000 else f"${v:,.0f}")


def _style(ax, title, subtitle):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.yaxis.set_major_formatter(DOLLARS)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.tick_params(colors=TEXT_2, length=0, labelsize=9)
    ax.set_title(title, loc="left", fontsize=12, fontweight="bold", color=TEXT, pad=22)
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=9, color=TEXT_2)


def aging_chart(summary, path, note=""):
    """Open balance by aging bucket: one series, so no legend; the title names it."""
    fig, ax = plt.subplots(figsize=(7, 3.6), dpi=150, facecolor=SURFACE)
    bars = ax.bar(summary["bucket"].astype(str), summary["balance"], width=0.6, color=BLUE)
    for b, v, pct in zip(bars, summary["balance"], summary["pct_of_total"]):
        ax.text(b.get_x() + b.get_width() / 2, v, f"${v:,.0f}\n{pct:.0f}%", ha="center", va="bottom",
                fontsize=8.5, color=TEXT_2)
    ax.margins(y=0.25)
    _style(ax, "Open AR by days past due", f"Total ${summary['balance'].sum():,.0f}{note}")
    ax.set_xlabel("Days past due date", fontsize=9, color=TEXT_2)
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)


def ar_trend_chart(month_end, path, note=""):
    """Invoiced vs collected per month (bars) and closing AR (line), all on one dollar axis."""
    fig, ax = plt.subplots(figsize=(7, 3.6), dpi=150, facecolor=SURFACE)
    x = range(len(month_end))
    w = 0.36
    ax.bar([i - w / 2 - 0.01 for i in x], month_end["invoiced"], width=w, color=BLUE, label="Invoiced")
    ax.bar([i + w / 2 + 0.01 for i in x], month_end["collected"], width=w, color=ORANGE, label="Collected")
    ax.plot(list(x), month_end["closing_ar"], color=AQUA, linewidth=2, marker="o", markersize=5,
            markeredgecolor=SURFACE, markeredgewidth=1.5, label="Closing AR")
    last = len(month_end) - 1
    ax.annotate(f"Closing AR ${month_end['closing_ar'].iloc[-1]:,.0f}", (last, month_end["closing_ar"].iloc[-1]),
                xytext=(0, 9), textcoords="offset points", ha="center", fontsize=8.5, color=TEXT)
    ax.set_xticks(list(x), month_end["month"])
    ax.margins(y=0.2)
    _style(ax, "Monthly AR roll-forward", f"Opening AR + invoiced - collected = closing AR{note}")
    ax.legend(frameon=False, fontsize=8.5, labelcolor=TEXT_2, ncol=3, loc="upper left", bbox_to_anchor=(0, -0.1))
    fig.tight_layout()
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
