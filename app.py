import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# --- 設定頁面資訊 ---
st.set_page_config(page_title="宇毛的財務中控台", page_icon="💰", layout="wide")

# --- CSS 美化 (RWD 手機版 + 自定義字卡) ---
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    .custom-card {
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 10px;
        transition: transform 0.2s;
    }
    .custom-card:hover {
        transform: translateY(-2px);
    }
    .card-title {
        font-size: 14px;
        color: #666;
        margin-bottom: 5px;
    }
    .card-value {
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 5px;
    }
    .card-note {
        font-size: 12px;
        font-weight: bold;
    }
    div[data-testid="stExpander"] {
        border: none;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 連接 Google Sheets (雲端/本機 雙棲版) ---
@st.cache_resource
def connect_to_gsheet():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    
    # 嘗試從 Streamlit 雲端秘密庫讀取
    if "gcp_service_account" in st.secrets:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    # 如果找不到，就嘗試讀取本機的 JSON 檔 (讓你電腦也能跑)
    else:
        creds = Credentials.from_service_account_file("credentials.json", scopes=scope)
        
    client = gspread.authorize(creds)
    sheet = client.open("宇毛的財務追蹤表_2026")
    return sheet

try:
    sh = connect_to_gsheet()
except Exception as e:
    st.error(f"❌ 連線失敗：{e}")
    st.stop()

# --- 側邊欄 ---
st.sidebar.title("🚀 功能選單")
page = st.sidebar.radio("請選擇功能", [
    "💸 隨手記帳 (本月)", 
    "🗓️ 歷史帳本回顧", 
    "🛍️ 購物冷靜清單", 
    "📊 資產與收支",
    "📅 未來推估"
])
st.sidebar.markdown("---")
st.sidebar.caption("宇毛的記帳本 v5.1 (History Visualized)")

# --- 讀取資料函式 ---
def get_data(worksheet_name, head=1):
    try:
        ws = sh.worksheet(worksheet_name)
        data = ws.get_all_records(head=head)
        return pd.DataFrame(data), ws
    except:
        return pd.DataFrame(), None

# --- 輔助函式：產生彩色卡片 HTML ---
def make_card_html(title, value, note, color_theme):
    colors = {
        "blue":   {"bg": "#e8f4f8", "border": "#3498db", "text": "#2980b9"},
        "red":    {"bg": "#fdedec", "border": "#e74c3c", "text": "#c0392b"}, 
        "green":  {"bg": "#eafaf1", "border": "#2ecc71", "text": "#27ae60"},
        "orange": {"bg": "#fef5e7", "border": "#f39c12", "text": "#d35400"},
        "gray":   {"bg": "#f4f6f7", "border": "#95a5a6", "text": "#7f8c8d"}
    }
    c = colors.get(color_theme, colors["gray"])
    
    return f"""
    <div class="custom-card" style="background-color: {c['bg']}; border-left: 5px solid {c['border']};">
        <div class="card-title">{title}</div>
        <div class="card-value" style="color: #2c3e50;">{value}</div>
        <div class="card-note" style="color: {c['text']};">{note}</div>
    </div>
    """

# ==========================================
# 🏠 頁面 1：隨手記帳 (本月)
# ==========================================
if page == "💸 隨手記帳 (本月)":
    current_month = datetime.now().month
    st.subheader(f"👋 嗨，宇毛！這是 {current_month} 月的帳本")
    
    # 預算邏輯
    if current_month == 2:
        monthly_budget = 97
    else:
        monthly_budget = 2207 
        
    df_log, ws_log = get_data("流動支出日記帳", head=4)
    df_status, _ = get_data("現況資金檢核")

    total_spent = 0
    current_month_logs = pd.DataFrame()
    
    if not df_log.empty:
        def get_month_from_date(date_str):
            try:
                for fmt in ("%m/%d", "%Y/%m/%d", "%Y-%m-%d"):
                    try:
                        return datetime.strptime(str(date_str), fmt).month
                    except:
                        continue
                return 0
            except:
                return 0

        df_log['Month'] = df_log['日期'].apply(get_month_from_date)
        current_month_logs = df_log[df_log['Month'] == current_month].copy()
        current_month_logs['實際消耗'] = pd.to_numeric(current_month_logs['實際消耗'], errors='coerce').fillna(0)
        total_spent = int(current_month_logs['實際消耗'].sum())
        
    remaining = monthly_budget - total_spent

    # --- 頂部儀表板 ---
    col1, col2, col3, col4 = st.columns(4)
    
    if remaining < 0:
        remaining_color = "red"
        remaining_note = "🛑 已透支 (危險)"
    elif remaining < 50:
        remaining_color = "red"
        remaining_note = "⚠️ 資金見底"
    else:
        remaining_color = "green"
        remaining_note = "✅ 資金安全"
    
    try:
        gap = df_status['數值 (B)'].iloc[-1]
    except:
        gap = "N/A"

    with col1:
        st.markdown(make_card_html(f"{current_month}月預算", f"${monthly_budget}", "當月額度", "blue"), unsafe_allow_html=True)
    with col2:
        st.markdown(make_card_html("本月已花", f"${total_spent}", "累積支出", "gray"), unsafe_allow_html=True)
    with col3:
        st.markdown(make_card_html("剩餘額度", f"${remaining}", remaining_note, remaining_color), unsafe_allow_html=True)
    with col4:
        st.markdown(make_card_html("總透支缺口", f"{gap}", "需長期填補", "orange"), unsafe_allow_html=True)

    if remaining < 0:
        st.error(f"🚨 {current_month}月已透支！請立即停止支出！")
    elif remaining < 50:
        st.warning("⚠️ 資金即將見底！")

    st.markdown("---")

    # --- 記帳輸入區 ---
    with st.container():
        st.write("📝 **新增消費**")
        with st.form("expense_form", clear_on_submit=True):
            c1, c2 = st.columns([1, 2])
            date_input = c1.date_input("日期", datetime.now())
            item_input = c2.text_input("項目")
            
            c3, c4 = st.columns(2)
            amount_input = c3.number_input("金額", min_value=0, step=1)
            is_reimbursable = c4.radio("報帳?", ["否", "是"], horizontal=True)
            
            submitted = st.form_submit_button("💰 確認記帳", use_container_width=True)

            if submitted and ws_log:
                if item_input and amount_input > 0:
                    date_str = date_input.strftime("%m/%d")
                    actual_cost = 0 if is_reimbursable == "是" else amount_input
                    ws_log.append_row([date_str, item_input, amount_input, is_reimbursable, actual_cost])
                    st.toast(f"✅ 已儲存")
                    st.rerun()

    # --- 本月紀錄 ---
    if not current_month_logs.empty:
        st.markdown(f"### 📜 {current_month} 月消費明細")
        recent_logs = current_month_logs.tail(5).iloc[::-1]
        
        for index, row in recent_logs.iterrows():
            with st.container():
                cost = row['實際消耗']
                color = "#e74c3c" if cost > 0 else "#95a5a6"
                
                st.markdown(f"""
                <div style="background-color: white; padding: 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                    <div>
                        <span style="color: #888; font-size: 0.8em;">{row['日期']}</span><br>
                        <span style="font-weight: bold; font-size: 1.1em; color: #333;">{row['項目']}</span>
                    </div>
                    <div style="text-align: right;">
                         <span style="color: {color}; font-weight: bold; font-size: 1.2em;">${row['金額']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info(f"📅 {current_month} 月還沒有任何消費紀錄。")

# ==========================================
# 🗓️ 頁面 2：歷史帳本回顧 (視覺化升級版)
# ==========================================
elif page == "🗓️ 歷史帳本回顧":
    st.subheader("🗓️ 歷史帳本查詢")
    
    df_log, _ = get_data("流動支出日記帳", head=4)
    
    if not df_log.empty:
        # 日期解析
        def get_month(x):
            try:
                for fmt in ("%m/%d", "%Y/%m/%d", "%Y-%m-%d"):
                    try:
                        return datetime.strptime(str(x), fmt).month
                    except:
                        continue
                return 0
            except:
                return 0

        df_log['Month'] = df_log['日期'].apply(get_month)
        
        # 找出可用月份
        available_months = sorted(df_log['Month'].unique())
        available_months = [m for m in available_months if m > 0]
        
        if available_months:
            # 讓使用者選擇月份 (預設選最後一個，即最新月份)
            selected_month = st.selectbox("請選擇月份", available_months, index=len(available_months)-1)
            
            # 篩選該月資料
            history_df = df_log[df_log['Month'] == selected_month].copy()
            
            # 計算該月數據
            history_df['實際消耗'] = pd.to_numeric(history_df['實際消耗'], errors='coerce').fillna(0)
            month_total = int(history_df['實際消耗'].sum())
            
            # 歷史預算判斷 (2月是97, 其他月預設2207)
            hist_budget = 97 if selected_month == 2 else 2207
            hist_balance = hist_budget - month_total
            
            # 狀態判斷
            if hist_balance < 0:
                status_color = "red"
                status_text = "🛑 超支了"
                balance_display = f"-${abs(hist_balance)}"
            else:
                status_color = "green"
                status_text = "✅ 資金安全"
                balance_display = f"${hist_balance}"

            # --- 歷史摘要儀表板 ---
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(make_card_html(f"{selected_month}月預算", f"${hist_budget}", "設定額度", "blue"), unsafe_allow_html=True)
            with c2:
                st.markdown(make_card_html("總支出", f"${month_total}", "實際花費", "gray"), unsafe_allow_html=True)
            with c3:
                st.markdown(make_card_html("結餘狀態", balance_display, status_text, status_color), unsafe_allow_html=True)
            
            st.markdown("---")
            st.markdown(f"### 📜 {selected_month} 月消費明細")

            # --- 歷史明細 (改用卡片顯示，非表格) ---
            # 反轉順序，讓該月最後一筆在最上面
            for index, row in history_df.iloc[::-1].iterrows():
                with st.container():
                    cost = row['實際消耗']
                    # 顏色邏輯：有花錢是紅色，報帳/0元是灰色
                    color = "#e74c3c" if cost > 0 else "#95a5a6"
                    
                    st.markdown(f"""
                    <div style="background-color: white; padding: 12px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.05);">
                        <div>
                            <span style="color: #888; font-size: 0.8em;">{row['日期']}</span><br>
                            <span style="font-weight: bold; font-size: 1.1em; color: #333;">{row['項目']}</span>
                        </div>
                        <div style="text-align: right;">
                             <span style="color: {color}; font-weight: bold; font-size: 1.2em;">${row['金額']}</span>
                             <br><span style="font-size: 0.8em; color: #aaa;">{ '報帳' if row['是否報帳'] == '是' else '自費' }</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        else:
            st.warning("目前沒有有效的歷史資料。")
    else:
        st.info("日記帳是空的。")

# ==========================================
# 🛍️ 頁面 3：購物冷靜清單
# ==========================================
elif page == "🛍️ 購物冷靜清單":
    st.subheader("🧊 購物冷靜清單")
    df_shop, ws_shop = get_data("購物冷靜清單")

    with st.expander("➕ 我想買東西 (點擊展開)", expanded=False):
        with st.form("shopping_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            s_name = col_a.text_input("物品名稱")
            s_price = col_b.number_input("價格", min_value=0)
            
            s_decision = st.selectbox("決策", ["延後 (推薦)", "考慮中", "必買"])
            s_note = st.text_input("備註")
            
            if st.form_submit_button("加入清單", use_container_width=True):
                if ws_shop:
                    row = [
                        datetime.now().strftime("%m/%d"), 
                        s_name, 
                        s_price, 
                        "3 (普通)", 
                        "2026/07/01", 
                        s_decision, 
                        s_note
                    ]
                    ws_shop.append_row(row)
                    st.success("已加入！")
                    st.rerun()

    st.markdown("### 📦 願望清單")
    if not df_shop.empty:
        for index, row in df_shop.iterrows():
            item_name = row.get('物品名稱', row.get('物品名稱 (B)', '未知'))
            price = row.get('預估價格', row.get('預估價格 (C)', 0))
            decision = row.get('最終決策', row.get('最終決策 (G)', '未知'))
            note = row.get('備註', row.get('理由與備註 (H)', '無'))

            status_color = "red" if decision == "延後" else "green"
            
            with st.expander(f"🛒 **{item_name}** - ${price}"):
                st.markdown(f"**決策：** :{status_color}[{decision}]")
                st.info(f"💡 {note}")
    else:
        st.info("清單是空的！")

# ==========================================
# 📊 頁面 4：資產與收支
# ==========================================
elif page == "📊 資產與收支":
    st.subheader("💰 資產概況")
    
    df_assets, _ = get_data("資產總覽表")
    if not df_assets.empty:
        df_assets['目前價值'] = df_assets['目前價值'].astype(str).str.replace(',', '')
        df_assets['目前價值'] = pd.to_numeric(df_assets['目前價值'], errors='coerce').fillna(0)
        
        total_row = df_assets[df_assets['資產項目'] == '總資產']
        if not total_row.empty:
            total_val = int(total_row['目前價值'].values[0])
            st.markdown(make_card_html("目前總身價", f"${total_val:,}", "含台幣/日幣/定存", "blue"), unsafe_allow_html=True)
        
        df_chart = df_assets[df_assets['資產項目'] != '總資產']
        st.bar_chart(df_chart.set_index('資產項目')['目前價值'])

    st.markdown("---")
    st.subheader("📉 收支結構")
    df_model, _ = get_data("每月收支模型")
    if not df_model.empty:
        for i, row in df_model.iterrows():
            amt = str(row.get('金額 (B)', row.get('金額', 0)))
            item = row.get('項目 (A)', row.get('項目', '未知'))
            if amt.startswith('-'):
                st.write(f"🔴 **{item}**: ${amt}")
            elif '收入' in item:
                st.write(f"🟢 **{item}**: ${amt}")

# ==========================================
# 📅 頁面 5：未來推估
# ==========================================
elif page == "📅 未來推估":
    st.subheader("🔮 財務預測")
    
    df_future, _ = get_data("未來四個月推估")
    if not df_future.empty:
        try:
            chart_df = df_future[['月份 (A)', '預估實際餘額 (D)', '目標應有餘額 (E)']].copy()
            for col in chart_df.columns[1:]:
                chart_df[col] = pd.to_numeric(chart_df[col], errors='coerce')
            
            st.line_chart(chart_df.set_index('月份 (A)'))
            
            last = chart_df.iloc[-1]
            st.markdown(make_card_html(f"{last['月份 (A)']} 預估結餘", f"${int(last['預估實際餘額 (D)'])}", "財務轉正", "green"), unsafe_allow_html=True)
        except:
            st.warning("資料格式異常")