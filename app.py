import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time # 用於刪除後的延遲重整

# --- 設定頁面資訊 ---
st.set_page_config(page_title="宇毛的財務中控台", page_icon="💰", layout="wide")

# --- CSS 美化 (v8.0 購物管理版) ---
st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 5rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* 通用卡片 */
    .custom-card {
        padding: 12px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
        border: 1px solid #f0f0f0;
        background-color: white;
        overflow: hidden; 
    }
    .card-title {
        font-size: 13px;
        color: #666;
        margin-bottom: 2px;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .card-value {
        font-size: 22px;
        font-weight: bold;
        color: #2c3e50;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .card-note {
        font-size: 12px;
        font-weight: bold;
        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    
    /* 資產專用小卡 */
    .asset-card {
        background-color: #f8f9fa;
        border-left: 4px solid #6c757d;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .asset-val { font-size: 20px; font-weight: bold; color: #2c3e50; }
    .asset-lbl { font-size: 12px; color: #666; }

    /* 底部總結專用區塊 (深色模式) */
    .summary-box {
        background-color: #2c3e50;
        color: white;
        padding: 20px;
        border-radius: 15px;
        margin-top: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.2);
    }
    .summary-title { font-size: 14px; opacity: 0.8; }
    .summary-val { font-size: 28px; font-weight: bold; color: #f1c40f; }
    
    /* 未來推估卡片 */
    .future-card {
        background-color: white;
        border: 1px solid #eee;
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        height: 100%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* 刪除按鈕區塊 */
    .delete-section {
        margin-top: 10px;
        padding-top: 10px;
        border-top: 1px dashed #eee;
        text-align: right;
    }
</style>
""", unsafe_allow_html=True)

# --- 連接 Google Sheets ---
@st.cache_resource
def connect_to_gsheet():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    if "gcp_service_account" in st.secrets:
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
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
    "🛍️ 購物冷靜清單", 
    "📊 資產與收支",
    "📅 未來推估",
    "🗓️ 歷史帳本回顧"
])
st.sidebar.markdown("---")
st.sidebar.caption("宇毛的記帳本 v8.0 (Shopping Manager)")

# --- 讀取資料函式 ---
def get_data(worksheet_name, head=1):
    try:
        ws = sh.worksheet(worksheet_name)
        data = ws.get_all_records(head=head)
        return pd.DataFrame(data), ws
    except:
        return pd.DataFrame(), None

# --- HTML 卡片生成器 ---
def make_card_html(title, value, note, color_theme):
    colors = {
        "blue":   {"bg": "#e8f4f8", "border": "#3498db", "text": "#2980b9"},
        "red":    {"bg": "#fdedec", "border": "#e74c3c", "text": "#c0392b"}, 
        "green":  {"bg": "#eafaf1", "border": "#2ecc71", "text": "#27ae60"},
        "orange": {"bg": "#fef5e7", "border": "#f39c12", "text": "#d35400"},
        "gray":   {"bg": "#f4f6f7", "border": "#95a5a6", "text": "#7f8c8d"},
        "purple": {"bg": "#f3e5f5", "border": "#8e44ad", "text": "#8e44ad"}
    }
    c = colors.get(color_theme, colors["gray"])
    return f"""
    <div class="custom-card" style="background-color: {c['bg']}; border-left: 5px solid {c['border']};">
        <div class="card-title">{title}</div>
        <div class="card-value">{value}</div>
        <div class="card-note" style="color: {c['text']};">{note}</div>
    </div>
    """

# ==========================================
# 🏠 頁面 1：隨手記帳 (優先填坑邏輯)
# ==========================================
if page == "💸 隨手記帳 (本月)":
    current_month = datetime.now().month
    st.subheader(f"👋 {current_month} 月財務面板")
    
    base_budget = 97 if current_month == 2 else 2207
    
    df_log, ws_log = get_data("流動支出日記帳", head=4)
    df_assets, ws_assets = get_data("資產總覽表")
    df_status, _ = get_data("現況資金檢核")

    try:
        gap_str = str(df_status['數值 (B)'].iloc[-1]).replace(',', '')
        current_gap = int(float(gap_str))
    except:
        current_gap = -9999

    total_expenses_only = 0
    current_month_logs = pd.DataFrame()
    
    if not df_log.empty:
        df_log['Month'] = pd.to_datetime(df_log['日期'], format='%m/%d', errors='coerce').dt.month
        df_log['Month'] = df_log['Month'].fillna(0).astype(int)
        
        current_month_logs = df_log[df_log['Month'] == current_month].copy()
        current_month_logs['實際消耗'] = pd.to_numeric(current_month_logs['實際消耗'], errors='coerce').fillna(0)
        total_expenses_only = int(current_month_logs[current_month_logs['實際消耗'] > 0]['實際消耗'].sum())

    surplus_from_gap = max(0, current_gap)
    remaining = (base_budget + surplus_from_gap) - total_expenses_only

    col1, col2, col3, col4 = st.columns(4)
    
    if current_gap < 0:
        gap_status = "📉 填坑中..."
        gap_color = "orange"
        gap_note = "收入優先抵債"
    else:
        gap_status = "🎉 已轉正"
        gap_color = "green"
        gap_note = f"溢出 +${surplus_from_gap} 至額度"

    if remaining < 0:
        rem_color = "red"
        rem_note = "🛑 已透支"
    elif remaining < 50:
        rem_color = "red"
        rem_note = "⚠️ 資金見底"
    else:
        rem_color = "green"
        rem_note = "✅ 資金安全"

    with col1:
        st.markdown(make_card_html(f"{current_month}月本金", f"${base_budget}", "固定額度", "blue"), unsafe_allow_html=True)
    with col2:
        st.markdown(make_card_html("本月花費", f"${total_expenses_only}", "不含收入", "gray"), unsafe_allow_html=True)
    with col3:
        st.markdown(make_card_html("目前可用", f"${remaining}", rem_note, rem_color), unsafe_allow_html=True)
    with col4:
        st.markdown(make_card_html("總透支缺口", f"${current_gap}", gap_note, gap_color), unsafe_allow_html=True)

    if current_gap < 0:
        st.info(f"💡 額外收入正優先填補 ${abs(current_gap)} 缺口，填滿後才會增加可用額度。")
    if remaining < 0:
        st.error("🚨 警告：本月已透支！停止支出！")

    st.markdown("---")

    with st.container():
        st.write("📝 **新增交易**")
        txn_type = st.radio("類型", ["💸 支出", "💰 收入"], horizontal=True, label_visibility="collapsed")
        
        with st.form("expense_form", clear_on_submit=True):
            c1, c2 = st.columns([1, 2])
            date_input = c1.date_input("日期", datetime.now())
            item_input = c2.text_input("項目", placeholder="輸入名稱...")
            
            c3, c4 = st.columns(2)
            amount_input = c3.number_input("金額", min_value=1, step=1)
            
            is_reimbursable = "否"
            update_asset = False
            
            if txn_type == "💸 支出":
                is_reimbursable = c4.radio("報帳?", ["否", "是"], horizontal=True)
            else:
                st.caption("✨ 收入將自動存入台幣活存，並優先抵銷總透支。")
                update_asset = True 

            submitted = st.form_submit_button("✅ 送出交易", use_container_width=True)

            if submitted and ws_log:
                if item_input and amount_input > 0:
                    date_str = date_input.strftime("%m/%d")
                    
                    if txn_type == "💸 支出":
                        actual_cost = 0 if is_reimbursable == "是" else amount_input
                        ws_log.append_row([date_str, item_input, amount_input, is_reimbursable, actual_cost])
                        st.toast(f"💸 支出已記：${amount_input}")
                    else:
                        actual_cost = -amount_input
                        ws_log.append_row([date_str, item_input, amount_input, "收入", actual_cost])
                        
                        if update_asset and ws_assets:
                            try:
                                all_assets = ws_assets.get_all_records()
                                for i, row in enumerate(all_assets):
                                    if row.get('資產項目') == '台幣活存':
                                        current_val = int(str(row.get('目前價值', 0)).replace(',', ''))
                                        new_val = current_val + amount_input
                                        ws_assets.update_cell(i + 2, 2, new_val)
                                        st.toast(f"💰 資產已更新：台幣 +${amount_input}")
                                        break
                            except:
                                st.error("資產連動失敗")
                    
                    time.sleep(1)
                    st.rerun()

    if not current_month_logs.empty:
        st.markdown("### 📜 本月明細")
        for index, row in current_month_logs.tail(5).iloc[::-1].iterrows():
            with st.container():
                cost = row['實際消耗']
                if cost > 0:
                    color, prefix = "#e74c3c", "-$"
                elif cost < 0:
                    color, prefix = "#2ecc71", "+$"
                else:
                    color, prefix = "#95a5a6", "$"
                
                st.markdown(f"""
                <div style="background-color: white; padding: 10px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;">
                    <div><span style="color:#888;font-size:0.8em;">{row['日期']}</span><br><b>{row['項目']}</b></div>
                    <div style="text-align:right;"><span style="color:{color};font-weight:bold;">{prefix}{row['金額']}</span></div>
                </div>
                """, unsafe_allow_html=True)

# ==========================================
# 🛍️ 頁面 2：購物冷靜清單 (總覽 + 刪除系統)
# ==========================================
elif page == "🛍️ 購物冷靜清單":
    st.subheader("🧊 購物冷靜清單")
    df_shop, ws_shop = get_data("購物冷靜清單")

    # --- 1. 總覽模組 (Dashboard) ---
    if not df_shop.empty:
        # 計算總金額
        total_items = len(df_shop)
        total_price = 0
        
        # 遍歷資料計算總額 (處理逗號與欄位)
        for index, row in df_shop.iterrows():
            price_raw = row.get('預估價格', row.get('預估價格 (C)', 0))
            try:
                p = int(str(price_raw).replace(',', ''))
            except:
                p = 0
            total_price += p
        
        # 顯示總覽卡片
        d1, d2 = st.columns(2)
        with d1:
            st.markdown(make_card_html("清單總項數", f"{total_items} 項", "慾望清單", "blue"), unsafe_allow_html=True)
        with d2:
            st.markdown(make_card_html("預估總金額", f"${total_price:,}", "需存錢目標", "orange"), unsafe_allow_html=True)
    else:
        st.info("目前清單是空的，太棒了！")

    st.markdown("---")

    # --- 2. 新增區 ---
    with st.expander("➕ 新增願望 (Add Item)", expanded=False):
        with st.form("shopping_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            s_name = c1.text_input("物品")
            s_price = c2.number_input("價格", min_value=0)
            if st.form_submit_button("加入"):
                if ws_shop:
                    ws_shop.append_row([datetime.now().strftime("%m/%d"), s_name, s_price, "3", "2026/07/01", "延後", ""])
                    st.success("已加入清單！")
                    time.sleep(1)
                    st.rerun()

    # --- 3. 清單與刪除系統 ---
    if not df_shop.empty:
        st.markdown("### 📦 願望清單明細")
        # 使用 enumerate 來獲取 index，以便刪除對應行
        for i, row in df_shop.iterrows():
            item_name = row.get('物品名稱', row.get('物品名稱 (B)', '未命名'))
            price_raw = row.get('預估價格', row.get('預估價格 (C)', 0))
            try:
                price_val = int(str(price_raw).replace(',', ''))
            except:
                price_val = 0
                
            decision = row.get('最終決策', row.get('最終決策 (G)', '考慮中'))
            note = row.get('備註', row.get('理由與備註 (H)', '無'))
            status_color = "red" if decision == "延後" else "green"
            
            # 卡片本體
            with st.expander(f"🛒 **{item_name}** - ${price_val:,}"):
                c_info, c_action = st.columns([3, 1])
                
                with c_info:
                    st.markdown(f"**決策：** :{status_color}[{decision}]")
                    st.info(f"💡 {note}")
                    
                with c_action:
                    st.write("") # 排版空格
                    st.write("") 
                    # 🔴 刪除按鈕
                    # key=f"del_{i}" 確保每個按鈕唯一
                    if st.button("🗑️ 刪除", key=f"del_{i}", type="primary", use_container_width=True):
                        if ws_shop:
                            # gspread 刪除列 (index + 2 因為標題佔 1 列，且 gspread 從 1 開始)
                            ws_shop.delete_rows(i + 2)
                            st.toast(f"✅ 已刪除：{item_name}")
                            time.sleep(1) # 讓使用者看到訊息
                            st.rerun() # 強制重整頁面

# ==========================================
# 📊 頁面 3：資產與收支
# ==========================================
elif page == "📊 資產與收支":
    st.subheader("💰 資產狀況")
    
    df_assets, _ = get_data("資產總覽表")
    if not df_assets.empty:
        df_assets['目前價值'] = df_assets['目前價值'].astype(str).str.replace(',', '')
        df_assets['目前價值'] = pd.to_numeric(df_assets['目前價值'], errors='coerce').fillna(0)
        
        assets_dict = dict(zip(df_assets['資產項目'], df_assets['目前價值']))
        
        twd_val = int(assets_dict.get('台幣活存', 0))
        jpy_val = int(assets_dict.get('日幣帳戶', 0))
        fixed_val = int(assets_dict.get('定存累計', 0))
        total_net_worth = int(assets_dict.get('總資產', 0))

        st.markdown(make_card_html("目前總身價 (Net Worth)", f"${total_net_worth:,}", "含所有資產", "blue"), unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""<div class="asset-card"><div class="asset-val">${twd_val:,}</div><div class="asset-lbl">🇹🇼 台幣活存</div></div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class="asset-card"><div class="asset-val">¥{jpy_val:,}</div><div class="asset-lbl">🇯🇵 日幣帳戶</div></div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class="asset-card"><div class="asset-val">${fixed_val:,}</div><div class="asset-lbl">🏦 定存累計</div></div>""", unsafe_allow_html=True)

    st.markdown("---")
    
    st.subheader("📉 每月固定收支結構")
    df_model, _ = get_data("每月收支模型")
    
    if not df_model.empty:
        for i, row in df_model.iterrows():
            item = str(row.get('項目 (A)', row.get('項目', ''))).strip()
            amt_raw = row.get('金額 (B)', row.get('金額', ''))
            
            if not item: continue
            if str(amt_raw).strip() == '' or pd.isna(amt_raw): continue
            
            if "總計" not in item and "剩餘" not in item:
                icon = "🔴" if str(amt_raw).startswith('-') else "🟢"
                st.markdown(f"**{icon} {item}**: ${amt_raw}")

        try:
            total_expense = df_model[df_model['項目 (A)'].astype(str).str.contains("支出總計")]['金額 (B)'].values[0]
            monthly_balance = df_model[df_model['項目 (A)'].astype(str).str.contains("每月淨剩餘")]['金額 (B)'].values[0]
            
            st.markdown(f"""
            <div class="summary-box">
                <div>
                    <div class="summary-title">每月固定支出總計</div>
                    <div style="font-size: 20px; font-weight: bold; color: #ff6b6b;">${total_expense}</div>
                </div>
                <div style="text-align: right;">
                    <div class="summary-title">每月固定餘額</div>
                    <div class="summary-val">${monthly_balance}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        except:
            pass

# ==========================================
# 📅 頁面 4：未來推估
# ==========================================
elif page == "📅 未來推估":
    st.subheader("🔮 未來六個月財務預測")
    
    df_future, _ = get_data("未來四個月推估")
    
    if not df_future.empty:
        target_df = df_future[~df_future['月份 (A)'].astype(str).str.contains("初始")]
        cols = st.columns(3)
        
        for i, (index, row) in enumerate(target_df.iterrows()):
            col = cols[i % 3]
            month_name = str(row['月份 (A)'])
            est_bal = row['預估實際餘額 (D)']
            target_bal = row['目標應有餘額 (E)']
            
            with col:
                st.markdown(f"""
                <div class="future-card">
                    <div style="font-weight:bold; font-size:16px; margin-bottom:5px;">{month_name}</div>
                    <div style="font-size:12px; color:#888;">目標: ${target_bal}</div>
                    <div style="font-size:20px; font-weight:bold; color:#2980b9;">${est_bal}</div>
                </div>
                """, unsafe_allow_html=True)
                st.write("") 

        try:
            last_row = df_future.iloc[-1]
            last_month = last_row['月份 (A)']
            last_val = last_row['預估實際餘額 (D)']
            st.markdown("---")
            st.markdown(make_card_html(f"🎉 {last_month} 最終預估結餘", f"${last_val}", "財務自由的起點", "purple"), unsafe_allow_html=True)
        except:
            pass

# ==========================================
# 🗓️ 頁面 5：歷史帳本回顧
# ==========================================
elif page == "🗓️ 歷史帳本回顧":
    st.subheader("🗓️ 歷史帳本查詢")
    
    df_log, _ = get_data("流動支出日記帳", head=4)
    
    if not df_log.empty:
        df_log['Month'] = pd.to_datetime(df_log['日期'], format='%m/%d', errors='coerce').dt.month
        df_log['Month'] = df_log['Month'].fillna(0).astype(int)
        
        available_months = sorted(df_log['Month'].unique())
        available_months = [m for m in available_months if m > 0]
        
        if available_months:
            selected_month = st.selectbox("請選擇月份", available_months, index=len(available_months)-1)
            
            history_df = df_log[df_log['Month'] == selected_month].copy()
            history_df['實際消耗'] = pd.to_numeric(history_df['實際消耗'], errors='coerce').fillna(0)
            month_total = int(history_df['實際消耗'].sum())
            
            st.markdown(make_card_html(f"{selected_month}月 淨支出", f"${month_total}", "含收入抵銷後", "gray"), unsafe_allow_html=True)
            
            st.markdown("### 📜 明細回顧")
            for index, row in history_df.iloc[::-1].iterrows():
                with st.container():
                    cost = row['實際消耗']
                    if cost > 0:
                        color, prefix = "#e74c3c", "-$"
                    elif cost < 0:
                        color, prefix = "#2ecc71", "+$"
                    else:
                        color, prefix = "#95a5a6", "$"
                    
                    st.markdown(f"""
                    <div style="background-color: white; padding: 10px; border-radius: 8px; margin-bottom: 8px; border: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;">
                        <div><span style="color:#888;font-size:0.8em;">{row['日期']}</span><br><b>{row['項目']}</b></div>
                        <div style="text-align:right;"><span style="color:{color};font-weight:bold;">{prefix}{row['金額']}</span></div>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("目前還沒有歷史資料。")
    else:
        st.info("日記帳是空的。")
