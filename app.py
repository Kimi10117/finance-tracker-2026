import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import time

# --- 設定頁面資訊 ---
st.set_page_config(page_title="宇毛的財務中控台", page_icon="💰", layout="wide")

# --- CSS 極致美化 (v18.2 Real-Time Gap) ---
st.markdown("""
<style>
    .stApp { background-color: var(--background-color); color: var(--text-color); }
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    .block-container { padding-top: 2rem; padding-bottom: 5rem; padding-left: 1rem; padding-right: 1rem; }
    
    .custom-card {
        background-color: var(--secondary-background-color);
        padding: 15px;
        border-radius: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 12px;
        border: 1px solid rgba(128, 128, 128, 0.1);
        transition: transform 0.2s ease;
    }
    .card-title { font-size: 13px; opacity: 0.7; font-weight: 600; text-transform: uppercase; margin-bottom: 6px; }
    .card-value { font-size: 26px; font-weight: 800; white-space: nowrap; }
    .card-note { font-size: 12px; font-weight: 600; margin-top: 4px; }
    
    .progress-bg { width: 100%; height: 8px; background-color: rgba(128, 128, 128, 0.2); border-radius: 4px; margin-top: 8px; overflow: hidden; }
    .progress-fill { height: 100%; border-radius: 4px; transition: width 0.5s ease; }
    
    .asset-card { background-color: var(--secondary-background-color); padding: 16px; border-radius: 16px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border: 1px solid rgba(128, 128, 128, 0.1); }
    .asset-val { font-size: 20px; font-weight: 700; }
    .asset-lbl { font-size: 12px; opacity: 0.7; font-weight: 600; margin-top: 4px; }
    
    .list-item { background-color: var(--secondary-background-color); padding: 14px; border-radius: 12px; margin-bottom: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid rgba(128, 128, 128, 0.1); display: flex; justify-content: space-between; align-items: center; }
    
    .badge { display: inline-block; padding: 3px 8px; font-size: 10px; font-weight: 700; border-radius: 12px; margin-top: 4px; white-space: nowrap; }
    .badge-gray { background: rgba(136, 152, 170, 0.2); opacity: 0.8; }
    .badge-orange { background: rgba(251, 99, 64, 0.15); color: #fb6340; }
    .badge-green { background: rgba(45, 206, 137, 0.15); color: #2dce89; }
    .badge-purple { background: rgba(142, 68, 173, 0.15); color: #8e44ad; }
    .badge-blue { background: rgba(52, 152, 219, 0.15); color: #3498db; }
    
    .summary-box { background: linear-gradient(135deg, #2c3e50 0%, #4ca1af 100%); color: white; padding: 24px; border-radius: 20px; margin-top: 24px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 10px 20px rgba(0,0,0,0.2); }
    .future-card { background-color: var(--secondary-background-color); border: 1px solid rgba(128, 128, 128, 0.1); padding: 10px; border-radius: 8px; text-align: center; height: 100%; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    
    div[role="radiogroup"] { background-color: var(--secondary-background-color); padding: 5px; border-radius: 12px; border: 1px solid rgba(128, 128, 128, 0.1); display: flex; justify-content: space-between; }
    div[role="radiogroup"] label { flex: 1; text-align: center; background-color: transparent; border: none; padding: 8px; border-radius: 8px; transition: all 0.2s; }
    div[role="radiogroup"] label[data-checked="true"] { background-color: rgba(128, 128, 128, 0.1); font-weight: bold; color: #5e72e4; }
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

try: sh = connect_to_gsheet()
except: st.stop()

# --- 讀取資料函式 ---
def get_data(worksheet_name, head=1):
    try:
        ws = sh.worksheet(worksheet_name)
        data = ws.get_all_records(head=head)
        return pd.DataFrame(data), ws
    except: return pd.DataFrame(), None

# --- UI 元件生成器 ---
def make_modern_card(title, value, note, color_theme, progress=None):
    themes = {"blue": "#5e72e4", "red": "#f5365c", "green": "#2dce89", "orange": "#fb6340", "gray": "var(--text-color)", "purple": "#8e44ad"}
    accent_color = themes.get(color_theme, "var(--text-color)")
    note_style = f"color: {accent_color};" if color_theme not in ["gray", "dark"] else "opacity: 0.7;"
    progress_html = f'<div class="progress-bg"><div class="progress-fill" style="width: {min(max(float(progress or 0),0),1)*100}%; background-color: {accent_color};"></div></div>' if progress is not None else ""
    return f"""<div class="custom-card"><div class="card-title">{title}</div><div class="card-value">{value}</div><div class="card-note" style="{note_style}">{note}</div>{progress_html}</div>"""

def make_badge(text, style="gray"): return f'<span class="badge badge-{style}">{text}</span>'

# ==========================================
# 🚀 準備資料 & 核心運算
# ==========================================
now_dt = datetime.now()
current_month = now_dt.month
current_day = now_dt.day
current_year = now_dt.year

df_log, ws_log = get_data("流動支出日記帳", head=4)
df_assets, ws_assets = get_data("資產總覽表")
df_status, ws_status = get_data("現況資金檢核")
df_future, _ = get_data("未來四個月推估")

if not df_log.empty and '已入帳' not in df_log.columns: df_log['已入帳'] = '已入帳'

# 1. 取得「當前台幣活存」 (Real Asset)
current_twd_balance = 0
try:
    # 假設台幣活存是第一筆資料 (B2)，如果位置變動可改用 filter
    if not df_assets.empty:
        # 尋找 '台幣活存'
        row = df_assets[df_assets['資產項目'] == '台幣活存']
        if not row.empty:
            current_twd_balance = int(str(row.iloc[0]['目前價值']).replace(',', ''))
except: pass

# 2. 取得「當月目標」 (Monthly Target)
current_month_target = 0
try:
    if not df_future.empty:
        # 尋找月份 (例如 "2月")
        target_row = df_future[df_future['月份 (A)'].astype(str).str.contains(f"{current_month}月")]
        if not target_row.empty:
            current_month_target = int(str(target_row.iloc[0]['目標應有餘額 (E)']).replace(',', ''))
except: pass

# 3. 計算並更新「總透支缺口」 (Gap = Asset - Target)
# 這是最關鍵的一步：缺口不再依賴 B9 的舊值，而是即時算出來，並強制寫回 B9
if current_month_target != 0: # 確保有抓到目標
    current_gap = current_twd_balance - current_month_target
    # 寫回 B9 以保持同步
    if ws_status:
        try: ws_status.update_cell(9, 2, current_gap)
        except: pass
else:
    # 如果抓不到目標，暫時讀取 B9 當備案
    try: current_gap = int(str(df_status.iloc[-1]['數值 (B)']).replace(',', ''))
    except: current_gap = -9999

# 4. 計算本月流動支出
total_variable_expenses = 0
pending_debt = 0
current_month_logs = pd.DataFrame()

if not df_log.empty:
    def robust_month_parser(x):
        try: return pd.to_datetime(str(x), format='%m/%d').month
        except: return current_month 
    
    df_log['Month'] = df_log['日期'].apply(robust_month_parser)
    current_month_logs = df_log[df_log['Month'] == current_month].copy()
    current_month_logs['實際消耗'] = pd.to_numeric(current_month_logs['實際消耗'], errors='coerce').fillna(0)
    current_month_logs['金額'] = pd.to_numeric(current_month_logs['金額'], errors='coerce').fillna(0)
    
    # 變動支出 (扣額度)
    v_mask = (current_month_logs['實際消耗'] > 0) & (current_month_logs['是否報帳'] != '固定')
    total_variable_expenses = int(current_month_logs[v_mask]['實際消耗'].sum())
    
    # 未入帳代墊
    p_mask = (current_month_logs['是否報帳'] == '是') & (current_month_logs['已入帳'] == '未入帳')
    pending_debt = int(current_month_logs[p_mask]['金額'].sum())

# 5. 計算可用額度
base_budget = 97 if current_month == 2 else 2207
surplus_from_gap = max(0, current_gap)
remaining = (base_budget + surplus_from_gap) - total_variable_expenses

# --- 💡 全同步更新函式 ---
def sync_update(amount_change):
    # 只負責更新資產表，因為 Gap 是動態算的，下次整理就會對了
    # 但為了讓使用者不用重整就能看到變化，我們還是可以順手更一下 B9
    if not ws_assets: return
    try:
        # 更新資產
        all_assets = ws_assets.get_all_records()
        new_val = 0
        for i, r in enumerate(all_assets):
            if r.get('資產項目') == '台幣活存':
                curr = int(str(r.get('目前價值', 0)).replace(',', ''))
                new_val = curr + amount_change
                ws_assets.update_cell(i+2, 2, new_val)
                break
        
        # 更新狀態表 (B6, B9)
        if ws_status:
            ws_status.update_cell(6, 2, new_val)
            ws_status.update_cell(9, 2, current_gap + amount_change) # 預測新的 Gap
            
    except: pass

# ==========================================
# 側邊欄 (智慧例行事項)
# ==========================================
st.sidebar.title("🚀 功能選單")

def check_logged(keyword):
    if current_month_logs.empty: return False
    return current_month_logs['項目'].astype(str).str.contains(keyword, case=False).any()

def execute_auto_entry(name, amount, type_code="固定", is_transfer=False):
    if not ws_log: return
    date_str = now_dt.strftime("%m/%d")
    
    # 特殊：自我分期 (只記帳+補缺口，不扣資產)
    if name == "自我分期(還債)":
        ws_log.append_row([date_str, name, amount, "固定", 0, "固定扣款"])
        # 這裡不 call sync_update，因為資產沒變
        # 但缺口變了 (還債了)，所以手動更新 B9
        if ws_status:
            try: ws_status.update_cell(9, 2, current_gap + amount)
            except: pass
        st.toast("✅ 還債執行完畢 (資產不變, 缺口縮小)"); time.sleep(1); st.rerun(); return

    # 定存轉帳
    if is_transfer:
        try:
            all = ws_assets.get_all_records()
            twd_r, fix_r, twd_v, fix_v = -1, -1, 0, 0
            for i, r in enumerate(all):
                if r.get('資產項目') == '台幣活存': twd_r=i+2; twd_v=int(str(r.get('目前價值',0)).replace(',',''))
                if r.get('資產項目') == '定存累計': fix_r=i+2; fix_v=int(str(r.get('目前價值',0)).replace(',',''))
            if twd_r!=-1:
                ws_assets.update_cell(twd_r, 2, twd_v - amount)
                ws_assets.update_cell(fix_r, 2, fix_v + amount)
                if ws_status: ws_status.update_cell(6, 2, twd_v - amount) # 同步 B6
                ws_log.append_row([date_str, name, amount, "固定", 0, "固定扣款"])
                st.toast("✅ 定存轉帳完成"); time.sleep(1); st.rerun()
        except: pass
        return

    # 一般固定收支
    is_inc = (type_code == "固定收入")
    change = amount if is_inc else -amount
    ws_log.append_row([date_str, name, amount, "固定", 0, "固定扣款"])
    sync_update(change)
    st.toast("✅ 已記錄"); time.sleep(1); st.rerun()

pending_tasks = []
if current_day >= 5 and not check_logged("固定收入"): pending_tasks.append({"name": "📥 入帳薪水 ($3900)", "type": "fixed_in", "amt": 3900, "desc": "固定收入 (薪水)"})
if current_day >= 10 and not check_logged("定存扣款"): pending_tasks.append({"name": "🏦 轉存定存 ($1000)", "type": "transfer", "amt": 1000, "desc": "定存扣款"})
if current_day >= 10 and not check_logged("電信費"): pending_tasks.append({"name": "📱 繳電信費 ($499)", "type": "fixed_out", "amt": 499, "desc": "電信費"})
if current_day >= 22 and not check_logged("YT Premium"): pending_tasks.append({"name": "▶️ 繳 YT Premium ($119)", "type": "fixed_out", "amt": 119, "desc": "YT Premium"})
if (current_year < 2026 or (current_year == 2026 and current_month < 7)) and current_day >= 6 and not check_logged("小雪"): pending_tasks.append({"name": "❄️ 繳小雪會員 ($75)", "type": "fixed_out", "amt": 75, "desc": "YT會員(小雪)"})
if (current_year < 2026 or (current_year == 2026 and current_month <= 7)) and current_day >= 5 and not check_logged("自我分期"): pending_tasks.append({"name": "💳 自我分期還債 ($2110)", "type": "fixed_out", "amt": 2110, "desc": "自我分期(還債)"})

if pending_tasks:
    st.sidebar.info(f"🔔 待辦事項 ({len(pending_tasks)})")
    for t in pending_tasks:
        if st.sidebar.button(t["name"], key=t["desc"]):
            typ = "固定收入" if t["type"]=="fixed_in" else "固定支出"
            is_tr = (t["type"]=="transfer")
            execute_auto_entry(t["desc"], t["amt"], typ, is_tr)
    st.sidebar.markdown("---")

page = st.sidebar.radio("請選擇功能", ["💸 隨手記帳 (本月)", "🛍️ 購物冷靜清單", "📊 資產與收支", "📅 未來推估", "🗓️ 歷史帳本回顧"])
st.sidebar.markdown("---")
st.sidebar.caption("宇毛的記帳本 v18.2 (Real-Time Gap)")

# ==========================================
# 🏠 頁面 1：隨手記帳
# ==========================================
if page == "💸 隨手記帳 (本月)":
    st.subheader(f"👋 {current_month} 月財務面板")
    col1, col2, col3, col4 = st.columns(4)
    
    gap_color = "green" if current_gap >= 0 else "orange"
    gap_note = "收入優先抵債" if current_gap < 0 else "溢出至額度"
    try: gap_prog = 1.0 - (abs(current_gap) / 3000)
    except: gap_prog = 0
    
    rem_color = "green"
    if remaining < 0: rem_color = "red"
    elif remaining < 50: rem_color = "orange"

    with col1: st.markdown(make_modern_card(f"{current_month}月本金", f"${base_budget}", "固定額度", "blue"), unsafe_allow_html=True)
    with col2: st.markdown(make_modern_card("本月花費", f"${total_variable_expenses}", "僅計流動支出", "gray"), unsafe_allow_html=True)
    with col3: st.markdown(make_modern_card("目前可用", f"${remaining}", "資金安全" if remaining>=0 else "已透支", rem_color), unsafe_allow_html=True)
    with col4: st.markdown(make_modern_card("總透支缺口", f"${current_gap}", gap_note, gap_color, progress=gap_prog), unsafe_allow_html=True)

    if pending_debt > 0: st.caption(f"ℹ️ 包含 ${pending_debt} 未入帳的代墊款。")
    if remaining < 0: st.error("🚨 警告：本月已透支！請停止支出！")

    st.markdown("---")
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
                st.info("💡 代墊款會扣除資產。")
                reimburse_target = st.text_input("幫誰代墊？", placeholder="例如: Andy")
                is_reimbursable = "是"
            else: is_reimbursable = "否"
        else: st.caption("ℹ️ 收入預設為 **「未入帳」**")
            
        if st.form_submit_button("確認記帳", use_container_width=True, type="primary") and ws_log:
            if item_input and amount_input > 0:
                d_str = date_input.strftime("%m/%d")
                name = f"{item_input} ({reimburse_target})" if reimburse_target else item_input
                
                if "支出" in txn_type:
                    act = amount_input
                    sta = "未入帳" if is_reimbursable == "是" else "已入帳"
                    ws_log.append_row([d_str, name, amount_input, is_reimbursable, act, sta])
                    sync_update(-amount_input)
                    st.toast(f"💸 支出已記：${amount_input}")
                else:
                    ws_log.append_row([d_str, name, amount_input, "收入", 0, "未入帳"]) # 收入先不更動資產
                    st.toast(f"💰 收入已記 (未入帳)：${amount_input}")
                time.sleep(1); st.rerun()

    if not current_month_logs.empty:
        st.markdown("### 📜 本月明細")
        for i, (idx, row) in enumerate(current_month_logs.iloc[::-1].iterrows()):
            real_idx = idx + 5 
            cls = "一般"
            if row['是否報帳'] == "是": cls = "報帳/代墊"
            elif row['是否報帳'] == "收入": cls = "收入"
            elif row['是否報帳'] == "固定": cls = "固定收支"
            
            sta = str(row.get('已入帳', '已入帳')).strip() or "已入帳"
            
            clr, txt, pfx = "gray", "var(--text-color)", "$"
            if cls == "收入": clr="green" if sta=="已入帳" else "gray"; txt="#2dce89" if sta=="已入帳" else "var(--text-color)"; pfx="+$"
            elif cls == "報帳/代墊": clr="purple" if sta=="未入帳" else "gray"; txt="#8e44ad" if sta=="未入帳" else "var(--text-color)"
            elif cls == "固定收支": clr="blue"; txt="#3498db"
            else: txt="#f5365c"; pfx="-$"

            with st.container():
                c1, c2, c3 = st.columns([3, 1.5, 1])
                c1.markdown(f"""<div style="line-height:1.4;"><span style="font-size:0.85em; opacity:0.7;">{row['日期']}</span><br><span style="font-weight:600;">{row['項目']}</span><br>{make_badge(sta, clr)} <span style="font-size:0.8em; opacity:0.6;">{cls}</span></div>""", unsafe_allow_html=True)
                c2.markdown(f"<div style='margin-top:10px;'><span style='color:{txt}; font-weight:800; font-size:1.1em;'>{pfx}{row['金額']}</span></div>", unsafe_allow_html=True)
                if cls in ["報帳/代墊", "收入"]:
                    is_clr = (sta == "已入帳")
                    lbl = "已結清?" if "報帳" in cls else "已入帳?"
                    if c3.toggle(lbl, value=is_clr, key=f"tg_{idx}") != is_clr:
                        new_s = "未入帳" if is_clr else "已入帳"
                        # 資產變動
                        chg = 0
                        if "報帳" in cls: chg = row['金額'] if not is_clr else -row['金額'] # 未->已: +
                        elif cls == "收入": chg = row['金額'] if not is_clr else -row['金額']
                        
                        if chg != 0: sync_update(chg)
                        ws_log.update_cell(real_idx, 6, new_s)
                        st.success("已更新"); time.sleep(0.5); st.rerun()
        st.markdown("---")

# ==========================================
# 🛍️ 頁面 2：購物冷靜清單
# ==========================================
elif page == "🛍️ 購物冷靜清單":
    st.subheader("🧊 購物冷靜清單")
    df_shop, ws_shop = get_data("購物冷靜清單")
    total = sum([int(str(r.get('預估價格', 0)).replace(',', '')) for i, r in df_shop.iterrows()]) if not df_shop.empty else 0
    
    d1, d2 = st.columns(2)
    with d1: st.markdown(make_modern_card("清單總項數", f"{len(df_shop)} 項", "慾望清單", "blue"), unsafe_allow_html=True)
    with d2: st.markdown(make_modern_card("預估總金額", f"${total:,}", "需存錢目標", "orange"), unsafe_allow_html=True)
    st.markdown("---")
    
    with st.expander("➕ 新增願望", expanded=False):
        with st.form("add_shop"):
            c1, c2 = st.columns(2)
            n = c1.text_input("物品"); p = c2.number_input("價格", min_value=0)
            if st.form_submit_button("加入", type="primary") and ws_shop:
                ws_shop.append_row([datetime.now().strftime("%m/%d"), n, p, "3", "2026/07/01", "延後", ""])
                st.success("已加入"); time.sleep(1); st.rerun()

    if not df_shop.empty:
        st.markdown("### 📦 明細")
        for i, row in df_shop.iterrows():
            n = row.get('物品名稱', '未命名'); p = row.get('預估價格', 0); d = row.get('最終決策', '考慮'); note = row.get('備註', '')
            with st.expander(f"🛒 **{n}** - ${p}"):
                st.markdown(f"**決策：** {d} | **備註：** {note}")
                if st.button("🗑️ 刪除", key=f"del_{i}"): ws_shop.delete_rows(i+2); st.toast("已刪除"); time.sleep(1); st.rerun()

# ==========================================
# 📊 頁面 3：資產與收支
# ==========================================
elif page == "📊 資產與收支":
    st.subheader("💰 資產狀況")
    if not df_assets.empty:
        ad = dict(zip(df_assets['資產項目'], df_assets['目前價值']))
        t = int(str(ad.get('總資產', 0)).replace(',', ''))
        st.markdown(make_modern_card("目前總身價", f"${t:,}", "含所有資產", "blue"), unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown(f"""<div class="asset-card"><div class="asset-val">${ad.get('台幣活存',0)}</div><div class="asset-lbl">🇹🇼 台幣活存</div></div>""", unsafe_allow_html=True)
        with c2: st.markdown(f"""<div class="asset-card"><div class="asset-val">¥{ad.get('日幣帳戶',0)}</div><div class="asset-lbl">🇯🇵 日幣帳戶</div></div>""", unsafe_allow_html=True)
        with c3: st.markdown(f"""<div class="asset-card"><div class="asset-val">${ad.get('定存累計',0)}</div><div class="asset-lbl">🏦 定存累計</div></div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("📉 每月固定收支")
    df_model, _ = get_data("每月收支模型")
    if not df_model.empty:
        for i, row in df_model.iterrows():
            if str(row.get('金額 (B)','')).strip(): st.markdown(f"**{row['項目 (A)']}**: ${row['金額 (B)']}")

# ==========================================
# 📅 頁面 4 & 5
# ==========================================
elif page == "📅 未來推估":
    st.subheader("🔮 財務預測")
    if not df_future.empty:
        rows = [df_future.iloc[i:i+3] for i in range(0, len(df_future), 3)]
        for batch in rows:
            cols = st.columns(3)
            for i, (idx, row) in enumerate(batch.iterrows()):
                if i < 3 and "初始" not in str(row['月份 (A)']):
                    with cols[i]: st.markdown(f"""<div class="asset-card"><div style="font-weight:bold;">{row['月份 (A)']}</div><div style="font-size:12px;">目標: ${row['目標應有餘額 (E)']}</div><div style="font-size:18px;color:#5e72e4;">${row['預估實際餘額 (D)']}</div></div>""", unsafe_allow_html=True)

elif page == "🗓️ 歷史帳本回顧":
    st.subheader("🗓️ 歷史帳本")
    if not df_log.empty:
        ms = sorted([m for m in df_log['Month'].unique() if m > 0])
        if ms:
            sel = st.selectbox("月份", ms, index=len(ms)-1)
            h = df_log[df_log['Month'] == sel]
            st.markdown(make_modern_card(f"{sel}月 淨支出", f"${int(h['實際消耗'].sum())}", "", "gray"), unsafe_allow_html=True)
            for i, r in h.iloc[::-1].iterrows():
                c = "#2dce89" if r['實際消耗'] < 0 else "#f5365c"
                st.markdown(f"""<div class="list-item"><div><span>{r['日期']}</span><br><b>{r['項目']}</b></div><div style="color:{c};font-weight:bold;">${r['金額']}</div></div>""", unsafe_allow_html=True)
