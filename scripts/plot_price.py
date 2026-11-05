import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from load_gladiator import load_gladiator

SURF, INK, INK2, GRID, BLUE, BLUE_LT = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1", "#2a78d6", "#86b6ef"

df = load_gladiator(sys.argv[1]).dropna(subset=["Price"])
monthly = df.set_index("Date")["Price"].resample("MS").mean().dropna()
monthly.index = monthly.index + __import__("pandas").Timedelta(days=14)  # plot mid-month

fig, ax = plt.subplots(figsize=(10, 4.8), dpi=200, facecolor=SURF)
ax.set_facecolor(SURF)
ax.scatter(df["Date"], df["Price"], s=14, color=BLUE_LT, edgecolor=SURF, linewidth=0.6, zorder=2, label="Each fill-up")
ax.plot(monthly.index, monthly.values, color=BLUE, lw=2, solid_joinstyle="round", solid_capstyle="round", zorder=3, label="Monthly average")

# Annotations: peak fill-up and latest monthly average
pk = df.loc[df["Price"].idxmax()]
ax.annotate(f"Peak ${pk.Price:.3f}\n{pk.Date:%b %-d, %Y}", (pk.Date, pk.Price), xytext=(10, 2),
            textcoords="offset points", fontsize=9, color=INK2, va="bottom")
ax.scatter([monthly.index[-1]], [monthly.values[-1]], s=40, color=BLUE, edgecolor=SURF, linewidth=1.5, zorder=4)
ax.annotate(f"${monthly.values[-1]:.2f}", (monthly.index[-1], monthly.values[-1]), xytext=(8, 0),
            textcoords="offset points", fontsize=10, color=INK, va="center", weight="bold")

ax.yaxis.set_major_formatter(lambda v, _: f"${v:.2f}")
ax.xaxis.set_major_locator(mdates.YearLocator())
ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
ax.set_ylim(2.0, 6.0)
ax.grid(axis="y", color=GRID, lw=1)
ax.set_axisbelow(True)
for s in ["top", "right", "left"]:
    ax.spines[s].set_visible(False)
ax.spines["bottom"].set_color(GRID)
ax.tick_params(colors=INK2, length=0, labelsize=9)
ax.set_title("Jeep Gladiator: price per gallon, 2021–2026", loc="left", fontsize=13, color=INK, weight="bold", pad=24)
ax.text(0, 1.02, f"{len(df)} fill-ups with a recorded price · mostly 87 octane", transform=ax.transAxes, fontsize=9, color=INK2)
leg = ax.legend(loc="upper right", frameon=False, fontsize=9, labelcolor=INK2)
fig.tight_layout()
fig.savefig(sys.argv[2], facecolor=SURF)
print(monthly.idxmax(), monthly.max(), df.groupby(df.Date.dt.year)["Price"].mean().round(3).to_dict())
