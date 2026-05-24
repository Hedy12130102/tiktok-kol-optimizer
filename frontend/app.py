# pyrefly: ignore [missing-import]
import pandas as pd
import requests
import streamlit as st


API_URL = "http://localhost:8000/optimize"

st.set_page_config(page_title="TikTok KOL Matrix Optimizer", layout="wide")

st.title("TikTok Shop KOL Matrix Optimizer")
st.caption("Local Search & Optimization: Hill Climber vs Simulated Annealing")

with st.sidebar:
    st.header("Campaign Settings")
    budget = st.slider("Marketing budget (USD)", 500, 20000, 5000, step=500)
    country = st.selectbox("Target country", ["MY", "ID", "TH", "PH"])
    category = st.selectbox("Product category", ["beauty", "tech", "fashion"])
    seed = st.number_input("Random seed", min_value=0, max_value=9999, value=42, step=1)
    run = st.button("Run optimization", type="primary", use_container_width=True)

if not run:
    st.info("Choose a budget and market segment, then run the optimizer.")
    st.stop()

try:
    with st.spinner("Searching for the best KOL matrix..."):
        response = requests.post(
            API_URL,
            json={
                "budget": budget,
                "country": country,
                "category": category,
                "seed": seed,
            },
            timeout=60,
        )
        response.raise_for_status()
except requests.RequestException as exc:
    st.error(f"Backend request failed: {exc}")
    st.stop()

data = response.json()
if data["candidates"] == 0:
    st.warning("No KOL candidates found for this country and category.")
    st.stop()

metric_cols = st.columns(5)
metric_cols[0].metric("Best algorithm", data["best_algorithm"])
metric_cols[1].metric("Predicted GMV", f"${data['total_gmv']:,.0f}")
metric_cols[2].metric("Budget used", f"${data['total_cost']:,.0f}", f"{data['total_cost'] / budget:.1%}")
metric_cols[3].metric("Selected KOLs", len(data["selected_kols"]))
metric_cols[4].metric("Candidates", data["candidates"])

results = data["results"]
summary_df = pd.DataFrame(
    [
        {
            "Algorithm": result["algorithm"],
            "Selected KOLs": result["selected_count"],
            "Budget Used": result["total_cost"],
            "Predicted GMV": result["total_gmv"],
            "ROI": result["roi"],
        }
        for result in results.values()
    ]
).sort_values("Predicted GMV", ascending=False)

st.subheader("Algorithm Comparison")
st.dataframe(
    summary_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Budget Used": st.column_config.NumberColumn(format="$%.0f"),
        "Predicted GMV": st.column_config.NumberColumn(format="$%.0f"),
        "ROI": st.column_config.NumberColumn(format="%.2f"),
    },
)

history = {}
min_len = min(len(result["history"]) for result in results.values())
for result in results.values():
    history[result["algorithm"]] = result["history"][:min_len]

st.subheader("Convergence Curve")
st.line_chart(pd.DataFrame(history))

st.subheader("Best KOL Matrix")
selected_df = pd.DataFrame(data["selected_kols"])
if selected_df.empty:
    st.warning("The best feasible solution selected no KOLs under this budget.")
else:
    selected_df = selected_df.sort_values("expected_gmv", ascending=False)
    st.dataframe(
        selected_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "cost": st.column_config.NumberColumn("cost", format="$%.0f"),
            "expected_gmv": st.column_config.NumberColumn("expected_gmv", format="$%.0f"),
            "engagement_rate": st.column_config.NumberColumn("engagement_rate", format="%.2%"),
            "fit_score": st.column_config.ProgressColumn("fit_score", min_value=0, max_value=1),
        },
    )
