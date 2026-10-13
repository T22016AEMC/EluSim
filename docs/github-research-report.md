# GitHub 開源專案調查報告

研究截止：2026-10-13（Asia/Taipei）。工作分支 `research/lc-open-source-20261013`。原工作目錄沒有Git與應用檔案；經授權建立研究分支。本次僅新增研究文件、證據及隔離測試腳本，没有建立正式平台或合併main。

## 結論與採用邊界

**不存在已查到、授權清楚且足以取代大部分原定平台開發工作的單一開源專案。唯一首選是方案B：自有整合Repository，優先PyLSS的RP核心，並以CADET-Process／CADET-Core作為後續傳輸模型與科學運算架構。** 後兩者尚未本機測試，且Core授權標頭衝突需確認；屬有門檻的建議，不是已驗證可部署承諾。唯一備選是方案C，若copyleft或CADET門檻不能接受，獨立建立經驗證的RP／SEC核心、採寬鬆授權基礎套件，OpenIEX修正並驗證後才加入IEX。

PyLSS最值得直接整合；STLC適合數值對照，OpenIEX為需修正的IEX候選。2-step、TIMPANI、MIT QSRR與DeepLC可做分開的選配結構／校正服務。GRIP功能很貼近需求但無明確授權；MDL-TL、GNN-TL、NonlinearGradientsUI及舊Java研究程式同樣不能直接複製。Graphormer-RT沒有完整專案／权重授權證據；AutoLC-BO有NC限制。

名稱解析、繪圖與批次輸入、跨模式參數契約、未知分子的適用域、pH／溫度／混合機制、聚合物與蛋白特定模型、可信度校準、React網站、API與任務管理仍需自行開發。物理求解器不會自動從SMILES取得固定相吸附參數。

## 調查方法與限制

先深入8個指定repo，再以GitHub／網頁搜尋 LC retention time prediction、HPLC gradient simulation、chromatography method optimization、QSRR、HILIC、normal phase、ion exchange、digital twin、peak simulation；額外檢查CADET、Graphormer-RT、DeepLC、RepoRT、mzrtsim、AutoLC-BO、GNN-TL、MIT QSRR及舊Java工具。搜尋是候選篩選，不是完整GitHub普查。

以GitHub API固定HEAD SHA、commit日期、recursive tree、issue/PR最近20筆與依賴／LICENSE／核心／測試檔檢查。匿名API後續403限流；補充用git ls-remote、固定SHA codeload及commit.patch。patch只取得作者日期的repo已明示，不能混當最新提交者日期。部分單檔下载失败／不存在記入source-review-index，不算成功閱讀；完整源碼資產存在與本次抽樣審查深度是不同概念。

下載文字源碼與範例到TEMP；未載入未知序列化權重。3個環境分開安裝，不修改全域或應用依賴。使用自行設計的合成三成分probe；這不是化合物結構預測或論文精度復現。測試內容、環境版本、失敗日誌及數值見[比較與測試](open-source-comparison.md)。

上游研究連結／RESULTS／資料拆分只標為作者證據；本次未重現外部資料。部分期刊／preprint全文受403限制，因此不捏造MAE、R²或跨模式精度。無測試覆蓋率量測、無完整dependency SBOM、無模型權重獨立法律結論；見[授權審查](license-review.md)。

## 優先八個Repository：逐項12維評估

### gmrandazzo/PyLSS

[GitHub](https://github.com/gmrandazzo/PyLSS) · [固定commit](https://github.com/gmrandazzo/PyLSS/commit/d2cda850fa0b0881fc3cf1cd68c4d93b59dac04f)

`d2cda850fa0b0881fc3cf1cd68c4d93b59dac04f`

|評估項目|檢查結果|
|---|---|
|2 維護／Issue／測試|固定HEAD最後提交：2026-05-01T08:46:56Z。open_issues_count=0（包含PR，不是純Issue數）；已取最近0筆all-state issue/PR清單。 tree中測試相關路徑10、workflow路徑2；路徑數不是覆蓋率，無本次量測coverage。|
|1 源碼／授權|完整 Python 原始碼；AGPL-3.0-or-later（LICENSE 與檔案標頭）。|
|3 語言／依賴／環境|Python；NumPy、SciPy、Matplotlib、PyYAML；GUI 另有 PyQt6。隔離測試採 Python 3.12.14，省略 GUI。|
|4 安裝／重現|本機 editable 安裝及 headless probe 成功；上游 pytest 6 項通過。NLSS 匯入失敗，不能宣稱全套成功。|
|5 方程式／模型|LSS：log10(k)=logKw−Sφ；解析梯度 Rt；simplex 擬合參數與梯度搜尋。|
|6 Rt／Rs／梯度／圖形|真正由參數計算 Rt、峰寬、Rs；Gaussian 圖形是理想化重建。零梯度回傳 9999；寬度／Rs 定義需校驗。|
|7 實驗Rt需求|已有 logKw/S 可直接運作；從未知樣本估計參數需多個實驗梯度 Rt。|
|8 SMILES未知化合物|沒有 SMILES／名稱推斷 logKw/S；未知結構零資料無法可靠預測。|
|9 Python／React API|原生 Python 可呼叫，適合薄 API 包裝； GUI 與數值計算分離。|
|10 權重／參數／資料|無結構預訓練權重；範例、測試、管柱／LSS 参数可重用；參數不能跨模式自動移植。|
|11 準確度／外部驗證|測試證明執行與參數敏感性，不是外部 Rt 準確度；六個單元測試不能代表實驗驗證。|
|12 公開網頁可用性|優先整合 RP 科學核心。AGPL 網路互動相應原始碼義務須履行；NLSS、欄轉移及 Rs 須另驗證。|

核心來源：[src/pylss/ssengine.py](https://github.com/gmrandazzo/PyLSS/blob/d2cda850fa0b0881fc3cf1cd68c4d93b59dac04f/src/pylss/ssengine.py)、[src/pylss/nlssengine.py](https://github.com/gmrandazzo/PyLSS/blob/d2cda850fa0b0881fc3cf1cd68c4d93b59dac04f/src/pylss/nlssengine.py)、[src/pylss/gradientutils.py](https://github.com/gmrandazzo/PyLSS/blob/d2cda850fa0b0881fc3cf1cd68c4d93b59dac04f/src/pylss/gradientutils.py)、[src/pylss/plotengine.py](https://github.com/gmrandazzo/PyLSS/blob/d2cda850fa0b0881fc3cf1cd68c4d93b59dac04f/src/pylss/plotengine.py)、[src/pylss/optseparation.py](https://github.com/gmrandazzo/PyLSS/blob/d2cda850fa0b0881fc3cf1cd68c4d93b59dac04f/src/pylss/optseparation.py)、[src/pylss/lsscoltransfer.py](https://github.com/gmrandazzo/PyLSS/blob/d2cda850fa0b0881fc3cf1cd68c4d93b59dac04f/src/pylss/lsscoltransfer.py)、[tests/test_ssengine.py](https://github.com/gmrandazzo/PyLSS/blob/d2cda850fa0b0881fc3cf1cd68c4d93b59dac04f/tests/test_ssengine.py)、[tests/test_optimizer.py](https://github.com/gmrandazzo/PyLSS/blob/d2cda850fa0b0881fc3cf1cd68c4d93b59dac04f/tests/test_optimizer.py)、[tests/test_chromanalysis.py](https://github.com/gmrandazzo/PyLSS/blob/d2cda850fa0b0881fc3cf1cd68c4d93b59dac04f/tests/test_chromanalysis.py)、[LICENSE](https://github.com/gmrandazzo/PyLSS/blob/d2cda850fa0b0881fc3cf1cd68c4d93b59dac04f/LICENSE)。

### gurevichlab/grip

[GitHub](https://github.com/gurevichlab/grip) · [固定commit](https://github.com/gurevichlab/grip/commit/4247e26580d6ad050125741833dedae8e9ba5370)

`4247e26580d6ad050125741833dedae8e9ba5370`

|評估項目|檢查結果|
|---|---|
|2 維護／Issue／測試|固定HEAD最後提交：2026-06-10T09:38:48Z。open_issues_count=0（包含PR，不是純Issue數）；已取最近0筆all-state issue/PR清單。 tree中測試相關路徑3、workflow路徑0；路徑數不是覆蓋率，無本次量測coverage。|
|1 源碼／授權|核心與 checkpoint 可見；固定版本未找到專案 LICENSE，不能當作可直接重用開源。|
|3 語言／依賴／環境|Python ≥3.10（環境檔較新）；PyTorch、Lightning、Chemprop 2.0.4、RDKit、NumPy<2。pyproject dependencies 空，環境檔才有完整依賴。|
|4 安裝／重現|原始碼／資產檢查；未安裝或下載 checkpoint，未重現推論。|
|5 方程式／模型|圖神經網路預測 ln(k0)、ln(S)，以梯度积分条件求 Rt；結構與方法特徵共同輸入。|
|6 Rt／Rs／梯度／圖形|計算梯度 Rt；沒有完整傳輸峰形、峰寬／Rs 引擎；查找分段梯度與未洗脫處理需審查。|
|7 實驗Rt需求|預訓練模型推論不要求該未知化合物實測 Rt，但訓練依賴歷史實驗與方法描述，並非純物理零資料模型。|
|8 SMILES未知化合物|程式接受結構資訊／SMILES，需模型與方法特徵；本次未實測。|
|9 Python／React API|可包 Python 推論 API，但環境重、wheel 子套件打包須驗證，且授權先阻擋。|
|10 權重／參數／資料|model/model-i6kwrq9u.ckpt 約12.4 MB 存在；未獨立确认權重與訓練資料授權。|
|11 準確度／外部驗證|有研究／資料拆分程式；未重現外部驗證，不能轉述準確度為本平台效能；輸出的 q 是梯度段索引，不是可信度。|
|12 公開網頁可用性|科學設計很值得借鑑；先向作者取得程式、權重、資料明確授權，未取得前排除直接整合。|

核心來源：[grip/models/grip.py](https://github.com/gurevichlab/grip/blob/4247e26580d6ad050125741833dedae8e9ba5370/grip/models/grip.py)、[grip/models/layers.py](https://github.com/gurevichlab/grip/blob/4247e26580d6ad050125741833dedae8e9ba5370/grip/models/layers.py)、[grip_inference.py](https://github.com/gurevichlab/grip/blob/4247e26580d6ad050125741833dedae8e9ba5370/grip_inference.py)、[grip/featurizers/system_descriptors.py](https://github.com/gurevichlab/grip/blob/4247e26580d6ad050125741833dedae8e9ba5370/grip/featurizers/system_descriptors.py)。

### sartorius-research/STLC

[GitHub](https://github.com/sartorius-research/STLC) · [固定commit](https://github.com/sartorius-research/STLC/commit/e482802bdd311a615c963c2adc65694e8f488cf3)

`e482802bdd311a615c963c2adc65694e8f488cf3`

|評估項目|檢查結果|
|---|---|
|2 維護／Issue／測試|固定HEAD最後提交：2023-03-13T21:22:57Z。open_issues_count=0（包含PR，不是純Issue數）；已取最近0筆all-state issue/PR清單。 tree中測試相關路徑0、workflow路徑0；路徑數不是覆蓋率，無本次量測coverage。|
|1 源碼／授權|完整 Python 原始碼；GPL-3.0。|
|3 語言／依賴／環境|Python、NumPy、SciPy、Matplotlib；正交配置（collocation）空間離散。|
|4 安裝／重現|本機安装与3成分傳輸測試成功；長度與步長變化已測；無原生溶劑梯度映射可測。|
|5 方程式／模型|Lumped Kinetic Model／General Rate Model；對流、軸向擴散、吸附動力學及顆粒傳輸。|
|6 Rt／Rs／梯度／圖形|解濃度波形並取峰頂 Rt；FWHM 與 Rs 是本次外加分析。是真實傳輸方程，非單純示意圖。|
|7 實驗Rt需求|給定吸附／動力學／傳輸參數可無實測 Rt 執行；參數辨識仍需資料或可信來源。|
|8 SMILES未知化合物|沒有 SMILES；無法从結構自動取得 a、b、k、D。|
|9 Python／React API|Python 可直接 import；適合作為數值對照與教學後端，API 單位規範需補。|
|10 權重／參數／資料|範例與數值實作，沒有分子預訓練模型／通用固定相資料庫。|
|11 準確度／外部驗證|本測試三條有限波形有微小負濃度；dt減半峰寬改變，尚未達網格收斂。源碼文件時間積分描述與實作需核對。|
|12 公開網頁可用性|可作峰形對照。GPL 分發／衍生程式義務見授權文件；不建議承擔整個多模式架構。|

核心來源：[stlc/lkm.py](https://github.com/sartorius-research/STLC/blob/e482802bdd311a615c963c2adc65694e8f488cf3/stlc/lkm.py)、[stlc/grm.py](https://github.com/sartorius-research/STLC/blob/e482802bdd311a615c963c2adc65694e8f488cf3/stlc/grm.py)、[stlc/occ.py](https://github.com/sartorius-research/STLC/blob/e482802bdd311a615c963c2adc65694e8f488cf3/stlc/occ.py)、[examples/lkm/multi_component.py](https://github.com/sartorius-research/STLC/blob/e482802bdd311a615c963c2adc65694e8f488cf3/examples/lkm/multi_component.py)、[LICENSE](https://github.com/sartorius-research/STLC/blob/e482802bdd311a615c963c2adc65694e8f488cf3/LICENSE)。

### jonkeeley/openiex

[GitHub](https://github.com/jonkeeley/openiex) · [固定commit](https://github.com/jonkeeley/openiex/commit/ecf795e93eb44bfe7330bda219d87890299978ef)

`ecf795e93eb44bfe7330bda219d87890299978ef`

|評估項目|檢查結果|
|---|---|
|2 維護／Issue／測試|固定HEAD最後提交：2025-05-28T17:14:40Z。open_issues_count=0（包含PR，不是純Issue數）；已取最近0筆all-state issue/PR清單。 tree中測試相關路徑0、workflow路徑0；路徑數不是覆蓋率，無本次量測coverage。|
|1 源碼／授權|完整 Python 包與範例；MIT。|
|3 語言／依賴／環境|Python、NumPy、SciPy、Matplotlib、pandas、tqdm；notebook進度條本測試另需ipywidgets。|
|4 安裝／重現|隔離安裝初次300秒超時，重試成功；三個案例完成，狀態EXECUTED_REVIEW_REQUIRED。序列化不一致，梯度敏感性未證實。|
|5 方程式／模型|IEX：鹽／蛋白質的運輸、位點佔用與多價離子交換動力學；BDF solve_ivp。|
|6 Rt／Rs／梯度／圖形|多蛋白鹽梯度濃度曲線可求峰頂／寬度；本次外加 FWHM-Rs，不可當作原生 Rs API。|
|7 實驗Rt需求|不強制實測 Rt，但需 lnK、價數、容量、擴散等蛋白／固定相參數。|
|8 SMILES未知化合物|沒有任意 SMILES／蛋白序列到吸附參數模型。|
|9 Python／React API|原生 Python；可包 API，但 solver 失敗狀態應保留。|
|10 權重／參數／資料|物種、柱、方法物件及教學範例；沒有經驗證通用蛋白參數庫／權重。|
|11 準確度／外部驗證|set_equilibrium 的 reverse lnK 寫成1−lnK；to_dict/from_dict往返需審查。solve_ivp成功／錯誤訊息未暴露。無外部准确度重現。|
|12 公開網頁可用性|MIT 元件有價值，適合後續修正與驗證的 IEX 備選；不能直接當作可靠蛋白設計引擎。|

核心來源：[src/openiex/physics.py](https://github.com/jonkeeley/openiex/blob/ecf795e93eb44bfe7330bda219d87890299978ef/src/openiex/physics.py)、[src/openiex/system.py](https://github.com/jonkeeley/openiex/blob/ecf795e93eb44bfe7330bda219d87890299978ef/src/openiex/system.py)、[src/openiex/solver.py](https://github.com/jonkeeley/openiex/blob/ecf795e93eb44bfe7330bda219d87890299978ef/src/openiex/solver.py)、[src/openiex/species.py](https://github.com/jonkeeley/openiex/blob/ecf795e93eb44bfe7330bda219d87890299978ef/src/openiex/species.py)、[src/openiex/method.py](https://github.com/jonkeeley/openiex/blob/ecf795e93eb44bfe7330bda219d87890299978ef/src/openiex/method.py)、[src/openiex/analysis.py](https://github.com/jonkeeley/openiex/blob/ecf795e93eb44bfe7330bda219d87890299978ef/src/openiex/analysis.py)、[LICENSE](https://github.com/jonkeeley/openiex/blob/ecf795e93eb44bfe7330bda219d87890299978ef/LICENSE)。

### boecker-lab/2-step

[GitHub](https://github.com/boecker-lab/2-step) · [固定commit](https://github.com/boecker-lab/2-step/commit/74c2675e8482f3d588bf8bb4bc47433f9200e68f)

`74c2675e8482f3d588bf8bb4bc47433f9200e68f`

|評估項目|檢查結果|
|---|---|
|2 維護／Issue／測試|固定HEAD最後提交：2026-10-12T09:05:33Z。open_issues_count=0（包含PR，不是純Issue數）；已取最近3筆all-state issue/PR清單。 tree中測試相關路徑6、workflow路徑4；路徑數不是覆蓋率，無本次量測coverage。|
|1 源碼／授權|完整核心、容器與模型；AGPL-3.0。|
|3 語言／依賴／環境|Python3.12、Chemprop1.6.1、PyTorch、RDKit、PuLP、statsmodels、NumPy<2；與 GRIP/TIMPANI 環境不宜混裝。|
|4 安裝／重現|檢查原始碼、CI與權重清單；本次未安装／推論，不宣稱容器測試通過。|
|5 方程式／模型|D-MPNN 排序模型預測 retention order index，再用目標方法 anchor Rt 映射；LAD限制係數／可選OLS。|
|6 Rt／Rs／梯度／圖形|排序／Rt 校正，不計算任意梯度機理、峰寬、Rs。|
|7 實驗Rt需求|可結構預測排序 index；可信目標方法 Rt 需已知化合物 anchors，不能稱零實驗方法轉移。|
|8 SMILES未知化合物|支持 SMILES 小分子；未知結構的排序推論需落在訓練適用域。|
|9 Python／React API|Python CLI／核心可封 API；需容器或獨立依賴環境。|
|10 權重／參數／資料|3個 .pt 模型約各3.8 MB，以及映射／測試資料；權重獨立條款未完整確定。|
|11 準確度／外部驗證|存在模型評估流程與 container CI；本次未重現論文或外部資料準確度，不能證明 Rs 或跨模式能力。|
|12 公開網頁可用性|值得做可選少量 anchors 校正；AGPL 與模型／資料個別授權確認後再納入。|

核心來源：[dmpnn.py](https://github.com/boecker-lab/2-step/blob/74c2675e8482f3d588bf8bb4bc47433f9200e68f/dmpnn.py)、[dmpnn_graph.py](https://github.com/boecker-lab/2-step/blob/74c2675e8482f3d588bf8bb4bc47433f9200e68f/dmpnn_graph.py)、[mpnranker2.py](https://github.com/boecker-lab/2-step/blob/74c2675e8482f3d588bf8bb4bc47433f9200e68f/mpnranker2.py)、[predict.py](https://github.com/boecker-lab/2-step/blob/74c2675e8482f3d588bf8bb4bc47433f9200e68f/predict.py)、[mapping.py](https://github.com/boecker-lab/2-step/blob/74c2675e8482f3d588bf8bb4bc47433f9200e68f/mapping.py)、[.github/workflows/test_container.yaml](https://github.com/boecker-lab/2-step/blob/74c2675e8482f3d588bf8bb4bc47433f9200e68f/.github/workflows/test_container.yaml)、[LICENSE](https://github.com/boecker-lab/2-step/blob/74c2675e8482f3d588bf8bb4bc47433f9200e68f/LICENSE)。

Issue／PR抽樣（不代表已解決或所有bug清單）：

- [Windows environment problem, workflows for env-testing ](https://github.com/boecker-lab/2-step/pull/3)：closed；更新 2026-10-12T09:05:34Z；PR。
- [Fix windows install issue](https://github.com/boecker-lab/2-step/pull/2)：closed；更新 2026-10-12T09:05:36Z；PR。
- [Environment fails on windows](https://github.com/boecker-lab/2-step/issues/1)：closed；更新 2026-10-12T09:06:14Z；issue。

### josiehong/TIMPANI

[GitHub](https://github.com/josiehong/TIMPANI) · [固定commit](https://github.com/josiehong/TIMPANI/commit/6db95fa96129b27d7a8fb999f27ff4451553a92d)

`6db95fa96129b27d7a8fb999f27ff4451553a92d`

|評估項目|檢查結果|
|---|---|
|2 維護／Issue／測試|固定HEAD最後提交：2026-07-27T02:53:59Z。open_issues_count=0（包含PR，不是純Issue數）；已取最近0筆all-state issue/PR清單。 tree中測試相關路徑4、workflow路徑0；路徑數不是覆蓋率，無本次量測coverage。|
|1 源碼／授權|完整訓練／特徵編碼原始碼；Apache-2.0。|
|3 語言／依賴／環境|Python≥3.9、PyTorch≥2、RDKit、DGL／圖網路；裝置與套件版本需獨立環境。|
|4 安裝／重現|程式與測試檔分析；無本機訓練／推論重現。|
|5 方程式／模型|Target-informed meta-learning；分子GNN／Graphormer + chromatography encoder；以任務梯度相似度調整訓練權重。|
|6 Rt／Rs／梯度／圖形|條件 Rt regression；沒有機理峰形／Rs／任意梯度最佳化。|
|7 實驗Rt需求|需要來源訓練集及少量目標實測 Rt；目標資料導引是方法核心。|
|8 SMILES未知化合物|結構編碼支持小分子；無權重／完成訓練不能僅輸入SMILES立即推論。|
|9 Python／React API|可以 Python API，但先建立訓練、模型版本與參數資料流程。|
|10 權重／參數／資料|本 snapshot 未見可直接使用 checkpoint；有設定、資料處理、RESULTS文件。|
|11 準確度／外部驗證|tests涵蓋encoder／trainer；未有可量化coverage。cosine任務權重不是prediction interval；RESULTS為上游自報未獨立重現。|
|12 公開網頁可用性|Apache 路線的結構／方法適配候選，第一階段不預設安裝；資料與產出權重授權另確認。|

核心來源：[timp/trainer/timp_trainer.py](https://github.com/josiehong/TIMPANI/blob/6db95fa96129b27d7a8fb999f27ff4451553a92d/timp/trainer/timp_trainer.py)、[timp/models/chrom_encoder.py](https://github.com/josiehong/TIMPANI/blob/6db95fa96129b27d7a8fb999f27ff4451553a92d/timp/models/chrom_encoder.py)、[timp/models/graphormer_rt.py](https://github.com/josiehong/TIMPANI/blob/6db95fa96129b27d7a8fb999f27ff4451553a92d/timp/models/graphormer_rt.py)、[timp/models/gnn.py](https://github.com/josiehong/TIMPANI/blob/6db95fa96129b27d7a8fb999f27ff4451553a92d/timp/models/gnn.py)、[tests/test_chrom_encoder.py](https://github.com/josiehong/TIMPANI/blob/6db95fa96129b27d7a8fb999f27ff4451553a92d/tests/test_chrom_encoder.py)、[tests/test_base_trainer.py](https://github.com/josiehong/TIMPANI/blob/6db95fa96129b27d7a8fb999f27ff4451553a92d/tests/test_base_trainer.py)、[doc/RESULTS.md](https://github.com/josiehong/TIMPANI/blob/6db95fa96129b27d7a8fb999f27ff4451553a92d/doc/RESULTS.md)、[LICENSE](https://github.com/josiehong/TIMPANI/blob/6db95fa96129b27d7a8fb999f27ff4451553a92d/LICENSE)。

### DLUT-datas/MDL-TL

[GitHub](https://github.com/DLUT-datas/MDL-TL) · [固定commit](https://github.com/DLUT-datas/MDL-TL/commit/3ae22dd1966aaf916a17db76cef87fa28d28f0b2)

`3ae22dd1966aaf916a17db76cef87fa28d28f0b2`

|評估項目|檢查結果|
|---|---|
|2 維護／Issue／測試|固定HEAD最後提交：2025-06-13T14:11:07Z。open_issues_count=0（包含PR，不是純Issue數）；已取最近0筆all-state issue/PR清單。 tree中測試相關路徑0、workflow路徑0；路徑數不是覆蓋率，無本次量測coverage。|
|1 源碼／授權|有CPEncoder、模型訓練及資料程式；沒有專案明確LICENSE。|
|3 語言／依賴／環境|Python3.7.10、TensorFlow／Keras舊環境、RDKit／資料處理，移植成本高。|
|4 安裝／重現|只作來源分析；未建立舊環境、未載入h5或重現。|
|5 方程式／模型|分子特徵 + 管柱／流動相／梯度autoencoder，DNN Rt regression與transfer learning。|
|6 Rt／Rs／梯度／圖形|特定方法Rt，不是流動相微分方程；無可靠峰形／Rs。|
|7 實驗Rt需求|基礎訓練與目標fine-tuning需實驗Rt資料；不符合純原理零資料未知化合物預測。|
|8 SMILES未知化合物|可經特徵流程处理结构；未验证可部署的獨立SMILES inference CLI。|
|9 Python／React API|可研究Python包装，但相容性、特徵重現、權重與授權均為阻擋。|
|10 權重／參數／資料|RPLC資料／訓練腳本；small_data/build.py要求base_model.h5，未確證完整權重鏈可重現。|
|11 準確度／外部驗證|資料集與論文連結為上游證據；本次未重新拆分／外部驗證，无置信區間保證。|
|12 公開網頁可用性|只借鑑條件編碼與遷移設計，不直接複製程式／資料／權重。|

核心來源：[CPEncoder/Column Type Encoder/ColumnTypeEncoder.py](https://github.com/DLUT-datas/MDL-TL/blob/3ae22dd1966aaf916a17db76cef87fa28d28f0b2/CPEncoder/Column%20Type%20Encoder/ColumnTypeEncoder.py)、[CPEncoder/Gradient Program Encoder/AutoEncoder.py](https://github.com/DLUT-datas/MDL-TL/blob/3ae22dd1966aaf916a17db76cef87fa28d28f0b2/CPEncoder/Gradient%20Program%20Encoder/AutoEncoder.py)、[train_base_model/build.py](https://github.com/DLUT-datas/MDL-TL/blob/3ae22dd1966aaf916a17db76cef87fa28d28f0b2/train_base_model/build.py)、[train_small_data/build.py](https://github.com/DLUT-datas/MDL-TL/blob/3ae22dd1966aaf916a17db76cef87fa28d28f0b2/train_small_data/build.py)、[data_process/preprocess.py](https://github.com/DLUT-datas/MDL-TL/blob/3ae22dd1966aaf916a17db76cef87fa28d28f0b2/data_process/preprocess.py)。

### statisticalbiotechnology/NonlinearGradientsUI

[GitHub](https://github.com/statisticalbiotechnology/NonlinearGradientsUI) · [固定commit](https://github.com/statisticalbiotechnology/NonlinearGradientsUI/commit/c8dd6681cd7171df751c97d91f26af74c364171b)

`c8dd6681cd7171df751c97d91f26af74c364171b`

|評估項目|檢查結果|
|---|---|
|2 維護／Issue／測試|固定HEAD最後提交：2014-05-16T16:09:31Z。open_issues_count=0（包含PR，不是純Issue數）；已取最近0筆all-state issue/PR清單。 tree中測試相關路徑16、workflow路徑0；路徑數不是覆蓋率，無本次量測coverage。|
|1 源碼／授權|Java核心可見；沒有專案LICENSE；lib/jmzml的Apache不能授權整個專案。|
|3 語言／依賴／環境|Java≥1.7、Swing、jmzML；Elude外部可執行檔與環境設定。|
|4 安裝／重現|只讀Java／範例，未安裝Java／Elude或重現GUI。|
|5 方程式／模型|用線性梯度Rt分布的分位數重排%B，讓洗脫密度更均勻；可使用Elude／實測結果。|
|6 Rt／Rs／梯度／圖形|輸出非線性梯度表與圖；不直接計算分子Rt、物理峰寬或Rs最優解。|
|7 實驗Rt需求|需要Rt列表、線性梯度或Elude預測結果；不是無參數未知分子引擎。|
|8 SMILES未知化合物|不支持任意SMILES；肽類Elude流程不等於小分子結構推論。|
|9 Python／React API|可用子程序或重寫已理解的數學方法，不能未經授權直接移植Java程式。|
|10 權重／參數／資料|範例與方法配置；外部Elude模型／資料授權需獨立審核。|
|11 準確度／外部驗證|舊研究工具；未見自動測試或外部Rs最優保證。手動test說明不等於coverage。|
|12 公開網頁可用性|僅理論參考；無LICENSE阻擋直接fork整合。|

核心來源：[src/nonlineargradientsui/GradientCalculator.java](https://github.com/statisticalbiotechnology/NonlinearGradientsUI/blob/c8dd6681cd7171df751c97d91f26af74c364171b/src/nonlineargradientsui/GradientCalculator.java)、[src/nonlineargradientsui/EludeWorker.java](https://github.com/statisticalbiotechnology/NonlinearGradientsUI/blob/c8dd6681cd7171df751c97d91f26af74c364171b/src/nonlineargradientsui/EludeWorker.java)、[src/nonlineargradientsui/MzOptimizer.java](https://github.com/statisticalbiotechnology/NonlinearGradientsUI/blob/c8dd6681cd7171df751c97d91f26af74c364171b/src/nonlineargradientsui/MzOptimizer.java)。

## 額外候選：同樣區分來源、權限與執行證據

### cadet/CADET-Core

[GitHub](https://github.com/cadet/CADET-Core) · [固定commit](https://github.com/cadet/CADET-Core/commit/b7f689ff7db3bd539188be08a43f7564ea39ff2e)

`b7f689ff7db3bd539188be08a43f7564ea39ff2e`；固定HEAD最後提交：2026-10-12T14:28:15Z。open_issues_count=146（包含PR，不是純Issue數）；已取最近20筆all-state issue/PR清單。 tree中測試相關路徑292、workflow路徑8；路徑數不是覆蓋率，無本次量測coverage。

- **源碼／授權**：LICENSE.txt AGPL-3.0；部分C++標頭／Python classifier GPL-3.0-or-later，存在版本條款衝突待審。
- **環境**：C++／SUNDIALS等數值依賴；Python介面。
- **科學功能**：GRM/LRM/SMA與多種binding，真正運輸／峰形；參數辨識、敏感度。
- **實際執行／驗證**：完整測試、CI；未本機安装或驗證。
- **重用判斷**：最強通用傳輸引擎候選；沒有SMILES→參數；本機可用性與license衝突是採用門檻。

|補充評估項目|檢查結果|
|---|---|
|6 Rt／Rs／梯度|出口曲線可取Rt／寬度／Rs；真正梯度binding，非示意峰|
|7 實驗Rt需求|無實測Rt仍可供binding／transport參數；不知道參數便不能推論|
|8 結構輸入|無SMILES|
|9 Python API|透過cadet-python供Python/React後端；native binary需固定|
|10 模型／參數／資料|binding參數schema、數值測試、參考案例；無分子權重|
|11 外部驗證|上游數值回歸不是結構預測精度；本機未測|

核心來源：[LICENSE.txt](https://github.com/cadet/CADET-Core/blob/b7f689ff7db3bd539188be08a43f7564ea39ff2e/LICENSE.txt)、[pyproject.toml](https://github.com/cadet/CADET-Core/blob/b7f689ff7db3bd539188be08a43f7564ea39ff2e/pyproject.toml)、[src/libcadet/model/binding/StericMassActionBinding.cpp](https://github.com/cadet/CADET-Core/blob/b7f689ff7db3bd539188be08a43f7564ea39ff2e/src/libcadet/model/binding/StericMassActionBinding.cpp)、[src/libcadet/model/GeneralRateModel.cpp](https://github.com/cadet/CADET-Core/blob/b7f689ff7db3bd539188be08a43f7564ea39ff2e/src/libcadet/model/GeneralRateModel.cpp)、[test/GeneralRateModel.cpp](https://github.com/cadet/CADET-Core/blob/b7f689ff7db3bd539188be08a43f7564ea39ff2e/test/GeneralRateModel.cpp)、[test/BindingModels.cpp](https://github.com/cadet/CADET-Core/blob/b7f689ff7db3bd539188be08a43f7564ea39ff2e/test/BindingModels.cpp)。

### cadet/CADET-Process

[GitHub](https://github.com/cadet/CADET-Process) · [固定commit](https://github.com/cadet/CADET-Process/commit/878cf16625632d173f8498f2566c546ae99187c2)

`878cf16625632d173f8498f2566c546ae99187c2`；固定HEAD最後提交：2024-11-13T08:31:26Z。open_issues_count=1（包含PR，不是純Issue數）；已取最近1筆all-state issue/PR清單。 tree中測試相關路徑0、workflow路徑0；路徑數不是覆蓋率，無本次量測coverage。

- **源碼／授權**：此舊repo主要README轉址，不是當前核心。
- **環境**：不適用。
- **科學功能**：指向fau-advanced-separations/CADET-Process。
- **實際執行／驗證**：未执行。
- **重用判斷**：不可把轉址repo的舊commit當作目前Process版本。

|補充評估項目|檢查結果|
|---|---|
|6 Rt／Rs／梯度|非完整source版本|
|7 實驗Rt需求|不適用|
|8 結構輸入|不適用|
|9 Python API|應使用FAU實際repo|
|10 模型／參數／資料|轉址README|
|11 外部驗證|不能沿用此空repo評估實際功能|

核心來源：見固定commit的tree、依賴檔與LICENSE；未列來源不能視為已讀。。

### fau-advanced-separations/CADET-Process

[GitHub](https://github.com/fau-advanced-separations/CADET-Process) · [固定commit](https://github.com/fau-advanced-separations/CADET-Process/commit/a65245e3c0cae8d885a805162fc6ee21201f6eca)

`a65245e3c0cae8d885a805162fc6ee21201f6eca`；固定HEAD最後提交：Fri, 25 Sep 2026 10:10:18 +0200（patch作者日期；非committer日期）。open_issues_count=未取得（包含PR，不是純Issue數）；API限流，沒有完整issue清單。 tree中測試相關路徑70、workflow路徑6；路徑數不是覆蓋率，無本次量測coverage。

- **源碼／授權**：GPL-3.0。
- **環境**：Python≥3.10；cadet-python≥1.0.4、SciPy、hopsy、pymoo等；部分optional最佳化依賴互斥。
- **科學功能**：unit operation、binding、方法事件、CADET adapter、峰分析、參數估計與最佳化。
- **實際執行／驗證**：有大量tests與CI；本機未安装。
- **重用判斷**：最值得作為科學運算架構，非整個React產品；需Core、提供參數。避免相容性／授權未確認時直接依賴。

|補充評估項目|檢查結果|
|---|---|
|6 Rt／Rs／梯度|Core出口曲線與peak comparisons／Rs／梯度事件、process search|
|7 實驗Rt需求|需給定或估計binding與column參數；parameter estimation需實測|
|8 結構輸入|無SMILES到參數|
|9 Python API|原生Python API，React可接自建服務；非原生網站|
|10 模型／參數／資料|process、事件、binding、优化／校正模組与範例|
|11 外部驗證|有單元、integration及coverage workflow；未量測coverage或重現外部資料|

核心來源：[CADETProcess/processModel/binding.py](https://github.com/fau-advanced-separations/CADET-Process/blob/a65245e3c0cae8d885a805162fc6ee21201f6eca/CADETProcess/processModel/binding.py)、[CADETProcess/processModel/unitOperation.py](https://github.com/fau-advanced-separations/CADET-Process/blob/a65245e3c0cae8d885a805162fc6ee21201f6eca/CADETProcess/processModel/unitOperation.py)、[CADETProcess/simulator/cadetAdapter.py](https://github.com/fau-advanced-separations/CADET-Process/blob/a65245e3c0cae8d885a805162fc6ee21201f6eca/CADETProcess/simulator/cadetAdapter.py)、[CADETProcess/comparison/peaks.py](https://github.com/fau-advanced-separations/CADET-Process/blob/a65245e3c0cae8d885a805162fc6ee21201f6eca/CADETProcess/comparison/peaks.py)、[LICENSE.md](https://github.com/fau-advanced-separations/CADET-Process/blob/a65245e3c0cae8d885a805162fc6ee21201f6eca/LICENSE.md)。

### HopkinsLaboratory/Graphormer-RT

[GitHub](https://github.com/HopkinsLaboratory/Graphormer-RT) · [固定commit](https://github.com/HopkinsLaboratory/Graphormer-RT/commit/e258cb149bc47646d9701fd66240cf6f13ae5b32)

`e258cb149bc47646d9701fd66240cf6f13ae5b32`；固定HEAD最後提交：2025-04-29T23:12:27Z。open_issues_count=0（包含PR，不是純Issue數）；已取最近1筆all-state issue/PR清單。 tree中測試相關路徑127、workflow路徑3；路徑數不是覆蓋率，無本次量測coverage。

- **源碼／授權**：根目錄未有LICENSE；部分Graphormer／fairseq MIT標頭不自動涵蓋修改、流程及權重。
- **環境**：PyTorch/fairseq/CUDA版本與本地絕對路徑依賴。
- **科學功能**：分開RP與HILIC graph transformer＋方法／管柱特徵；不是任意模式同模型。
- **實際執行／驗證**：未安裝／未推論；沒有完整專案CI證據。
- **重用判斷**：Zenodo15021743約1.3GB模型，Rights欄未確認明確授權；參考跨模式分開訓練的設計，不直接整合。

|補充評估項目|檢查結果|
|---|---|
|6 Rt／Rs／梯度|Rt regression；梯度僅條件特徵，無PDE峰／Rs|
|7 實驗Rt需求|推論可不用target Rt但需已訓練權重與正確方法特徵；訓練需實驗|
|8 結構輸入|SMILES graph；RP與HILIC專模|
|9 Python API|可包Python但fairseq／CUDA／預處理強耦合；授權阻擋|
|10 模型／參數／資料|Zenodo RP與5個HILIC模型；未下載，license未確認|
|11 外部驗證|有資料拆分／研究論文；未取得全文或重現外部精度|

核心來源：[graphormer/models/graphormer.py](https://github.com/HopkinsLaboratory/Graphormer-RT/blob/e258cb149bc47646d9701fd66240cf6f13ae5b32/graphormer/models/graphormer.py)、[graphormer/models/graphormerHILIC.py](https://github.com/HopkinsLaboratory/Graphormer-RT/blob/e258cb149bc47646d9701fd66240cf6f13ae5b32/graphormer/models/graphormerHILIC.py)、[graphormer/modules/graphormer_layers.py](https://github.com/HopkinsLaboratory/Graphormer-RT/blob/e258cb149bc47646d9701fd66240cf6f13ae5b32/graphormer/modules/graphormer_layers.py)。

### CompOmics/DeepLC

[GitHub](https://github.com/CompOmics/DeepLC) · [固定commit](https://github.com/CompOmics/DeepLC/commit/e24a5822bdb5304fcb1beb9ee5b307e1ab643221)

`e24a5822bdb5304fcb1beb9ee5b307e1ab643221`；固定HEAD最後提交：2026-10-11T09:36:23Z。open_issues_count=1（包含PR，不是純Issue數）；已取最近20筆all-state issue/PR清單。 tree中測試相關路徑17、workflow路徑3；路徑數不是覆蓋率，無本次量測coverage。

- **源碼／授權**：Apache-2.0；權重與資料須另確認。
- **環境**：本snapshot v4.5.0 Python≥3.11、PyTorch≥2.6<3、psm-utils、scikit-learn。
- **科學功能**：肽序列／修飾的原子編碼CNN、reference head選擇、校正／fine-tune。
- **實際執行／驗證**：有模型與測試／工具鏈；未本機執行。
- **重用判斷**：生物分子中特定肽類可選API；不是任意聚合物、小分子與所有蛋白通用LC模型。

|補充評估項目|檢查結果|
|---|---|
|6 Rt／Rs／梯度|肽Rt regression／校正；不做物理梯度峰與Rs|
|7 實驗Rt需求|原生預設reference head可無target Rt；新方法通常需校正|
|8 結構輸入|肽序列及修飾，非任意SMILES／聚合物|
|9 Python API|Python prediction/calibration API；可獨立worker|
|10 模型／參數／資料|package_data模型、reference selection與calibration；權重license另核|
|11 外部驗證|論文及上游流程；本次未重現研究結果|

核心來源：[deeplc/core.py](https://github.com/CompOmics/DeepLC/blob/e24a5822bdb5304fcb1beb9ee5b307e1ab643221/deeplc/core.py)、[deeplc/_architecture.py](https://github.com/CompOmics/DeepLC/blob/e24a5822bdb5304fcb1beb9ee5b307e1ab643221/deeplc/_architecture.py)、[deeplc/calibration/simple.py](https://github.com/CompOmics/DeepLC/blob/e24a5822bdb5304fcb1beb9ee5b307e1ab643221/deeplc/calibration/simple.py)、[deeplc/_reference_selection.py](https://github.com/CompOmics/DeepLC/blob/e24a5822bdb5304fcb1beb9ee5b307e1ab643221/deeplc/_reference_selection.py)、[LICENSE](https://github.com/CompOmics/DeepLC/blob/e24a5822bdb5304fcb1beb9ee5b307e1ab643221/LICENSE)。

### michaelwitting/RepoRT

[GitHub](https://github.com/michaelwitting/RepoRT) · [固定commit](https://github.com/michaelwitting/RepoRT/commit/9de8d603377bbb6cc0f74e250eb7533fd8874df1)

`9de8d603377bbb6cc0f74e250eb7533fd8874df1`；固定HEAD最後提交：2026-07-09T12:17:46Z。open_issues_count=15（包含PR，不是純Issue數）；已取最近20筆all-state issue/PR清單。 tree中測試相關路徑0、workflow路徑7；路徑數不是覆蓋率，無本次量測coverage。

- **源碼／授權**：CC-BY-SA-4.0。
- **環境**：資料標準化／Python前處理。
- **科學功能**：方法metadata＋結構／實測Rt資料集，非模擬器。
- **實際執行／驗證**：檢查tree與流程，未重現訓練。
- **重用判斷**：最有價值的可選實驗資料來源；保留來源、分享相同條款與原資料例外。

|補充評估項目|檢查結果|
|---|---|
|6 Rt／Rs／梯度|實測Rt資料，沒有Rt/峰/Rs求解器|
|7 實驗Rt需求|本身是實驗資料來源|
|8 結構輸入|SMILES／structure identifiers與method metadata|
|9 Python API|資料讀取／前處理可供Python訓練，非推論API|
|10 模型／參數／資料|標準化方法與Rt records；每組來源獨立核查|
|11 外部驗證|資料檢查workflow不是預測模型準確度|

核心來源：[LICENSE](https://github.com/michaelwitting/RepoRT/blob/9de8d603377bbb6cc0f74e250eb7533fd8874df1/LICENSE)、[README.md](https://github.com/michaelwitting/RepoRT/blob/9de8d603377bbb6cc0f74e250eb7533fd8874df1/README.md)。

### yufree/mzrtsim

[GitHub](https://github.com/yufree/mzrtsim) · [固定commit](https://github.com/yufree/mzrtsim/commit/9735e7b692b1ce88b6305420ae0568ea12128e96)

`9735e7b692b1ce88b6305420ae0568ea12128e96`；固定HEAD最後提交：2026-04-10T00:19:36Z。open_issues_count=0（包含PR，不是純Issue數）；已取最近0筆all-state issue/PR清單。 tree中測試相關路徑12、workflow路徑2；路徑數不是覆蓋率，無本次量測coverage。

- **源碼／授權**：DESCRIPTION GPL-2，API未識別不能當作無授權；保守GPL-2-only。
- **環境**：R≥4.3／Bioconductor、SummarizedExperiment、RaMS。
- **科學功能**：指定或隨機Rt、峰與噪音／mzML合成。
- **實際執行／驗證**：有testthat與CI；本次未执行。
- **重用判斷**：適合前端／資料流程測試，不能承擔科學Rt預測；GPL2-only與GPL3組合要特別審核。

|補充評估項目|檢查結果|
|---|---|
|6 Rt／Rs／梯度|指定／隨機Rt合成峰；不預測物理梯度／Rs最佳化|
|7 實驗Rt需求|不需實測但需指定或抽樣Rt，不能當未知分子模型|
|8 結構輸入|無SMILES|
|9 Python API|R子程序或隔離服務；不必為主Python核心|
|10 模型／參數／資料|mzML／LC-MS合成與測試fixture|
|11 外部驗證|testthat及CI驗證資料格式／數值，非LC保留精度|

核心來源：[DESCRIPTION](https://github.com/yufree/mzrtsim/blob/9735e7b692b1ce88b6305420ae0568ea12128e96/DESCRIPTION)、[R/mzmlsim.R](https://github.com/yufree/mzrtsim/blob/9735e7b692b1ce88b6305420ae0568ea12128e96/R/mzmlsim.R)、[R/mzrtsim.R](https://github.com/yufree/mzrtsim/blob/9735e7b692b1ce88b6305420ae0568ea12128e96/R/mzrtsim.R)、[tests/testthat/test-mzml-integrity.R](https://github.com/yufree/mzrtsim/blob/9735e7b692b1ce88b6305420ae0568ea12128e96/tests/testthat/test-mzml-integrity.R)。

### jraysajulga/High-Performance-Liquid-Chromatography-Research-Programs

[GitHub](https://github.com/jraysajulga/High-Performance-Liquid-Chromatography-Research-Programs) · [固定commit](https://github.com/jraysajulga/High-Performance-Liquid-Chromatography-Research-Programs/commit/4165fe30cd067c1545c13142d03562c1d258ab31)

`4165fe30cd067c1545c13142d03562c1d258ab31`；固定HEAD最後提交：2017-10-11T17:20:26Z。open_issues_count=1（包含PR，不是純Issue數）；API限流，沒有完整issue清單。 tree中測試相關路徑0、workflow路徑0；路徑數不是覆蓋率，無本次量測coverage。

- **源碼／授權**：無專案明確授權。
- **環境**：Java/JFreeChart；完整build環境未證實。
- **科學功能**：plate propagation、injection solvent、Neue-Kuss等供參數模擬。
- **實際執行／驗證**：來源分析；未編譯、無量化測試coverage。
- **重用判斷**：理論參考；老舊研究程式不直接移植。

|補充評估項目|檢查結果|
|---|---|
|6 Rt／Rs／梯度|plate propagation與injection solvent峰；完整Rt/Rs pipeline未本機證實|
|7 實驗Rt需求|需要供保留模型參數|
|8 結構輸入|無SMILES模型|
|9 Python API|Java子程序理論上可接API；直接移植無授權|
|10 模型／參數／資料|simulation.java與matrix.java；build資料不足|
|11 外部驗證|未見可靠自動測試／外部验证證據|

核心來源：[simulation.java](https://github.com/jraysajulga/High-Performance-Liquid-Chromatography-Research-Programs/blob/4165fe30cd067c1545c13142d03562c1d258ab31/simulation.java)、[matrix.java](https://github.com/jraysajulga/High-Performance-Liquid-Chromatography-Research-Programs/blob/4165fe30cd067c1545c13142d03562c1d258ab31/matrix.java)。

### Jimbo994/AutoLC-BO

[GitHub](https://github.com/Jimbo994/AutoLC-BO) · [固定commit](https://github.com/Jimbo994/AutoLC-BO/commit/5e6fee42c5d24130bbcfacd58c8c33f578ad9d04)

`5e6fee42c5d24130bbcfacd58c8c33f578ad9d04`；固定HEAD最後提交：Fri, 16 Feb 2024 15:31:23 +0100（patch作者日期；非committer日期）。open_issues_count=未取得（包含PR，不是純Issue數）；API限流，沒有完整issue清單。 tree中測試相關路徑0、workflow路徑0；路徑數不是覆蓋率，無本次量測coverage。

- **源碼／授權**：CC-BY-NC-SA-4.0，含NC，非一般商業開源選項。
- **環境**：Python／Jupyter、GPy/GPyOpt；實驗連接另有Chemstation與Slack設定。
- **科學功能**：LSS分段梯度、峰寬、Rs目標与Bayesian optimization。
- **實際執行／驗證**：未安裝；未執行儀器或通訊程式。
- **重用判斷**：梯度搜尋設計有價值；商用及整合許可受限。程式可用性不能排除NC限制。

|補充評估項目|檢查結果|
|---|---|
|6 Rt／Rs／梯度|真正多段梯度Rt/width/Rs與BO；不是單純色譜繪圖|
|7 實驗Rt需求|需retention params與實驗校正或儀器feedback|
|8 結構輸入|不提供通用SMILES→LSS|
|9 Python API|核心Python可包API；不得連接儀器／Slack作本次測試|
|10 模型／參數／資料|rm_code/bo_code、參數資料與notebooks；無結構預訓練|
|11 外部驗證|有研究示例；未驗證外部精度或部署，不把BO variance當Rt區間|

核心來源：[license.md](https://github.com/Jimbo994/AutoLC-BO/blob/5e6fee42c5d24130bbcfacd58c8c33f578ad9d04/license.md)、[rm_code/retention_model.py](https://github.com/Jimbo994/AutoLC-BO/blob/5e6fee42c5d24130bbcfacd58c8c33f578ad9d04/rm_code/retention_model.py)、[rm_code/peak_width.py](https://github.com/Jimbo994/AutoLC-BO/blob/5e6fee42c5d24130bbcfacd58c8c33f578ad9d04/rm_code/peak_width.py)、[rm_code/crf.py](https://github.com/Jimbo994/AutoLC-BO/blob/5e6fee42c5d24130bbcfacd58c8c33f578ad9d04/rm_code/crf.py)、[bo_code/BO.py](https://github.com/Jimbo994/AutoLC-BO/blob/5e6fee42c5d24130bbcfacd58c8c33f578ad9d04/bo_code/BO.py)。

### Qiong-Yang/GNN-TL

[GitHub](https://github.com/Qiong-Yang/GNN-TL) · [固定commit](https://github.com/Qiong-Yang/GNN-TL/commit/dcbd1fafcca5c5d8d8b4bbbaecdd8842fbce2e40)

`dcbd1fafcca5c5d8d8b4bbbaecdd8842fbce2e40`；固定HEAD最後提交：Sat, 9 Oct 2021 16:55:30 +0800（patch作者日期；非committer日期）。open_issues_count=未取得（包含PR，不是純Issue數）；API限流，沒有完整issue清單。 tree中測試相關路徑0、workflow路徑0；路徑數不是覆蓋率，無本次量測coverage。

- **源碼／授權**：無LICENSE。
- **環境**：舊Python3.6、PyTorch、RDKit。
- **科學功能**：GNN＋MLP，訓練／HILIC transfer learning。
- **實際執行／驗證**：未安裝／訓練；沒有單元／CI證據。
- **重用判斷**：需要來源／目標Rt、模型及授權；只能理論參考。

|補充評估項目|檢查結果|
|---|---|
|6 Rt／Rs／梯度|固定方法Rt regression，沒有任意gradient／peak／Rs|
|7 實驗Rt需求|source／target實驗Rt及訓練權重；transfer需target資料|
|8 結構輸入|分子圖／SMILES小分子|
|9 Python API|Python可改推論API，但舊環境與授權阻擋|
|10 模型／參數／資料|來源訓練／transfer流程與數據拆分；無已核對合法權重鏈|
|11 外部驗證|train/val/test文件不等於單元測試；未重現外部验证|

核心來源：[model/train.py](https://github.com/Qiong-Yang/GNN-TL/blob/dcbd1fafcca5c5d8d8b4bbbaecdd8842fbce2e40/model/train.py)、[model/transferlearning.py](https://github.com/Qiong-Yang/GNN-TL/blob/dcbd1fafcca5c5d8d8b4bbbaecdd8842fbce2e40/model/transferlearning.py)、[model/preprocess.py](https://github.com/Qiong-Yang/GNN-TL/blob/dcbd1fafcca5c5d8d8b4bbbaecdd8842fbce2e40/model/preprocess.py)。

### julianealdag/hplc-retention-prediction

[GitHub](https://github.com/julianealdag/hplc-retention-prediction) · [固定commit](https://github.com/julianealdag/hplc-retention-prediction/commit/c7f5f9e030e22dbb7a619e86e6c2f097b940b13d)

`c7f5f9e030e22dbb7a619e86e6c2f097b940b13d`；固定HEAD最後提交：Mon, 5 Oct 2026 17:58:56 +0200（patch作者日期；非committer日期）。open_issues_count=未取得（包含PR，不是純Issue數）；API限流，沒有完整issue清單。 tree中測試相關路徑4、workflow路徑1；路徑數不是覆蓋率，無本次量測coverage。

- **源碼／授權**：MIT；release joblib／MCMRT資料仍各別核對。
- **環境**：Python/RDKit、scikit-learn；保存模型需匹配版本。
- **科學功能**：RF/Ridge/Lasso QSRR，以已知method_names為條件；group split；descriptor範圍提示。
- **實際執行／驗證**：有tests／CI；未安裝或推論。
- **重用判斷**：最值得探索的寬鬆授權小分子QSRR候選；未知method直接拒絕，不支持任意梯度物理與跨模式。range note不是校準區間。

|補充評估項目|檢查結果|
|---|---|
|6 Rt／Rs／梯度|既有method Rt regression；無物理gradient／peak／Rs|
|7 實驗Rt需求|已訓練模型可無新分子target Rt；不支持未知method直接推論|
|8 結構輸入|SMILES＋RDKit descriptors|
|9 Python API|TrainedModel.predict原生Python，可封API|
|10 模型／參數／資料|release joblib、training pipelines、MCMRT來源；版本／license逐artifact確認|
|11 外部驗證|group holdout評估源碼；descriptor-range／seen pair提示不等於校準置信區間；未重現上游數字|

核心來源：[src/hplc_rt/predictor.py](https://github.com/julianealdag/hplc-retention-prediction/blob/c7f5f9e030e22dbb7a619e86e6c2f097b940b13d/src/hplc_rt/predictor.py)、[src/hplc_rt/features.py](https://github.com/julianealdag/hplc-retention-prediction/blob/c7f5f9e030e22dbb7a619e86e6c2f097b940b13d/src/hplc_rt/features.py)、[src/hplc_rt/models.py](https://github.com/julianealdag/hplc-retention-prediction/blob/c7f5f9e030e22dbb7a619e86e6c2f097b940b13d/src/hplc_rt/models.py)、[src/hplc_rt/splits.py](https://github.com/julianealdag/hplc-retention-prediction/blob/c7f5f9e030e22dbb7a619e86e6c2f097b940b13d/src/hplc_rt/splits.py)、[tests/test_predictor.py](https://github.com/julianealdag/hplc-retention-prediction/blob/c7f5f9e030e22dbb7a619e86e6c2f097b940b13d/tests/test_predictor.py)、[docs/corrections.md](https://github.com/julianealdag/hplc-retention-prediction/blob/c7f5f9e030e22dbb7a619e86e6c2f097b940b13d/docs/corrections.md)、[LICENSE](https://github.com/julianealdag/hplc-retention-prediction/blob/c7f5f9e030e22dbb7a619e86e6c2f097b940b13d/LICENSE)。

## 證據與交付索引

- [功能與實測矩陣](open-source-comparison.md)：三個環境、命令、輸出、未通過／未測項目。
- [科學模型與A–F分類](scientific-model-comparison.md)：方程式、單位、前提與模式邊界。
- [架構與三條路線比較](recommended-architecture.md)：方案A/B/C的9項權衡，不使用無依據精確百分比。
- [第一階段修訂計畫](phase1-revised-plan.md)：可重用、需修正、自行研發與採用門檻。
- [授權審查](license-review.md)：GPL/AGPL、資料／權重、依賴與待法律確認項目。
- [核心閱讀索引](research-evidence/source-review-index.json)：已保存檔案SHA256、符號／行號；error項不是已讀證據。
- `research-evidence/<owner>__<repo>.json`：固定commit、tree、最近issue／PR、依賴檔來源。`extra-*`為限流後補充，日期證據若缺失明示未取得。
- `scripts/research/`：採集、檢查、三個隔離環境、探針、報告生成與審核腳本。上游源碼不納入本平台Repository。

完成調查後停止，待使用者確認組合；此報告不構成正式平台或正式法律意見。
