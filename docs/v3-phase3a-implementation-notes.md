# 階段 3A 實作筆記

## A：物理模型
- 混合器採理想完全混合槽質量平衡；先積分成最大間距 0.002 min 的入口表，再沿既有體積傳輸。混合槽平均延遲額外加在純平移延遲上。
- mixer_ml=0 保留原求解路徑；啟用時使用 ODE。地圖上限 2,000 候選；多段搜尋最多 2,000 次評估，沿用工作時間及雙運算槽限制。
- 柱效預設 fixed；選 van_deemter 時採 Knox 約化式，以洗提時流速計算 N。A/B/C、Dm 與流阻因子為典型參考值，未經驗證。
- 固定約化流速 ν 時，N 與粒徑反比；固定流速時粒徑同時改變 ν，不能單獨宣稱反比。
- 黏度採 Guillarme、Heinisch、Rocca (2004), J. Chromatogr. A 1052, 39–51, Table 2：
  https://doi.org/10.1016/j.chroma.2004.08.052 。使用 25、60、90 °C 與 φ=0、0.2、0.4、0.6、0.8、1 表格。
- 純有機黏度採表格溫度的 log 線性插值；混合物採原文式 26/27 的非理想組成曲率，將 log10 黏度扣除兩端線性基線，再加上 Vogel 水與純有機表格端點的 log10 基線。此為明示的端點正規化，並非原文未調整擬合式；共同適用範圍 25–90 °C、φ 0–1，範圍外明示外推。
- 純水依指定 Vogel 式；純有機採相同文獻表格端點。未計入壓力、鹽、緩衝液對黏度的影響。
- Darcy 壓力式 ΔP=ΦηLu_s/dp²：Snyder、Kirkland、Dolan，Introduction to Modern Liquid Chromatography，3rd ed. (2010)。
- 壓力以入口組成至少 201 點加節點取樣，未沿管柱軸向積分。單次模擬超限只警告；最佳化標為不可行。未設定上限時，最佳化跳過壓力取樣。
- 不變更 Render、render.yaml、.gitignore；不改既有 A/B 來源與資料。

## 程式測試
- 測混合槽階躍／線性輸入閉式解、零體積路徑、單一固定程式的延遲性質。
- 測 Knox 極小點方程、SI 換算與比例關係；Darcy 比例、黏度端點、API 預設與拒絕未知欄位。
- 桌面流程檢查新欄位、中文說明、理論板數、最高壓力與超限警告。
- 科學數據工作只限 B 部分登記程序，沒有下載新實驗資料。

## 待使用者確認
- 混合槽對實際儀器梯度的描述、實測延遲與混合器體積。
- Knox 係數、擴散係數與洗提時 N 是否適合使用者管柱。
- 流阻因子、入口黏度近似、實際系統壓力與限制值。
- 等級 C 參數在使用者實驗條件下的使用方式。

## B：登記候選
- 僅使用 repo 的 273 筆曲線、既有 seed 42 scaffold 分割與訓練組標準化；C5/C6/C7 符號限制與 S–logKw 轉換照需求實作。
- C5：19/19 門檻，Rt 範圍 0.8307348662834384 min，logk35 測試組 MAE 0.4456223631208842。
- C6：19/19 門檻，Rt 範圍 0.8869785503903049 min，logk35 測試組 MAE 0.44175445165556565。
- C7：19/19 門檻，Rt 範圍 0.8869785503903049 min，logk35 測試組 MAE 0.44175445165556565。
- 登記規則選 C6（C6/C7 同值時依登記次序）；版本 3.0.0，保留 generic-lss-v2.json。不變更 A/B 模型。
- review/phase3a/tier-c-candidates.csv 與 tier-c-sanity-molecules.csv 僅記錄登記結果；數據判讀由使用者進行。
- 原模型來源與 CC BY-NC-SA 3.0 US、非商業用途限制維持；係數狀態欄維持原待使用者確認代碼。

## 修改既有測試與原因
- frontend/tests/p0-estimation.spec.ts 的峰表 CSV 表頭：新增 plates_used、max_pressure_bar、time_at_max_pressure_min，原欄位保留。
- backend/tests/test_sanity_ordering.py：經使用者明確同意，僅 test_transformed_equation_identity 的 selected_candidate 從 C2 改為 C6。原因＝階段 3A 第 6 節的預先登記選擇規則選出新候選，測試中硬寫的候選名稱需同步。其餘門檻、斷言與容差不變。另一個 C2 斷言是歷史 2.1 報告，保持原樣。
- backend/tests/test_estimation.py 的 test_generic_equation_and_clipping：改依模型 metadata 的特徵名稱組向量，保留原推論及裁切斷言。
- 同檔 test_fit_groups_and_standardization_use_training_rows_only：從原訓練記錄的 SMILES 計算模型記載特徵，保留原分組隔離、平均值與資料筆數斷言；新模型新增兩個登記特徵，不能繼續固定五維。
- workflow-repair.spec.ts 不需修改：壓力設定使用一般設定容器，第一個結果 section 仍為層析圖。

## 本機執行記錄
- 修改前 pytest（依常設規則排除原合理性測試檔）：91 通過。
- 本次完整 pytest -q：118 通過，0 失敗；含第 6 節例外所允許的原門檻。原 Starlette 提醒仍存在。
- pnpm --dir frontend build：完成；保留既有單一大型 bundle 提醒。
- 桌面 Playwright：17 通過，0 失敗；九個分頁殘留英文清單為空（保留產品名稱）。
- 最後黏度式調整後，新物理設定桌面流程另重跑：1 通過。
- 舊 JSON 測試另移除新欄位後重跑：1 通過。
- 混合器地圖，1 候選 × 3 成分、含 ODE 重算，本機 1.984000 s；候選上限 2,000，多段評估上限 2,000，既有 jobs 30 s 限制保持。
- 完整輸出保存在本機 artifacts/phase3a-pytest-output.txt、phase3a-playwright-output.txt、phase3a-physics-playwright-output.txt；artifacts 維持既有忽略設定。
- 數據判讀、儀器參數及條件使用方式由使用者確認，本文不作實驗結論。
