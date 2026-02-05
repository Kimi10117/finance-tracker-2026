import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 設定頁面資訊 ---
st.set_page_config(page_title="宇毛的財務中控台", page_icon="💰", layout="wide")

# --- CSS 極致美化 (v17.0 Logic Separation) ---
st.markdown("""
<style>
    /* 1. 全局背景與變數適配 */
    .stApp {
        background-color: var(--background-color);
        color: var(--text-color);
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    .block-container {
        padding-top: 3.5rem;
        padding-bottom: 5rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    /* === 現代化卡片設計 === */
    .custom-card {
        background-color: var(--secondary-background-color);
        padding: 15px;
        border-radius: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 12px;
        border: 1px solid rgba(128, 128, 128, 0.1);
        transition: transform 0.2s ease;
    }
    
    .card-title {
        font-size: 13px;
        color: var(--text-color);
        opacity: 0.7;
        font-weight: 600;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin-bottom: 6px;
        white-space: normal;
        line-height: 1.2;
    }
    
    .card-value {
        font-size: 26px;
        font-weight: 800;
        color: var(--text-color);
        letter-spacing: -0.5px;
        line-height: 1.2;
        white-space: nowrap; 
    }
    
    .card-note {
        font-size: 12px;
        font-weight: 600;
        margin-top: 4px;
        display: flex;
        align-items: center;
        gap: 4px;
        white-space: normal; 
    }

    /* === 進度條樣式 === */
    .progress-bg {
        width: 100%;
        height: 8px;
        background-color: rgba(128, 128, 128, 0.2);
        border-radius: 4px;
        margin-top: 8px;
        overflow: hidden;
    }
    .progress-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.5s ease;
    }

    /* === 資產卡片 === */
    .asset-card {
        background-color: var(--secondary-background-color);
        padding: 16px;
        border-radius: 16px;
        text-align: center;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border: 1px solid rgba(128, 128, 128, 0.1);
    }
    .asset-val { font-size: 20px; font-weight: 700; color: var(--text-color); }
    .asset-lbl { font-size: 12px; color: var(--text-color); opacity: 0.7; font-weight: 600; margin-top: 4px; }

    /* === 交易明細優化 === */
    .list-item {
        background-color: var(--secondary-background-color);
        padding: 14px;
        border-radius: 12px;
        margin-bottom: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        border: 1px solid rgba(128, 128, 128, 0.1);
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    /* 膠囊標籤 */
    .badge {
        display: inline-block;
        padding: 3px 8px;
        font-size: 10px;
        font-weight: 700;
        border-radius: 12px;
        margin-top: 4px;
        white-space: nowrap; 
    }
    .badge-gray { background: rgba(136, 152, 170, 0.2); color: var(--text-color); opacity: 0.8; }
    .badge-orange { background: rgba(251, 99, 64, 0.15); color: #fb6340; }
    .badge-green { background: rgba(45, 206, 137, 0.15); color: #2dce89; }
    .badge-purple { background: rgba(142, 68, 173, 0.15); color: #8e44ad; }
    .badge-blue { background: rgba(52, 152, 219, 0.15); color: #3498db; }

    /* === 底部總結區 === */
    .summary-box {
        background: linear-gradient(135deg, #2c3e50 0%, #4ca1af 100%); 
        color: white;
        padding: 24px;
        border-radius: 20px;
        margin-top: 24px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
    }
    
    /* === 未來推估卡片 === */
    .future-card {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.1);
        padding: 10px;
        border-radius: 8px;
        text-align: center;
        height: 100%;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* === Radio Button 優化 === */
    div[role="radiogroup"] {
        background-color: var(--secondary-background-color);
        padding: 5px;
        border-radius: 12px;
        border: 1px solid rgba(128, 128, 128, 0.1);
        display: flex;
        justify-content: space-between;
    }
    div[role="radiogroup"] label {
        flex: 1;
        text-align: center;
        background-color: transparent;
        border: none;
        padding: 8px;
        border-radius: 8px;
        transition: all 0.2s;
        color: var(--text-color);
    }
    div[role="radiogroup"] label[data-checked="true"] {
        background-color: rgba(128, 128, 128, 0.1);
        font-weight: bold;
        color: #5e72e4;
    }
    .stRadio > label {
        font-weight: bold;
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
st.sidebar.caption("宇毛的記帳本 v17.0 (Logic Fix)")

# --- 讀取資料函式 ---
def get_data(worksheet_name, head=1):
    try:
        ws = sh.worksheet(worksheet_name)
        data = ws.get_all_records(head=head)
        return pd.DataFrame(data), ws
    except:
        return pd.DataFrame(), None

# --- UI 元件生成器 ---
def make_modern_card(title, value, note, color_theme, progress=None):
    themes = {
        "blue":   "#5e72e4", "red": "#f5365c", "green": "#2dce89",
        "orange": "#fb6340", "gray": "var(--text-color)", "dark": "var(--text-color)", "purple": "#8e44ad"
    }
    accent_color = themes.get(color_theme, "var(--text-color)")
    note_style = f"color: {accent_color};"
    if color_theme in ["gray", "dark"]: note_style = "color: var(--text-color); opacity: 0.7;"

    progress_html = ""
    if progress is not None:
        try:
            pct = min(max(float(progress), 0.0), 1.0) * 100
            progress_html = f'<div class="progress-bg"><div class="progress-fill" style="width: {pct}%; background-color: {accent_color};"></div></div>'
        except: progress_html = ""
        
    return f"""
    <div class="custom-card">
        <div class="card-title">{title}</div>
        <div class="card-value">{value}</div>
        <div class="card-note" style="{note_style}">{note}</div>
        {progress_html}
    </div>
    """

def make_badge(text, style="gray"):
    return f'<span class="badge badge-{style}">{text}</span>'

# ==========================================
# 🏠 頁面 1：隨手記帳
# ==========================================
if page == "💸 隨手記帳 (本月)":
    now_dt = datetime.now()
    current_month = now_dt.month
    current_day = now_dt.day
    current_year = now_dt.year
    
    st.subheader(f"👋 {current_month} 月財務面板")
    
    base_budget = 97 if current_month == 2 else 2207
    
    df_log, ws_log = get_data("流動支出日記帳", head=4)
    df_assets, ws_assets = get_data("資產總覽表")
    df_status, ws_status = get_data("現況資金檢核")

    if not df_log.empty and '已入帳' not in df_log.columns: df_log['已入帳'] = '已入帳'

    # 1. 取得靜態缺口 (來自試算表 B9)
    try:
        if ws_status:
            gap_val = ws_status.cell(9, 2).value 
            base_gap_static = int(str(gap_val).replace(',', ''))
        else:
            base_gap_static = -9999
    except:
        base_gap_static = -9999

    # 2. 計算本月數據 (核心邏輯修正：排除固定支出)
    total_variable_expenses = 0 # 變動支出 (要扣額度的)
    pending_debt = 0 # 代墊 (未入帳)
    current_month_logs = pd.DataFrame()
    
    if not df_log.empty:
        def robust_month_parser(x):
            try: return pd.to_datetime(str(x), format='%m/%d').month
            except:
                try: return pd.to_datetime(str(x)).month
                except: 
                    if str(x).strip() == "": return 0
                    return current_month 

        df_log['Month'] = df_log['日期'].apply(robust_month_parser)
        current_month_logs = df_log[df_log['Month'] == current_month].copy()
        current_month_logs['實際消耗'] = pd.to_numeric(current_month_logs['實際消耗'], errors='coerce').fillna(0)
        current_month_logs['金額'] = pd.to_numeric(current_month_logs['金額'], errors='coerce').fillna(0)
        current_month_logs['項目'] = current_month_logs['項目'].astype(str)
        
        # 關鍵過濾：計算「已實現」且「非固定」的支出，才去扣預算
        # 條件：實際消耗 > 0  AND  類型 != '固定'
        variable_mask = (current_month_logs['實際消耗'] > 0) & (current_month_logs['是否報帳'] != '固定')
        total_variable_expenses = int(current_month_logs[variable_mask]['實際消耗'].sum())
        
        # 計算未入帳的代墊 (這算負債)
        pending_filter = (current_month_logs['是否報帳'] == '是') & (current_month_logs['已入帳'] == '未入帳')
        pending_debt = int(current_month_logs[pending_filter]['金額'].sum())

    # 3. 核心數值計算
    # 缺口：直接讀取試算表 B9 (已包含所有已發生的收支)
    current_gap = base_gap_static
    
    # 額度：本金 + 缺口溢出(如果有) - 變動支出
    surplus_from_gap = max(0, current_gap)
    remaining = (base_budget + surplus_from_gap) - total_variable_expenses

    # --- 💡 全同步更新函式 ---
    def sync_update(amount_change, is_income_flag=False):
        if not ws_assets or not ws_status: return
        try:
            # 1. 更新資產 (台幣)
            all_assets = ws_assets.get_all_records()
            new_twd_balance = 0
            for i, r in enumerate(all_assets):
                if r.get('資產項目') == '台幣活存':
                    curr = int(str(r.get('目前價值', 0)).replace(',', ''))
                    new_twd_balance = curr + amount_change
                    ws_assets.update_cell(i+2, 2, new_twd_balance)
                    break
            
            # 2. 更新 B6 餘額
            ws_status.update_cell(6, 2, new_twd_balance)
            
            # 3. 更新 B9 缺口 (Gap 也跟著變動)
            curr_gap_val = int(str(ws_status.cell(9, 2).value).replace(',', ''))
            new_gap_val = curr_gap_val + amount_change
            ws_status.update_cell(9, 2, new_gap_val)
            
        except Exception as e: st.error(f"Sync Error: {e}")

    # --- 🔔 智慧例行事項 ---
    with st.expander("🔔 智慧例行事項檢查 (Smart Check)", expanded=True):
        r_col1, r_col2 = st.columns(2)
        
        def check_logged(keyword):
            if current_month_logs.empty: return False
            return current_month_logs['項目'].str.contains(keyword, case=False).any()

        def execute_auto_entry(name, amount, type_code="固定", is_transfer=False):
            if not ws_log: return
            date_str = now_dt.strftime("%m/%d")
            
            if is_transfer: # 定存轉帳 (資產內部轉移，不變動總資產，也不變動缺口)
                try:
                    all_assets = ws_assets.get_all_records()
                    twd_r, fix_r = -1, -1
                    twd_v, fix_v = 0, 0
                    for i, r in enumerate(all_assets):
                        if r.get('資產項目') == '台幣活存': twd_r=i+2; twd_v=int(str(r.get('目前價值',0)).replace(',',''))
                        if r.get('資產項目') == '定存累計': fix_r=i+2; fix_v=int(str(r.get('目前價值',0)).replace(',',''))
                    if twd_r!=-1 and fix_r!=-1:
                        ws_assets.update_cell(twd_r, 2, twd_v - amount) # 台幣少
                        ws_assets.update_cell(fix_r, 2, fix_v + amount) # 定存多
                        ws_status.update_cell(6, 2, twd_v - amount) # B6 同步台幣
                        
                        ws_log.append_row([date_str, name, amount, "固定", 0, "固定扣款"]) 
                        st.success(f"✅ {name} 執行成功！")
                        time.sleep(1)
                        st.rerun()
                except: st.error("轉帳失敗")
                return

            # 固定收支 (收入為正，支出為負)
            is_income = (type_code == "固定收入")
            change = amount if is_income else -amount
            
            # 寫入 Log: 類型=固定，實際消耗=0 (不扣預算)，狀態=固定扣款
            # 注意：這裡實際消耗設為 0，因為 $97 預算已經把這些扣掉了，不能再扣一次！
            ws_log.append_row([date_str, name, amount, "固定", 0, "固定扣款"])
            
            # 同步資產與缺口
            sync_update(change)
            
            st.success(f"✅ {name} 已記錄！(不影響預算)")
            time.sleep(1)
            st.rerun()

        with r_col1:
            st.markdown("**💰 收入與資產**")
            if current_day >= 5:
                if not check_logged("固定收入"):
                    if st.button("📥 入帳薪水 ($3900)", key="btn_salary"): 
                        execute_auto_entry("固定收入 (薪水)", 3900, type_code="固定收入")
                else: st.caption("✅ 薪水已入帳")
            else: st.caption(f"⏳ 薪水: 再等 {5-current_day} 天")

            if current_day >= 10:
                if not check_logged("定存扣款"):
                    if st.button("🏦 轉存定存 ($1000)", key="btn_deposit"): 
                        execute_auto_entry("定存扣款", 1000, is_transfer=True)
                else: st.caption("✅ 定存已轉")
            else: st.caption(f"⏳ 定存: 再等 {10-current_day} 天")

        with r_col2:
            st.markdown("**💸 固定支出**")
            # 定義固定支出列表
            fixed_items = [
                {"day": 10, "name": "電信費", "amt": 499, "key": "btn_tel"},
                {"day": 22, "name": "YT Premium", "amt": 119, "key": "btn_ytp"}
            ]
            
            for item in fixed_items:
                if current_day >= item["day"]:
                    if not check_logged(item["name"]):
                        if st.button(f"💸 繳{item['name']} (${item['amt']})", key=item["key"]):
                            execute_auto_entry(item["name"], item["amt"], type_code="固定支出")
                    else: st.caption(f"✅ {item['name']}已繳")
            
            # 特殊日期: 小雪
            if current_year < 2026 or (current_year == 2026 and current_month < 7):
                if current_day >= 6:
                    if not check_logged("小雪"):
                        if st.button("❄️ 繳小雪會員 ($75)", key="btn_koyuki"):
                            execute_auto_entry("YT會員(小雪)", 75, type_code="固定支出")
                    else: st.caption("✅ 小雪會員已繳")
            
            # 還債 (只要缺口是負的就顯示)
            if current_gap < 0:
                if not check_logged("自我分期"):
                    if st.button("💳 自我分期還債 ($2110)", type="primary", key="btn_debt"):
                        execute_auto_entry("自我分期(還債)", 2110, type_code="固定支出")
                else: st.caption("✅ 本月已還債")

    # --- 儀表板區域 ---
    col1, col2, col3, col4 = st.columns(4)
    
    gap_progress = 0.0
    if current_gap < 0:
        gap_status = "📉 填坑中..."
        gap_color = "orange"
        gap_note = "收入優先抵債"
        try: gap_progress = 1.0 - (abs(current_gap) / max(abs(base_gap_static)+1000, 2000))
        except: gap_progress = 0.0
    else:
        gap_status = "🎉 已轉正"
        gap_color = "green"
        gap_note = f"溢出 +${surplus_from_gap}"
        gap_progress = 1.0

    rem_color = "green"
    rem_note = "✅ 資金安全"
    if remaining < 0:
        rem_color = "red"
        rem_note = "🛑 已透支"
    elif remaining < 50:
        rem_color = "orange"
        rem_note = "⚠️ 資金見底"

    with col1: st.markdown(make_modern_card(f"{current_month}月本金", f"${base_budget}", "固定額度", "blue"), unsafe_allow_html=True)
    with col2: st.markdown(make_modern_card("本月花費", f"${total_variable_expenses}", "僅計流動支出", "gray"), unsafe_allow_html=True)
    with col3: st.markdown(make_modern_card("目前可用", f"${remaining}", rem_note, rem_color), unsafe_allow_html=True)
    with col4: st.markdown(make_modern_card("總透支缺口", f"${current_gap}", gap_note, gap_color, progress=gap_progress), unsafe_allow_html=True)

    if pending_debt > 0:
        st.caption(f"ℹ️ 包含 ${pending_debt} 未入帳的代墊款。")
    if current_gap < 0:
        st.info(f"💡 缺口雖為負，但只要「目前可用」是綠色，代表本月消費還在控制內。")
    if remaining < 0:
        st.error("🚨 警告：本月已透支！請停止支出！")

    st.markdown("---")

    # --- 交易輸入區 ---
    st.subheader("📝 新增交易")
    txn_type = st.radio("類型", ["💸 支出", "💰 收入"], horizontal=True)
    
    with st.form("expense_form", clear_on_submit=True):
        c1, c2 = st.columns([1, 2])
        date_input = c1.date_input("日期", datetime.now())
        item_input = c2.text_input("項目", placeholder="例如: 午餐")
        
        c3, c4 = st.columns(2)
        amount_input = c3.number_input("金額", min_value=1, step=1)
        
        is_reimbursable = "否"
        reimburse_target = ""
        
        if "支出" in txn_type:
            is_reimbursable = c4.radio("是否報帳/代墊?", ["否", "是"], horizontal=True)
            if "是" in is_reimbursable:
                st.info("💡 代墊款會先扣除你的資產與額度，直到朋友還錢。")
                reimburse_target = st.text_input("幫誰代墊？", placeholder="例如: Andy")
                is_reimbursable = "是"
            else:
                is_reimbursable = "否"
        else:
            st.caption("ℹ️ 收入預設為 **「未入帳」**")
            
        submitted = st.form_submit_button("確認記帳", use_container_width=True, type="primary")

        if submitted and ws_log:
            if item_input and amount_input > 0:
                date_str = date_input.strftime("%m/%d")
                
                final_item_name = item_input
                if reimburse_target:
                    final_item_name = f"{item_input} ({reimburse_target})"
                
                if "支出" in txn_type:
                    if is_reimbursable == "是":
                        actual_cost = amount_input; status_val = "未入帳"
                    else:
                        actual_cost = amount_input; status_val = "已入帳"
                    
                    ws_log.append_row([date_str, final_item_name, amount_input, is_reimbursable, actual_cost, status_val])
                    
                    # 支出: 扣資產、扣 Gap (變更負)
                    change = -amount_input
                    sync_update(change)

                    st.toast(f"💸 支出已記：${amount_input}")
                    
                else:
                    actual_cost = 0; status_val = "未入帳"
                    ws_log.append_row([date_str, final_item_name, amount_input, "收入", actual_cost, status_val])
                    st.toast(f"💰 收入已記 (未入帳)：${amount_input}")
                
                time.sleep(1)
                st.rerun()

    # --- 明細列表 ---
    if not current_month_logs.empty:
        st.markdown("### 📜 本月明細")
        for i, (index, row) in enumerate(current_month_logs.iloc[::-1].iterrows()):
            real_row_idx = index + 5 
            txn_class = "一般"
            # 判斷類型
            if row['是否報帳'] == "是": txn_class = "報帳/代墊"
            elif row['是否報帳'] == "收入": txn_class = "收入"
            elif row['是否報帳'] == "固定": txn_class = "固定收支"
            
            status = str(row.get('已入帳', '已入帳')).strip() or "已入帳"
            
            # 視覺邏輯
            badge_color = "gray"
            text_color = "var(--text-color)"
            prefix = "$"
            
            if txn_class == "收入":
                badge_color = "green" if status == "已入帳" else "gray"
                text_color = "#2dce89" if status == "已入帳" else "var(--text-color)"
                prefix = "+$"
            elif txn_class == "報帳/代墊":
                badge_color = "purple" if status == "未入帳" else "gray"
                text_color = "#8e44ad" if status == "未入帳" else "var(--text-color)"
            elif txn_class == "固定收支":
                badge_color = "blue"
                text_color = "#3498db"
                prefix = "$" # 固定收支可能是正或負，這邊簡化顯示
            else: # 一般支出
                text_color = "#f5365c"
                prefix = "-$"

            badge_html = make_badge(status, badge_color)
            amt_html = f'<span style="color: {text_color}; font-weight: 800; font-size: 1.1em; opacity: {0.5 if status=="未入帳" and txn_class=="收入" else 1.0};">{prefix}{row["金額"]}</span>'

            with st.container():
                col_info, col_amt, col_action = st.columns([3, 1.5, 1])
                with col_info:
                    st.markdown(f"""
                    <div style="line-height:1.4;">
                        <span style="font-size:0.85em; opacity: 0.7;">{row['日期']}</span><br>
                        <span style="font-weight:600;">{row['項目']}</span>
                        <br>{badge_html} <span style="font-size:0.8em; opacity: 0.6;">{txn_class}</span>
                    </div>
                    """, unsafe_allow_html=True)
                with col_amt:
                    st.markdown(f"<div style='margin-top:10px;'>{amt_html}</div>", unsafe_allow_html=True)
                with col_action:
                    # 只有 一般收支/代墊 可以切換狀態 (固定收支不能切)
                    if txn_class in ["報帳/代墊", "收入"]:
                        is_cleared = (status == "已入帳")
                        toggle_label = "已結清?" if "報帳" in txn_class else "已入帳?"
                        
                        if st.toggle(toggle_label, value=is_cleared, key=f"tg_{index}") != is_cleared:
                            new_state = not is_cleared
                            new_status_str = "已入帳" if new_state else "未入帳"
                            new_actual_cost = 0
                            asset_change = 0
                            
                            if "報帳" in txn_class:
                                new_actual_cost = row['金額'] if not new_state else 0
                                # 代墊還款: 資產+
                                asset_change = row['金額'] if new_state else -row['金額']
                            elif txn_class == "收入":
                                new_actual_cost = -row['金額'] if new_state else 0
                                asset_change = row['金額'] if new_state else -row['金額']
                                
                            if asset_change != 0:
                                sync_update(asset_change)

                            if ws_log:
                                ws_log.update_cell(real_row_idx, 5, new_actual_cost)
                                ws_log.update_cell(real_row_idx, 6, new_status_str)
                                st.success(f"已更新")
                                time.sleep(0.5)
                                st.rerun()
                st.markdown("---")

# ==========================================
# 🛍️ 頁面 2：購物冷靜清單 (Modern UI)
# ==========================================
elif page == "🛍️ 購物冷靜清單":
    st.subheader("🧊 購物冷靜清單")
    df_shop, ws_shop = get_data("購物冷靜清單")

    if not df_shop.empty:
        total_items = len(df_shop)
        total_price = 0
        for index, row in df_shop.iterrows():
            try: p = int(str(row.get('預估價格', 0)).replace(',', ''))
            except: p = 0
            total_price += p
        
        d1, d2 = st.columns(2)
        with d1: st.markdown(make_modern_card("清單總項數", f"{total_items} 項", "慾望清單", "blue"), unsafe_allow_html=True)
        with d2: st.markdown(make_modern_card("預估總金額", f"${total_price:,}", "需存錢目標", "orange"), unsafe_allow_html=True)
    else:
        st.info("清單是空的！")

    st.markdown("---")

    with st.expander("➕ 新增願望", expanded=False):
        with st.form("shopping_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            s_name = c1.text_input("物品")
            s_price = c2.number_input("價格", min_value=0)
            if st.form_submit_button("加入", type="primary"):
                if ws_shop:
                    ws_shop.append_row([datetime.now().strftime("%m/%d"), s_name, s_price, "3", "2026/07/01", "延後", ""])
                    st.success("已加入！")
                    time.sleep(1)
                    st.rerun()

    if not df_shop.empty:
        st.markdown("### 📦 願望清單明細")
        for i, row in df_shop.iterrows():
            item = row.get('物品名稱', row.get('物品名稱 (B)', '未命名'))
            try: price = int(str(row.get('預估價格', 0)).replace(',', ''))
            except: price = 0
            decision = row.get('最終決策', '考慮中')
            note = row.get('備註', '無')
            status_color = "red" if decision == "延後" else "green"
            
            with st.expander(f"🛒 **{item}** - ${price:,}"):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**決策：** :{status_color}[{decision}]")
                    st.caption(f"備註: {note}")
                with c2:
                    st.write("")
                    if st.button("🗑️ 刪除", key=f"del_{i}", type="primary", use_container_width=True):
                        if ws_shop:
                            ws_shop.delete_rows(i + 2)
                            st.toast("已刪除")
                            time.sleep(1)
                            st.rerun()

# ==========================================
# 📊 頁面 3：資產與收支 (Visual Fix)
# ==========================================
elif page == "📊 資產與收支":
    st.subheader("💰 資產狀況")
    df_assets, _ = get_data("資產總覽表")
    if not df_assets.empty:
        df_assets['目前價值'] = df_assets['目前價值'].astype(str).str.replace(',', '')
        df_assets['目前價值'] = pd.to_numeric(df_assets['目前價值'], errors='coerce').fillna(0)
        assets_dict = dict(zip(df_assets['資產項目'], df_assets['目前價值']))
        
        twd = int(assets_dict.get('台幣活存', 0))
        jpy = int(assets_dict.get('日幣帳戶', 0))
        fix = int(assets_dict.get('定存累計', 0))
        total = int(assets_dict.get('總資產', 0))

        st.markdown(make_modern_card("目前總身價", f"${total:,}", "含所有資產", "blue"), unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f"""<div class="asset-card"><div class="asset-val">${twd:,}</div><div class="asset-lbl">🇹🇼 台幣活存</div></div>""", unsafe_allow_html=True)
        with c2: st.markdown(f"""<div class="asset-card"><div class="asset-val">¥{jpy:,}</div><div class="asset-lbl">🇯🇵 日幣帳戶</div></div>""", unsafe_allow_html=True)
        with c3: st.markdown(f"""<div class="asset-card"><div class="asset-val">${fix:,}</div><div class="asset-lbl">🏦 定存累計</div></div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📉 每月固定收支結構")
    df_model, _ = get_data("每月收支模型")
    if not df_model.empty:
        for i, row in df_model.iterrows():
            item = str(row.get('項目 (A)', row.get('項目', ''))).strip()
            amt = row.get('金額 (B)', row.get('金額', ''))
            if not item or str(amt).strip() == '' or pd.isna(amt): continue
            if "總計" not in item and "剩餘" not in item:
                icon = "🔴" if str(amt).startswith('-') else "🟢"
                st.markdown(f"**{icon} {item}**: ${amt}")
        try:
            exp = df_model[df_model['項目 (A)'].astype(str).str.contains("支出總計")]['金額 (B)'].values[0]
            bal = df_model[df_model['項目 (A)'].astype(str).str.contains("每月淨剩餘")]['金額 (B)'].values[0]
            st.markdown(f"""
            <div class="summary-box">
                <div><div class="summary-title">固定支出總計</div><div style="font-size:20px;font-weight:bold;color:#ff6b6b;">${exp}</div></div>
                <div style="text-align:right;"><div class="summary-title">固定餘額</div><div style="font-size:20px;font-weight:bold;color:#2dce89;">${bal}</div></div>
            </div>""", unsafe_allow_html=True)
        except: pass

# ==========================================
# 📅 頁面 4：未來推估 (Mobile Order Fix)
# ==========================================
elif page == "📅 未來推估":
    st.subheader("🔮 未來六個月財務預測")
    df_future, _ = get_data("未來四個月推估")
    if not df_future.empty:
        target_df = df_future[~df_future['月份 (A)'].astype(str).str.contains("初始")]
        rows_data = [target_df.iloc[i:i+3] for i in range(0, len(target_df), 3)]
        
        for row_batch in rows_data:
            cols = st.columns(3) 
            for i, (index, row) in enumerate(row_batch.iterrows()):
                if i < 3:
                    month = str(row['月份 (A)'])
                    est = row['預估實際餘額 (D)']
                    tgt = row['目標應有餘額 (E)']
                    with cols[i]:
                        st.markdown(f"""<div class="asset-card" style="text-align:center;"><div style="font-weight:bold;margin-bottom:5px;color:var(--text-color);">{month}</div><div style="font-size:12px;opacity:0.7;">目標: ${tgt}</div><div style="font-size:20px;font-weight:bold;color:#5e72e4;">${est}</div></div>""", unsafe_allow_html=True)
        try:
            last = df_future.iloc[-1]
            st.markdown("---")
            st.markdown(make_modern_card(f"🎉 {last['月份 (A)']} 最終預估", f"${last['預估實際餘額 (D)']}", "財務自由起點", "purple"), unsafe_allow_html=True)
        except: pass

elif page == "🗓️ 歷史帳本回顧":
    st.subheader("🗓️ 歷史帳本查詢")
    df_log, _ = get_data("流動支出日記帳", head=4)
    if not df_log.empty:
        if '已入帳' not in df_log.columns: df_log['已入帳'] = '已入帳'
        df_log['Month'] = pd.to_datetime(df_log['日期'], format='%m/%d', errors='coerce').dt.month
        df_log['Month'] = df_log['Month'].fillna(0).astype(int)
        months = sorted([m for m in df_log['Month'].unique() if m > 0])
        
        if months:
            sel = st.selectbox("選擇月份", months, index=len(months)-1)
            hist = df_log[df_log['Month'] == sel].copy()
            hist['實際消耗'] = pd.to_numeric(hist['實際消耗'], errors='coerce').fillna(0)
            total = int(hist['實際消耗'].sum())
            
            st.markdown(make_modern_card(f"{sel}月 淨支出", f"${total}", "含收入抵銷後", "gray"), unsafe_allow_html=True)
            st.markdown("### 📜 明細回顧")
            for i, row in hist.iloc[::-1].iterrows():
                cost = row['實際消耗']
                color = "#f5365c" if cost > 0 else ("#2dce89" if cost < 0 else "#adb5bd")
                st.markdown(f"""
                <div class="list-item">
                    <div><span style="color:var(--text-color);opacity:0.7;font-size:0.85em;">{row['日期']}</span><br><b style="color:var(--text-color);">{row['項目']}</b></div>
                    <div style="text-align:right;"><span style="color:{color};font-weight:bold;">${row['金額']}</span></div>
                </div>""", unsafe_allow_html=True)
        else: st.info("無資料")
    else: st.info("無資料")
