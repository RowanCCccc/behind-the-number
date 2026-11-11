"""
Behind the Number
What medical AI headlines don't tell you.

Run locally:  python3 -m streamlit run app.py
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from metrics import (
    calc_metrics,
    match_headline,
    parse_percent,
    prevalence_curve,
    rates_from_counts,
    round_to_total,
    wilson_ci,
)

st.set_page_config(page_title="Behind the Number", page_icon="🔎")

# ---------------------------------------------------------------------------
# Example studies
# ---------------------------------------------------------------------------
PRESETS = {
    "Example: UCL brain tumour MRI study (2026)": {
        "se": 91.5,
        "sp": 74.4,
        "prev": 89.4,
        "headline": "83",
        "pos": "the tumour will enhance",
        "neg": "the tumour will not enhance",
        "source": (
            "Example data: Ruffle et al. (2026), *The Lancet Medical Imaging & "
            "Theranostics*; UCL News, 16 September 2026."
        ),
        "subgroups": [["Children", 9, 20], ["Meningioma", 93, 100]],
    },
    "Enter my own numbers": {
        "se": 90.0,
        "sp": 90.0,
        "prev": 10.0,
        "headline": "",
        "pos": "positive",
        "neg": "negative",
        "source": "",
        "subgroups": [["Subgroup A", 18, 20]],
    },
}

COLOURS = {
    "tp": "#1d4ed8",   # correctly flagged
    "fn": "#dc2626",   # missed
    "tn": "#93c5fd",   # correctly cleared
    "fp": "#f59e0b",   # false alarm
    "ppv": "#1d4ed8",
    "npv": "#ea580c",
}


def pct(x: float) -> str:
    """0.509 -> '50.9%'"""
    return "—" if x != x else f"{x * 100:.1f}%"


def per100(x: float) -> str:
    """0.509 -> '51'"""
    return "—" if x != x else f"{round(x * 100)}"


def pts(diff: float) -> str:
    """Difference in percentage points, e.g. '+44.4 pts'"""
    return f"{diff * 100:+.1f} pts vs study"


# ---------------------------------------------------------------------------
# Sidebar: the study's numbers
# ---------------------------------------------------------------------------
st.sidebar.header("Study numbers")
preset_name = st.sidebar.selectbox("Start from", list(PRESETS))
preset = PRESETS[preset_name]
k = preset_name  # widget keys include the preset, so switching preset resets them

mode = st.sidebar.radio(
    "The study reports...",
    ["Sensitivity and specificity", "Counts (TP, FP, TN, FN)"],
    key="mode_" + k,
)

if mode == "Sensitivity and specificity":
    se = st.sidebar.number_input(
        "Sensitivity (%)", 0.0, 100.0, preset["se"], 0.1, key="se_" + k,
        help="Of the people who are truly positive, how many the AI finds.",
    ) / 100
    sp = st.sidebar.number_input(
        "Specificity (%)", 0.0, 100.0, preset["sp"], 0.1, key="sp_" + k,
        help="Of the people who are truly negative, how many the AI correctly clears.",
    ) / 100
    prev = st.sidebar.number_input(
        "Prevalence in the study (%)", 0.1, 99.9, preset["prev"], 0.1, key="prev_" + k,
        help="Share of people in the test set who are truly positive.",
    ) / 100
else:
    default = calc_metrics(preset["se"] / 100, preset["sp"] / 100, preset["prev"] / 100)
    tp = st.sidebar.number_input("True positives (TP)", min_value=0, value=round(default["tp"] * 1000), step=1, key="tp_" + k)
    fp = st.sidebar.number_input("False positives (FP)", min_value=0, value=round(default["fp"] * 1000), step=1, key="fp_" + k)
    tn = st.sidebar.number_input("True negatives (TN)", min_value=0, value=round(default["tn"] * 1000), step=1, key="tn_" + k)
    fn = st.sidebar.number_input("False negatives (FN)", min_value=0, value=round(default["fn"] * 1000), step=1, key="fn_" + k)
    rates = rates_from_counts(int(tp), int(fp), int(tn), int(fn))
    if rates is None:
        st.error("Please enter at least one truly positive case (TP + FN) and one truly negative case (TN + FP).")
        st.stop()
    se, sp, prev = rates

pos_word = st.sidebar.text_input("A positive result means...", preset["pos"], key="pos_" + k)
neg_word = st.sidebar.text_input("A negative result means...", preset["neg"], key="neg_" + k)
headline_text = st.sidebar.text_input(
    "Number in the headline (%), optional", preset["headline"], key="headline_" + k,
    help="For example, '83' if the news says the AI is '83% accurate'.",
)

# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.title("Behind the Number")
st.markdown("**What medical AI headlines don't tell you.**")
st.caption(
    "For understanding research numbers only. This tool does not diagnose or give "
    "medical advice. Nothing you enter is stored."
)
if preset["source"]:
    st.caption(preset["source"])

m = calc_metrics(se, sp, prev)

tab1, tab2, tab3 = st.tabs(
    ["1 · The numbers that matter", "2 · Change the setting", "3 · Check small subgroups"]
)

# ---------------------------------------------------------------------------
# Tab 1: the numbers that matter
# ---------------------------------------------------------------------------
with tab1:
    st.subheader("What the AI's answers really mean")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("PPV", pct(m["ppv"]), help="Positive predictive value: when the AI says positive, how often it is right.")
    c2.metric("NPV", pct(m["npv"]), help="Negative predictive value: when the AI says negative, how often it is right.")
    c3.metric("Accuracy", pct(m["acc"]), help="Share of all the AI's answers that are right.")
    c4.metric("Balanced accuracy", pct(m["bal"]), help="Average of sensitivity and specificity.")

    st.markdown(
        f"- When the AI says **{pos_word}**, it is right about **{per100(m['ppv'])} times in 100**.\n"
        f"- When the AI says **{neg_word}**, it is right about **{per100(m['npv'])} times in 100**."
    )

    headline = parse_percent(headline_text)
    if headline is not None:
        st.markdown("#### Headline check")
        matches = match_headline(headline, m)
        if matches:
            names = " or ".join(f"**{name}** ({pct(v)})" for name, v in matches)
            st.info(
                f"The headline figure of **{headline * 100:.0f}%** matches the {names}. "
                f"Plain accuracy is {pct(m['acc'])}. "
                f"When the AI says {neg_word}, it is right {pct(m['npv'])} of the time (NPV)."
            )
        else:
            st.warning(
                f"**{headline * 100:.0f}%** does not match any measure that can be calculated "
                "from these numbers. It may be the AUC or another measure. Check the paper "
                "to see what it means."
            )

    st.markdown("#### What would happen to 100 patients")
    counts = round_to_total([m["tp"], m["fn"], m["tn"], m["fp"]])
    labels = ["Correctly flagged", "Missed", "Correctly cleared", "False alarm"]
    colours = [COLOURS["tp"], COLOURS["fn"], COLOURS["tn"], COLOURS["fp"]]

    waffle = go.Figure()
    position = 0
    for n, label, colour in zip(counts, labels, colours):
        xs = [(position + i) % 10 for i in range(n)]
        ys = [9 - (position + i) // 10 for i in range(n)]
        position += n
        waffle.add_trace(
            go.Scatter(
                x=xs, y=ys, mode="markers", name=f"{label} ({n})",
                marker=dict(symbol="square", size=20, color=colour),
                hoverinfo="name",
            )
        )
    waffle.update_layout(
        height=420,
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(visible=False, range=[-0.7, 9.7]),
        yaxis=dict(visible=False, range=[-0.7, 9.7], scaleanchor="x"),
        legend=dict(orientation="h", y=-0.02),
        plot_bgcolor="white",
    )
    st.plotly_chart(waffle)

    said_negative = counts[1] + counts[2]
    st.caption(
        f"Each square is one patient. The AI says '{neg_word}' for {said_negative} of 100 patients, "
        f"and {counts[1]} of them are actually positive (red). "
        f"Correctly flagged = AI says '{pos_word}' and is right. "
        f"False alarm = AI says '{pos_word}' but is wrong."
    )

# ---------------------------------------------------------------------------
# Tab 2: change the setting
# ---------------------------------------------------------------------------
with tab2:
    st.subheader("Same AI, different setting")
    st.markdown(
        "The AI's sensitivity and specificity stay the same. Move the slider to use it "
        "in a group where positive cases are more or less common."
    )
    new_prev = st.slider("Prevalence in your setting (%)", 1, 99, 30, key="slider_" + k) / 100
    m2 = calc_metrics(se, sp, new_prev)

    c1, c2 = st.columns(2)
    c1.metric("PPV in your setting", pct(m2["ppv"]), delta=pts(m2["ppv"] - m["ppv"]))
    c2.metric("NPV in your setting", pct(m2["npv"]), delta=pts(m2["npv"] - m["npv"]))

    st.markdown(
        f"At **{new_prev * 100:.0f}%** prevalence:\n"
        f"- When the AI says **{pos_word}**, it is right about **{per100(m2['ppv'])} times in 100** "
        f"(study: {per100(m['ppv'])}).\n"
        f"- When the AI says **{neg_word}**, it is right about **{per100(m2['npv'])} times in 100** "
        f"(study: {per100(m['npv'])})."
    )

    xs, ppvs, npvs = prevalence_curve(se, sp)
    curve = go.Figure()
    curve.add_trace(go.Scatter(
        x=[x * 100 for x in xs], y=[v * 100 for v in ppvs], name="PPV",
        line=dict(color=COLOURS["ppv"], width=3),
    ))
    curve.add_trace(go.Scatter(
        x=[x * 100 for x in xs], y=[v * 100 for v in npvs], name="NPV",
        line=dict(color=COLOURS["npv"], width=3),
    ))
    curve.add_vline(x=prev * 100, line_dash="dash", line_color="grey",
                    annotation_text="Study", annotation_position="top")
    curve.add_vline(x=new_prev * 100, line_color="black",
                    annotation_text="Your setting", annotation_position="bottom")
    curve.update_layout(
        height=400,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(title="Prevalence (%)", range=[0, 100]),
        yaxis=dict(title="How often the AI is right (%)", range=[0, 101]),
        legend=dict(orientation="h", y=1.12),
        hovermode="x unified",
    )
    st.plotly_chart(curve)
    st.caption(
        "Assumption: sensitivity and specificity stay the same in the new setting. "
        "In real life they can change with different patients, scanners or hospitals."
    )

# ---------------------------------------------------------------------------
# Tab 3: check small subgroups
# ---------------------------------------------------------------------------
with tab3:
    st.subheader("How sure can we be about small groups?")
    st.markdown(
        "Enter how many cases the AI got right in each subgroup, and how many cases there were. "
        "You can edit the table and add rows."
    )

    table = pd.DataFrame(preset["subgroups"], columns=["Subgroup", "Correct (k)", "Total (n)"])
    edited = st.data_editor(
        table,
        num_rows="dynamic",
        key="subgroups_" + k,
        column_config={
            "Correct (k)": st.column_config.NumberColumn(min_value=0, step=1),
            "Total (n)": st.column_config.NumberColumn(min_value=1, step=1),
        },
    )

    rows = []
    skipped = []
    for _, r in edited.iterrows():
        name = "Unnamed" if pd.isna(r["Subgroup"]) else str(r["Subgroup"])
        try:
            k_right = int(r["Correct (k)"])
            n_total = int(r["Total (n)"])
        except (TypeError, ValueError):
            continue  # row not filled in yet
        if n_total <= 0 or k_right < 0 or k_right > n_total:
            skipped.append(name)
            continue
        low, high = wilson_ci(k_right, n_total)
        rows.append((name, k_right, n_total, k_right / n_total, low, high))

    if skipped:
        st.error("Check these rows (correct cases cannot be more than the total): " + ", ".join(skipped))

    if rows:
        ci_chart = go.Figure(go.Scatter(
            x=[r[3] * 100 for r in rows],
            y=[r[0] for r in rows],
            mode="markers",
            marker=dict(size=12, color=COLOURS["tp"]),
            error_x=dict(
                type="data", symmetric=False,
                array=[(r[5] - r[3]) * 100 for r in rows],
                arrayminus=[(r[3] - r[4]) * 100 for r in rows],
                thickness=2, width=8,
            ),
            hovertemplate="%{y}: %{x:.0f}%<extra></extra>",
        ))
        ci_chart.update_layout(
            height=140 + 60 * len(rows),
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(title="Rate (%) with 95% confidence interval", range=[0, 100]),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(ci_chart)

        for name, k_right, n_total, rate, low, high in rows:
            text = (
                f"**{name}**: {k_right} of {n_total} ({rate * 100:.0f}%). "
                f"The true rate could plausibly be anywhere from **{low * 100:.0f}% to {high * 100:.0f}%**."
            )
            if n_total < 30 or (high - low) > 0.20:
                st.warning(text + " This group is small, so treat the result with caution.")
            else:
                st.success(text + " This is a fairly precise estimate.")

    st.caption(
        "95% confidence intervals use the Wilson method, which works better than the "
        "simple formula for small groups."
    )

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown("---")
st.caption(
    "Built by Rowan (Liujun) Chen for DSH Hacks V2 · "
    "[Code on GitHub](https://github.com/RowanCCccc/behind-the-number)"
)
