import streamlit as st, requests

st.set_page_config(page_title="KOL Matrix Optimizer", page_icon="🎯")
st.title(" TikTok Shop KOL Matrix Optimizer")

budget   = st.slider("Marketing Budget (USD)", 500, 20000, 5000, step=500)
country  = st.selectbox("Target Country", ["MY", "ID", "TH", "PH"])
category = st.selectbox("Product Category", ["beauty", "tech", "fashion"])

if st.button("Run Optimization ▶"):
    with st.spinner("Simulated Annealing running..."):
        r = requests.post("http://localhost:8000/optimize",
                          json={"budget": budget, "country": country, "category": category})
    if r.status_code == 200:
        data = r.json()
        st.success(f"Total GMV: **${data['total_gmv']:,.0f}** | Budget used: **${data['total_cost']:,.0f}**")
        if data["selected_kols"]:
            st.dataframe(data["selected_kols"])
        else:
            st.warning("No KOLs found for the given criteria.")
    else:
        st.error(f"Error connecting to backend: {r.text}")
