"""Matplotlib plots. Single run: step plot. Ensemble: mean line with +-1 SD band."""
import io

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

try:  # seaborn is optional; it only changes the look
    import seaborn as sns
    sns.set_theme(style="whitegrid")
except Exception:  # pragma: no cover
    pass


def fig_to_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def plot_single(traj, species, t_end):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    times, counts = traj.times, traj.counts
    if times[-1] < t_end:  # hold the last state to the end time
        times = np.append(times, t_end)
        counts = np.vstack([counts, counts[-1]])
    for s in species:
        ax.plot(times, counts[:, traj.species.index(s)], drawstyle="steps-post", label=s)
    ax.set_xlabel("time")
    ax.set_ylabel("molecule count")
    ax.set_xlim(0, t_end)
    ax.legend()
    fig.tight_layout()
    return fig


def plot_ensemble(ens, species, overlay=False, max_overlay=50):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    for s in species:
        line, = ax.plot(ens.grid, ens.mean[s], label=f"{s} mean")
        color = line.get_color()
        if overlay:
            for run in ens.runs[s][:max_overlay]:
                ax.plot(ens.grid, run, color=color, alpha=0.12, linewidth=0.8, drawstyle="steps-post")
        ax.fill_between(ens.grid, ens.mean[s] - ens.sd[s], ens.mean[s] + ens.sd[s], color=color, alpha=0.25)
    ax.set_xlabel("time")
    ax.set_ylabel("molecule count")
    ax.set_title(f"Mean ± 1 SD of {ens.n_runs} runs")
    ax.legend()
    fig.tight_layout()
    return fig


def plot_histogram(values, title, poisson_mean=None):
    from math import exp, lgamma, log
    fig, ax = plt.subplots(figsize=(6, 3.5))
    values = np.asarray(values)
    bins = np.arange(values.min(), values.max() + 2) - 0.5
    ax.hist(values, bins=bins, density=True, alpha=0.7, label="simulation")
    if poisson_mean:
        xs = np.arange(values.min(), values.max() + 1)
        ax.plot(xs, [exp(-poisson_mean + x * log(poisson_mean) - lgamma(x + 1)) for x in xs],
                "o-", color="black", label="Poisson")
    ax.set_xlabel("final count")
    ax.set_ylabel("probability")
    ax.set_title(title)
    ax.legend()
    fig.tight_layout()
    return fig
