# 階段 2 實作說明

本階段只處理定流速 LSS 的解析遷移、解析度地圖、多段搜尋及既有最佳化分頁。實驗數據與用途判斷由使用者執行。

## 修改內容

- backend/elusim/analytic.py：以 u=t−x·t0 變換，逐段累積 ∫du/k=t0，使用 expm1 / log1p 處理梯度段與其反解。支援起始 hold、dwell、step 與最後無限 hold；呼叫端以程式結束時間截斷溶出事件。純量版回傳原生 Python 數值；NumPy 批次版計算候選 × 化合物。
- backend/elusim/engine.py：solver=auto / analytic 的定流速輸入走解析路徑；變流速回退 ODE，回傳實際 solver。峰寬、注入與柱外變異數、峰面積、校正流程維持既有定義。多段峰寬仍是出口局部近似。
- backend/elusim/optimizer.py：地圖以 NumPy 批次計算，依可行條件、run time、min Rs 排名；前十筆逐一 ODE 重算，另回傳最多三十筆非支配候選。
- 多段搜尋使用 SciPy differential_evolution，seed 固定、polish=False；排序內部分率與正時間權重保證組成單調與時間遞增。可加入地圖候選作為初始族群成員。時間上限停止後回傳已計算候選，另作 ODE 重算。這是有限時間的隨機搜尋。
- schemas.py、main.py、jobs.py：保留舊 /api/optimize；新增 map 與 multisegment routes、請求上限、兩個程序工作槽及三十秒 timeout。多段 HTTP 斷線時設取消事件，停止其程序。
- sources.py：舊來源代碼保留，顯示文字改為待使用者檢查；舊標籤字串仍可遷移。
- OptimizationWorkspace.tsx：搜尋範圍由使用者輸入；參數來源不縮限範圍。提供 ECharts 地圖、起始切片、候選表、Pareto、2/3 段搜尋、取消、明確確認後套用與重新模擬、CSV/JSON 匯出。手機圖表及表格在區塊內捲動。
- 原模型、係數、資料檔、UV/DAD、化合物與校正工作區不變。render.yaml、.gitignore 及 Render 設定不變。

公式來源：Snyder & Dolan, High-Performance Gradient Elution (Wiley, 2007)；Poppe et al., J. Chromatogr. 204 (1981) 77–84；Schoenmakers et al., J. Chromatogr. 205 (1981) 13–30。只依公式自行實作，未引入其他模擬器程式。

## 程式檢查

- test_analytic.py：六組線性公式、220 組 seed=42 合成多段/step/hold/dwell 程式、純量與批次比對、變流速回退與有限時間窗。ODE 比較使用 rtol=1e-10、max_step=0.05 min。
- test_optimize_map.py：形狀、null、預先拒絕過量/變流速請求、排名、非支配性、ODE 欄位、回應大小及二萬候選 × 五化合物耗時。
- test_optimize_multisegment.py：兩段/三段、固定 seed、組成/時間單調、時間預算停止及初始候選。
- 舊 test_linear_gradient_closed_form 改用 1e-7 相對容差比較 ODE 與解析結果；不要求兩個浮點運算路徑逐位相同。其比較檔改寫 pytest 暫存目錄，使非 root 容器測試不寫入原始碼目錄。
- 舊 workbench 與 retention-integration 瀏覽器測試改為新版範圍欄位及地圖/候選操作；套用增加確認對話。原有其他操作仍保留。
- optimizer.spec.ts：桌面及 Pixel 7 尺寸，實際 SMILES 估算與 API 地圖、地圖點擊、候選/Pareto 套用、重算、三種匯出、多段搜尋/取消及橫向溢出。
- scripts/export_phase2.py：只用 Synthetic A/B/C 產生地圖與兩段搜尋輸出。原始數字在 review/phase2；不提供科學結論。

重現指令（PowerShell，於專案根目錄執行）：

    $env:OPENBLAS_NUM_THREADS="1"
    $env:OMP_NUM_THREADS="1"
    $env:ELUSIM_REVIEW_DIR="C:\Users\T22016\Desktop\程式\EluSims\review\phase2"
    & ".venv/Scripts/python.exe" -m pytest -q
    $env:PYTHONPATH="backend"
    & ".venv/Scripts/python.exe" "scripts/export_phase2.py"
    & ".venv/Scripts/python.exe" -m uvicorn elusim.main:app --host 127.0.0.1 --port 8112
    # 另一個 PowerShell，於 frontend：
    $env:ELUSIM_BASE_URL="http://127.0.0.1:8112"
    pnpm build
    pnpm exec playwright test --reporter=list

最後一次完整輸出與數字摘要見 review/phase2/phase2-report.md。

## 待使用者以實驗數據檢查

1. logKw/S 及 A/B/C 來源參數對指定化學系統的可用性：既有 backend/models 與 data/retention 不變。
2. 多段/step 梯度的 Rt、出口局部峰寬近似與 Rs：review/phase2/analytic-vs-ode.csv、backend/elusim/analytic.py、engine.py。
3. 地圖候選對實際管柱、溶劑、溫度、pH、進樣條件的適用性：review/phase2/map-demo.json、map-demo.csv。
4. 多段搜尋候選與實際方法限制：review/phase2/multisegment-demo.json。
5. 色譜訊號仍是相對響應，不是定量 UV、RI 或 MS 偵測器輸出。

## 邊界

- 流速變化只能單次 ODE 模擬；地圖與多段搜尋要求定流速。
- 未在程式結束前溶出者不生成虛構峰。峰寬的局部近似不因解析 Rt 而變成實驗結論。
- 地圖最多二萬候選、四十萬候選/化合物組合；另限制儲存格四萬與 JSON 一 MiB。長 Compound ID 可能需減少 steps。
- 多段搜尋時間預算控制搜尋本身；ODE 重算另需時間，整個工作仍受三十秒上限。
- 相同 seed 在未觸發時間停止時可重現；觸發時間停止時，硬體/負載可改變最後完成的世代。
- 多段搜尋的取消會中止客戶端請求並終止其運算程序；連線中斷的偵測速度也受 ASGI/網路環境影響。
- 未加入壓力、混合器、van Deemter、Neue–Kuss、Monte Carlo 或係數重訓。

- run_time_min 按最後峰 tR+3σ 定義，不等於完整梯度、清洗與再平衡週期；程式最後節點另見 gradient。

- 完整瀏覽器測試共用同一個本機 IP；tests/fixtures.ts 將真實 POST 排程為每 61 秒最多 25 次，跨桌面／手機 worker 共用時間戳，保留正式伺服器每分鐘 30 次限制。未修改科學 API 回應。
