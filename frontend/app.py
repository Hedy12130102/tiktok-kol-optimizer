import pandas as pd
import requests
import streamlit as st
import plotly.express as px
def get_tier(followers):
    if followers>1000000:
        return "Mega"
    elif followers>100000:
        return "Macro"
    elif followers>10000:
        return "Micro"
    else:
        return "Nano"
def badge_color(tier):
    colors={
        "Mega":"#9b59b6",
        "Macro":"#3498db",
        "Micro":"#2ecc71",
        "Nano":"#f1c40f"
    }
    color=colors.get(tier,"#95a5a6")
    return f'<span style="background-color:{color};color:white;padding:2px 8px;border-radius:12px;font-size:12px">{tier}</span>'
st.set_page_config(page_title="Tiktok Shop KOL Matrix System",layout="wide")
API_URL = "http://localhost:8000"
st.markdown("<h1 style='text-align:center'>Tiktok Shop KOL Matrix System</h1>",unsafe_allow_html=True)
try:
    health=requests.get(f"{API_URL}/health")
    health.raise_for_status()
    st.success("Backend connected.")
except:
    st.error("Backend unavailable. Make sure uvicorn is runing.")
with st.sidebar:
    st.header("Configuration")
    budget=st.number_input("Budget(USD)",min_value=1,value=50000,step=5000)
    country=st.selectbox("Country",["MY","ID","TH","PH"])
    category=st.selectbox("Category",["beauty","tech","fashion"])
    if st.button("Check",type="primary",key="optimize_bt"):
        with st.spinner("Computing..."):
            try:
                payload={
                    "budget":budget,
                    "country":country,
                    "category":category,
                    "seed":42
                }
                response=requests.post(f"{API_URL}/optimize",json=payload,timeout=60)
                response.raise_for_status()
                data=response.json()
                if data.get("candidates",0)==0:
                    st.session_state.pop("results",None)
                    st.warning("No KOL was found for this filter combination. Please try different country/category.")
                else:
                    st.session_state["results"]=data
                st.success("Backend connected successfully.")
            except requests.exceptions.ConnectionError:
                st.error("Backend unavailable. Make sure uvicorn is runing.")
            except requests.exceptions.Timeout:
                st.error("Request timeout. Please try again.")
            except requests.exceptions.HTTPError:
                st.error(f"HTTP error: {response.status_code}.")
            except Exception as e:
                st.error(f"Unexcepted error: {e}.")
tab1,tab2,tab3=st.tabs(["Selected KOLs","Chart Analysis","Scalability Analysis"])
if "results" in st.session_state:
    results=st.session_state["results"]
    with tab1:
        reason_list=[]
        df=pd.DataFrame(results["selected_kols"])
        df["tier"]=df["followers"].apply(get_tier)
        df["badge"]=df["tier"].apply(badge_color)
        display_df=df[["name","followers","badge","cost","expected_gmv"]].copy()
        display_df.columns=["Name","Followers","Tier","Cost(USD)","Expected GMV(USD)"]
        st.markdown("<h3 style='text-align:center'>Selected KOLs</h3>",unsafe_allow_html=True)
        st.write(display_df.to_html(escape=False,index=False),unsafe_allow_html=True)
        st.markdown("<h3 style='text-align:center'>KOL Details</h3>",unsafe_allow_html=True)
        for kol in results["selected_kols"]:
            temp_r=[]
            r=kol.get("reasons",[])
            for i in r:
                temp_r.append(f"✅ {i}")
            n=kol["name"]
            reason_list.append({"name":n,"reason":temp_r})
            with st.expander(f'{kol["name"]} -- Followers:{kol["followers"]:,}'):
                col1,col2=st.columns(2)
                with col1:
                    st.metric("Followers",f"{kol['followers']:,}")
                    st.metric("Fit Score",f"{kol['fit_score']:.2f}")
                    st.metric("Cost",f"${kol['cost']:.2f}")
                with col2:
                    st.metric("Engagement Rate",f"{kol['engagement_rate']:.2f}")
                    st.metric("Expected GMV",f"${kol['expected_gmv']:.2f}")
                    st.metric("Tier",get_tier(kol["followers"]))
        st.markdown("<h3 style='text-align:center'>Reasons:</h3>",unsafe_allow_html=True)
        for i,v in enumerate(reason_list):
            st.write(f'{i+1}. {v["name"]}: ')
            for j in v["reason"]:
                st.write(f"{j}")

    with tab2:
        local_search_results = {
            k: v for k, v in results["results"].items()
            if k in ["simulated_annealing", "hill_climber"]
        }
        recommended_key = max(
            local_search_results,
            key=lambda k: local_search_results[k]["total_gmv"]
        )
        recommended_name = {
            "simulated_annealing": "Simulated Annealing",
            "hill_climber": "Hill Climber",
        }.get(recommended_key, results["best_algorithm"])
        col1,col2,col3=st.columns(3)
        with col1:
            st.metric("Recommended Algorithm", recommended_name)
        with col2:
            st.metric("Total GMV",f"${results['total_gmv']:.0f}")
        with col3:
            st.metric("ROI",f"{results['roi']:.2f}x")
        st.divider()
        name_change={
            "simulated_annealing":"Simulated Annealing",
            "hill_climber":"Hill Climber",
            "random_search":"Random Search"
        }
        roi_al=[]
        for k,v in results["results"].items():
            display_name=name_change.get(k,k)
            roi_al.append({
                "Algorithm":display_name,
                "ROI":v["roi"]
            })
        roi_df=pd.DataFrame(roi_al)
        fig_bar=px.bar(roi_df,x="Algorithm",y="ROI",text="ROI",color="Algorithm",title="Algorithm comparison")
        fig_bar.update_traces(texttemplate='%{text:.2f}x',textposition='outside')
        fig_bar.update_layout(showlegend=False)
        st.plotly_chart(fig_bar,use_container_width=True)
        df=pd.DataFrame(results["selected_kols"])
        df["tier"]=df["followers"].apply(get_tier)
        tier_count=df["tier"].value_counts().reset_index()
        tier_count.columns=(["Tier","Count"])
        if not tier_count.empty:
            fig_pie=px.pie(tier_count,values="Count",names="Tier",color="Tier",
                color_discrete_map={"Mega":"#9b59b6","Macro":"#3498db",
                "Micro":"#2ecc71","Nano":"#f1c40f"},title="Tier Distribution")
            fig_pie.update_traces(textposition="inside",textinfo="percent+label")
            fig_pie.update_layout(showlegend=False)
            st.plotly_chart(fig_pie,use_container_width=True)
else:
    with tab1:
        st.info("Configure parameters on the left and click 'check' button.")
    with tab2:
        st.info("Configure parameters on the left and click 'check' button.")
with tab3:
    test_budget=st.number_input("Budget",min_value=1,value=50000,step=5000)
    n_size=st.slider("KOL Pool Size",min_value=10,max_value=500,value=100,step=10,help="Test algorithm performance with different pool sizes.")
    if st.button("Check",type="primary",key="scalability_bt"):
        with st.spinner("Analysing..."):
            try:
                payload={
                    "n":n_size,
                    "budget":test_budget,
                    "seed":42
                }
                response=requests.post(f"{API_URL}/scalability",json=payload,timeout=120)
                response.raise_for_status()
                scal_data=response.json()
                st.session_state["scalability"]=scal_data
                st.success("Backend connected successfully.")
            except requests.exceptions.ConnectionError:
                st.error("Backend unavailable. Make sure uvicorn is runing.")
            except requests.exceptions.Timeout:
                st.error("Request timeout. Please try again.")
            except requests.exceptions.HTTPError:
                st.error(f"HTTP error: {response.status_code}.")
            except Exception as e:
                st.error(f"Unexcepted error: {e}.")
        if "scalability" in st.session_state:
            data=[]
            scal_data=st.session_state["scalability"]
            display_name=["Simulated Annealing","Hill Climber","Random Search"]
            back_name=["simulated_annealing","hill_climber","random_search"]
            for name,key in zip(display_name,back_name):
                if key in scal_data:
                    data.append({"Algorithm":name,"Time(Seconds)":scal_data[key]["time_seconds"],
                                 "GMV":scal_data[key]["total_gmv"],"ROI":scal_data[key]["roi"],
                                 "Selected":scal_data[key]["selected_count"]})
            if data:
                col1,col2=st.columns(2)
                df_scal=pd.DataFrame(data)
                with col1:
                    fig_time=px.bar(df_scal,x="Algorithm",y="Time(Seconds)",text="Time(Seconds)",color="Algorithm",title=f"Execution Time at Pool Size {n_size}")
                    fig_time.update_traces(texttemplate="%{text:.3f}s",textposition="outside")
                    st.plotly_chart(fig_time,use_container_width=True)
                with col2:
                    fig_gmv=px.bar(df_scal,x="Algorithm",y="GMV",text="GMV",color="Algorithm",title="GMV found by each algorithm")
                    fig_gmv.update_traces(texttemplate="%{text:,.0f}",textposition="outside")
                    st.plotly_chart(fig_gmv,use_container_width=True)
                st.divider()
                with st.expander("Detailed Performance Data"):
                    st.dataframe(df_scal,use_container_width=True)
                    best_time=df_scal.loc[df_scal["Time(Seconds)"].idxmin(),"Algorithm"]
                    best_gmv=df_scal.loc[df_scal["GMV"].idxmax(),"Algorithm"]
                    st.info(f"\nFastest Algorithm:{best_time}")
                    st.info(f"\nBest GMV Algorithm:{best_gmv}")
            else:
                st.warning("No scalability data available.")
        else:
            st.error("Error")
    else:
        st.info("Set Pool Size and Budget above and click 'check' button.")
