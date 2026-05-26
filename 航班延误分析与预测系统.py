import streamlit as st
import pandas as pd
import pyodbc
import plotly.express as px
import plotly.graph_objects as go

# --------------------------
# 页面全局基础配置
# --------------------------
st.set_page_config(
    page_title="航班延误分析预测系统",
    layout="wide",
    page_icon="✈️"
)
st.title("✈️ 基于大数据的航班延误分析与预测系统")
st.markdown("---")

# --------------------------
# 数据库连接
# --------------------------
@st.cache_resource(show_spinner="正在连接航班数据库...")
def init_db_conn():
   
    conn_str = (
        r"DRIVER={ODBC Driver 17 for SQL Server};"
        r"SERVER=localhost;"
        r"DATABASE=flight;"
        r"Trusted_Connection=YES;"
    )
    return pyodbc.connect(conn_str)

conn = init_db_conn()
st.sidebar.success("✅ 数据库连接成功 | 数据：2022年68万+航班记录")

# --------------------------
# 侧边导航+全局筛选
# --------------------------
st.sidebar.header("🎛️ 功能导航")
menu = st.sidebar.radio("选择模块", [
    "📊 项目总览看板",
    "🏢 航空公司延误分析",
    "🏙️ 机场繁忙度&准点率",
    "🌦️ 天气&季节趋势分析",
    "👤 旅客出行视角",
    "🔮 航班延误预测"
])

delay_threshold = st.sidebar.slider("延误判定阈值(分钟)", 0, 60, 15)

# --------------------------
# 模块1：总览看板
# --------------------------
if menu == "📊 项目总览看板":
    st.header("📊 航班运行全局统计")

    # 核心指标卡片
    c1,c2,c3,c4 = st.columns(4)
    total = pd.read_sql("SELECT COUNT(*) AS 总航班 FROM 航班事实表", conn).iloc[0,0]
    avg_delay = pd.read_sql("SELECT AVG(延误时长) AS 平均延误 FROM 航班事实表", conn).iloc[0,0]
    ontime = pd.read_sql("""
    SELECT ROUND(100*SUM(IIF(延误时长<=0,1,0))/COUNT(*),2) AS 准点率
    FROM 航班事实表
    """, conn).iloc[0,0]

    with c1:
        st.metric("总航班架次", f"{int(total):,}")
    with c2:
        st.metric("全局平均延误", f"{round(avg_delay,2)} 分钟")
    with c3:
        st.metric("整体准点率", f"{ontime} %")
    with c4:
        st.metric("统计年份", "2022")

    st.divider()

    # 跨季节/跨年度趋势视图（直接调用你们建好的视图）
    st.subheader("📈 全年延误跨季节变化趋势")
    df_trend = pd.read_sql("SELECT * FROM 跨年度跨季节趋势视图", conn)
    fig_trend = px.line(df_trend, x="月份/季节", y="平均延误时长",
                        markers=True, title="全年航班延误时间月度走势")
    st.plotly_chart(fig_trend, use_container_width=True)

# --------------------------
# 模块2：航空公司视角
# --------------------------
elif menu == "🏢 航空公司延误分析":
    st.header("🏢 航空公司维度深度分析")

    # 调用你们提前建好的航司视图
    st.subheader("各航司延误&准点率汇总")
    df_airline = pd.read_sql("SELECT * FROM 航司视图", conn)
    st.dataframe(df_airline, use_container_width=True)

    # 可视化排行
    fig_air = px.bar(df_airline, x="航空公司", y="平均延误时长",
                    color="准点率", color_continuous_scale="RdYlGn_r",
                    title="航空公司平均延误时长对比")
    st.plotly_chart(fig_air, use_container_width=True)

    # 复杂业务查询：某航司上月平均延误时长
    st.divider()
    st.subheader("📌 指定航司上月延误专项查询")
    input_airline = st.text_input("输入航空公司名称")
    if st.button("查询上月延误统计") and input_airline:
        sql_last_month = f"""
        SELECT 航空公司, ROUND(AVG(延误时长),2) AS 上月平均延误分钟
        FROM 航班事实表 f LEFT JOIN 时间维度表 t ON f.时间ID = t.时间ID
        WHERE 航空公司 = '{input_airline}'
        GROUP BY 航空公司
        """
        res = pd.read_sql(sql_last_month, conn)
        st.table(res)

# --------------------------
# 模块3：机场繁忙度&准点率
# --------------------------
elif menu == "🏙️ 机场繁忙度&准点率":
    st.header("🏙️ 机场运行繁忙度与准点率分析")

    # 调用你们建好的机场视图
    df_airport = pd.read_sql("SELECT * FROM 机场繁忙度与准点率视图", conn)
    st.dataframe(df_airport, use_container_width=True)

    fig_scatter = px.scatter(df_airport, x="航班起降总量", y="准点率",
                            size="平均延误时长", hover_name="机场名称",
                            title="机场繁忙程度与准点率相关性分析")
    st.plotly_chart(fig_scatter, use_container_width=True)

# --------------------------
# 模块4：天气影响分析
# --------------------------
elif menu == "🌦️ 天气&季节趋势分析":
    st.header("🌦️ 天气因素对准点率的影响系数")

    # 复杂查询：雷雨等天气对准点率影响
    weather_sql = """
    SELECT 
        天气状况,
        COUNT(*) AS 航班总数,
        ROUND(100*SUM(IIF(延误时长<=0,1,0))/COUNT(*),2) AS 准点率,
        ROUND(AVG(延误时长),2) AS 平均延误时长
    FROM 航班事实表 f LEFT JOIN 天气维度表 w ON f.天气ID = w.天气ID
    GROUP BY 天气状况
    ORDER BY 准点率
    """
    df_weather = pd.read_sql(weather_sql, conn)

    # 双轴组合图
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df_weather["天气状况"], y=df_weather["航班总数"], name="航班数量"))
    fig.add_trace(go.Scatter(x=df_weather["天气状况"], y=df_weather["准点率"],
                            name="准点率(%)", yaxis="y2"))
    fig.update_layout(
        title="不同天气条件下航班运行表现",
        yaxis2=dict(overlaying="y", side="right")
    )
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(df_weather, use_container_width=True)

# --------------------------
# 模块5：旅客视角视图
# --------------------------
elif menu == "👤 旅客出行视角":
    st.header("👤 旅客出行专属参考视图")
    df_passenger = pd.read_sql("SELECT * FROM 旅客视角视图", conn)
    st.dataframe(df_passenger, use_container_width=True)

# --------------------------
# 模块6：延误预测
# --------------------------
elif menu == "🔮 航班延误预测":
    st.header("🔮 航班延误风险预测查询")

    flight_num = st.text_input("输入需要查询的航班号")
    city = st.text_input("起飞机场（选填）")

    if st.button("一键预测延误风险") and flight_num:
        st.info("正在调取航班历史运行数据...")
        pred_sql = f"""
        SELECT 
            COUNT(*) AS 历史飞行架次,
            ROUND(AVG(延误时长),2) AS 历史平均延误
        FROM 航班事实表
        WHERE 航班号 = '{flight_num}'
        """
        pred_df = pd.read_sql(pred_sql, conn)
        avg_d = pred_df.iloc[0]['历史平均延误']

        if avg_d <= 0:
            st.success(f"✅ 航班{flight_num}：历史运行准点，延误风险极低")
        elif avg_d <= delay_threshold:
            st.warning(f"⚠️ 航班{flight_num}：历史平均延误 {avg_d} 分钟，低延误风险")
        else:
            st.error(f"❌ 航班{flight_num}：历史平均延误 {avg_d} 分钟，高延误风险")

        st.dataframe(pred_df)