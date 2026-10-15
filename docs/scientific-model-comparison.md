# 科學模型、方程式與適用條件

日期：2026-10-13。這是固定 commit 原始碼審查與合成參數可行性測試，不是 LC Gradient Studio 的實驗準確度驗證。[來源索引](research-evidence/source-review-index.json) 保存核心檔案 SHA256、符號及行號；commit 與永久連結見 [GitHub 調查](github-research-report.md)。

## RP 的參數與梯度不是同一件事

LSS 通常寫作 `log10 k(φ) = log10 kw − Sφ`，φ 為有機相體積分率。**S／kw 取決於分析物和色譜系統**，不是由模式名稱或 logP 就唯一決定。PyLSS 的 `SSGenerator.rtpred` 實際使用負號，檔頭文字有正號；判斷以可執行碼為準。

PyLSS 定義 `b=t0·(φf−φi)·S/tg`、`k0=10^(logkw−Sφi)`，實作為：

`tR = (t0/b) log10(1+2.3 k0 b) + t0 + td`。

此處 td=Vd/F、t0=Vm/F，管柱幾何估計 Vm=πd²Lε/4，須先對齊體積單位。2.3 是 ln(10) 的近似，不可把自然對數模型的 S 直接代入。`getlssparameters` 用兩個以上實測梯度 Rt 最小化平方殘差擬合 logkw/S。Rt 預測只需這些參數，但**參數未知時此程式沒有 SMILES → 參數模型**。

邊界問題：b≤0 回傳 9999；本次零梯度補測也是 9999，不能視為合法等度 Rt。尚需初始等度、dwell 期間遷移、梯度結束後 hold、非洗脫、分段梯度與負斜率的獨立驗證。公式計算通過並不代表可任意外插。

GRIP 使用自然對數的 `k(φ)=k0 exp(−Sφ)`，神經網路預測 lnS／lnk0，再解分段積分 `∫ exp(Sφ(t))dt = t0·k0`。`RTLayerLSS` 對等度及線性段各有解析積分，考慮可學的 dwell／post-column volume；推論使用累積積分定位洗脫段。這是 LSS 梯度保留近似，不是完整粒子傳輸 PDE，也不是純第一原理：結構至參數仍由實驗資料訓練。程式訓練與 eval 分支不同；超出完整梯度積分時 fallback 會選首段，需另外查核外插。回傳的 q 是段索引，**不是不確定性**。固定 commit 無授權，僅列理論候選。

AutoLC-BO 的 `retention_model.py` 亦用自然對數 LSS，包含多段遷移量、初始等度與結束等度，`compute_chromatogram` 回傳 Rt／峰寬。其 `crf.py` 有真正的解析分離度目標，不只示意圖；但含 NC 授權，不能預設納入公開商業平台。

## 峰寬與分離度

PyLSS `get_lss_peak_width` 採經驗效率 `N=L(cm)·10000/(3.4 dp(μm))`，配合梯度壓縮 G 與 `ke=1/(2.3b)`，計算 `W=4G t0(1+ke)/√N`；可加額外展寬參數。此效率關係不是一般流速／温度／分析物通用的 van Deemter 校正。

`get_lss_gradient_critical_rs` 再把 W 乘 1.7 才套 `Rs=2(tR2−tR1)/(W1+W2)`。前者已有 4σ 型式、後者卻再宣稱轉基線寬，**峰寬定義與倍率需要文獻／標準樣驗證**。本次數值報告保留「上游原生 Rs」，不稱真實分離度。

`plotengine.BuildChromatogram` 用 `A exp(−((t−tR)/C)^2)` 產生 Gaussian 峰；C=√2σ，不是 FWHM 或基線峰寬。測試腳本明確做 W→C 換算。這只能顯示由已知 Rt／寬度合成的峰，不能預測注射溶劑效應、非對稱峰、過載或傳質尾峰。

一般 Gaussian 情況：`Wbase=4σ`、`WFWHM≈2.35482σ`，可用 `Rs≈1.18 ΔtR/(WFWHM1+WFWHM2)`。STLC／OpenIEX 測試的 `apparent_rs_fwhm` 是腳本依離散出口峰推導的近似；非 Gaussian／拖尾情況不應把這個值當精確基線 Rs。強重疊時亦須說明 apex、moment 和峰邊界定義。

## 傳輸與吸附模型

STLC 的 LKM 核心為對流－擴散與固定相動力學：

`∂c/∂t + u∂c/∂z + ((1−ε)/ε)∂q/∂t = Dax∂²c/∂z²`。

`q*i = ai ci / (1+Σ bj cj)`，並以傳質速率接近 q*。`lkm.py` 使用正交配置空間離散，重組稀疏系統逐步求解。其 docstring 稱 improved Euler，但可執行 `solve` 使用 `(Wh−C)` 稀疏分解與增量，呈隐式步進形式；不能僅照註解宣稱二階時間精度。需時間／空間收斂、質量守恆、非負性與剛性測試。

STLC GRM 加入粒內徑向擴散與膜傳質：

`∂cb/∂t = Dax∂²cb/∂z² − u∂cb/∂z − ((1−εc)/εc)(3/Rp)kf(cb−cp|Rp)`，粒內方程再結合孔隙擴散與吸附。GRM 模組可執行碼已存在；本次測的是 LKM，沒有把 GRM 算作通過。提供 inlet profile 不等於有機相梯度會改變 ai／ka／kd；原模組尚需模式專屬的溶劑參數依賴。

CADET-Core 有 GRM／LRM、有限體積與 DG 等離散、吸附／反應模型、Jacobian 與參數敏感度；`test/GeneralRateModel.cpp`、`test/BindingModels.cpp` 與參考解提供數值驗證入口。CADET-Process 的 `binding.py` 暴露 Linear、Langmuir、SMA、GeneralizedIonExchange、mobile-phase modulation 等參數，`cadetAdapter.py` 轉成 solver 設定，**不是從分子結構算出這些參數**。其過程最佳化已有工具，但需自訂方法目標、條件及已校正參數。

標準 SMA 可表為 `dq_i/dt = kA_i c_i qbar0^νi − kD_i q_i c_salt^νi`，`qbar0 = Λ−Σ(νi+σi)qi`（濃度參考尺度依實作）。ν 為特徵交換電荷，σ 為遮蔽，Λ 為容量。CADET 實際 residual 計算見 `StericMassActionBinding.cpp`；rate 常數、參考濃度不能與 OpenIEX 不經換算混用。

OpenIEX 實作 SMA 類交換速率、孔隙可及性 Kd、軸向對流擴散及 SciPy `solve_ivp` BDF。核心不是假峰圖，但可靠性問題包括：`set_equilibrium` 將反向 lnK 設為 `1−lnK`，通常應為 `−lnK`；`from_dict` 重複載入正反向 pair；`run_simulation` 沒保留 `sol.success/status/message`。本次另測序列化及完整回傳終點，沒有修補上游程式。多離子／蛋白的化學計量及守恆仍需查核。

實測forward lnK=−1卻reverse=2（預期1），且to_dict/from_dict往返不一致。這組參數的峰在梯度前就通過，有共同峰頂／Rs=0；修改梯度時間的早期微差須排除取樣格點，不可當作鹽梯度預測成功。柱長變化可改出口峰時，但無法修補模型的平衡條款問題。

## HILIC、NP、SEC 不能套用 RP 假設

PyLSS `ssengine.py` 的文字介紹 Neue–Kuss：`ln k = ln kw + 2 ln(1+aφ) − Sφ/(1+aφ)`，但**文字存在不等於該公式有成熟實作**。另一个 `nlssengine.py` 實際使用不同的非線性函數、舊式絕對匯入，且 `getlssparameters` 把第二個參數也當第三個回傳。這些問題及匯入補測使它不能列為可直接重用的 HILIC 模組。

Graphormer-RT 有 RP 與 HILIC 專屬模型／encoder，結構圖、方法、溶劑與固定相資訊送入 graph transformer 做 Rt 回歸。它屬資料驅動模型，RepoRT 與訓練條件決定適用範圍，不能因標題提 first principles 就認定不需要資料。實際 `graphormer_layers.py` 仍有手動特徵維度及遮除特徵設定，擴充新方法需重新核對 encoder／權重一致性。

GNN-TL 是特定 HILIC 系統的圖網路與 transfer learning；不輸入任意新梯度物理参数。NP 的溶劑競爭吸附及表面水活性，在本次候選中沒有找到可直接使用且經核對的通用結構至參數模組。

理想 SEC 的 `tR=(Vm+KSEC·Vp)/F`，0≤KSEC≤1；對應排阻／全可及的體積邊界。可沿用傳輸引擎，仍需實際孔徑分布、水動力半徑、構形／溶劑影響和非特異吸附。**按分子量排序不是完整 SEC 科學預測**，聚合物需分散性／分布表示。本次没有 SEC 實測驗證。

## 結構、排序與少資料校正

| 工具 | 實際模型 | 是否要目標 Rt／參數 | 不能替代的部分 |
|---|---|---|---|
| 2-step | D-MPNN RankNet 類排序 ROI，第二步非負基底係數 LAD，再可選 OLS | ROI 可由預訓練模型取得；Rt 映射需 anchors，來源碼以 rt>t0 取校正樣 | 沒有梯度積分、峰寬或 Rs；ROI 不等於 LSS 參數 |
| TIMPANI | GNN／Graphormer backbone、head／context adaptation，目標梯度 alignment 加權 meta-learning | 需要目標條件少量 labeled Rt；本 snapshot 無 .pt／.ckpt | 不是零資料物理預測、沒有 PDE 或方法最佳化 |
| MDL-TL | 分子表示 + 管柱／溶劑／梯度 autoencoder 向量，DNN MAE 回歸與 transfer | source 訓練與目標 fine-tuning Rt；`build.py` 載 base_model.h5 | 无 Rt→峰形或物理可外插保證；無授權 |
| hplc-retention-prediction | RDKit descriptors + method features；RF／Ridge／Lasso、group splits | 可用訓練模型推論新分子，但只能選訓練方法；訓練需實驗 Rt | descriptor min/max warning 不是概率區間；不能輸入任意新管柱／梯度 |
| DeepLC | 肽序列／修飾原子特徵 CNN、多條件 head、參考校正 | 原生可無 target Rt 回傳預設訓練條件；實際新系統需校正／head 選擇 | 非通用小分子 SMILES、非物理梯度模擬 |
| NonlinearGradientsUI | 將既有 Rt 分布映射到 %B 分位數，使洗脫密度均勻 | 實測或 Elude 產生的 Rt 分布，後者需肽／模型 | 不計算新方法中每個分子的物理 Rt／Rs |
| mzrtsim | 指定／隨機 Rt、峰寬、噪聲／尾峰與 mzML 組裝 | Rt 必須指定或抽樣，不是從結構與方法算出 | 適合測資料處理器，不適合最佳化保留機理 |

TIMPANI 的 source-task 權重使用梯度 cosine 的 soft mapping `(1+cos)/2`，並以目標訓練折的梯度對齊；它是訓練任務的權重，不能顯示成分子預測信心。2-step LAD 的非負係數與 OLS 保護也不是校準的 prediction interval。

## A–F 能力與重用級別

| 工作 | 已有完整可執行模組 | 修改後可重用 | 只能借鑑／待授權 | 必須自行研發或驗證 |
|---|---|---|---|---|
| A 結構→滯留參數 | 本次沒有已實測且有授權的通用模組 | TIMPANI／MIT QSRR 可做 Rt 基線；DeepLC 做肽 Rt | GRIP 才直接輸出 LSS 參數；無授權 | 按 LC 模式與固定相建立參數預測及域外檢查 |
| B 參數＋梯度→Rt | PyLSS RP headless 已實測 | 多段／等度補強；CADET 的模式化傳輸 | AutoLC-BO 多段解析式（NC） | NP／HILIC 機理與不洗脫邊界驗證 |
| C 峰形／峰寬／Rs | STLC／OpenIEX 出口曲線已執行；PyLSS 有近似峰寬／Rs | 定義統一、solver 失敗检查、儀器展寬校正 | 舊 Java 注射模型（无授權） | 過載／尾峰、detector 響應、模式專屬驗證 |
| D 梯度搜尋 | PyLSS 優化碼存在；CADET-Process 優化框架存在，非本次實測項 | 加方法約束、Rs／耗時／壓力多目標 | AutoLC-BO、分布均勻化 | 跨模式推薦目標與可信度約束 |
| E 管柱／模式轉移 | 無已實測通用模組 | 2-step／TIMPANI／DeepLC 的條件內校正或 transfer | Graphormer-RT RP/HILIC 專模 | 新固定相／模式不能共享同一 S 或吸附參數；需獨立驗證 |
| F 少量實驗修正 | PyLSS fit；2-step LAD／DeepLC calibration 有原生碼 | TIMPANI 訓練流程、CADET 参数估計 | MDL-TL transfer（无授權） | 參數可辨識性、獨立測試與置信區間校準 |

「存在完整原始碼」和「本次執行通過」刻意分開。D／E／F 沒有完整實測時，不推論成成功。

## 準確度與外部驗證界線

STLC 有 [GRM orthogonal collocation 論文](https://doi.org/10.1016/j.compchemeng.2022.108068)，CADET 有 solver 回歸／參考解；這屬數值模型證據，不證明從未知結構估計參數准确。GRIP 有 [預印本](https://www.biorxiv.org/content/10.1101/2024.11.11.622855v1.full)，2-step 有 [研究預印本](https://doi.org/10.26434/chemrxiv-2024-wd5j8-v3)，Graphormer-RT 有 [Analytical Chemistry 論文](https://doi.org/10.1021/acs.analchem.4c05859)，DeepLC 有 [Nature Methods 論文](https://doi.org/10.1038/s41592-021-01301-5)。本次瀏覽這些全文受 403／存取限制，沒有重現其外部測試集，**不抄錄未核實的精確準確率**。

MIT QSRR 專案有 row-wise、compound-held-out、method-held-out 的評估程式，README 明確揭示方法轉移的落差；數字属于上游自報，不能套到本平台。TIMPANI 有 RUNBOOK／RESULTS 與兩類單元測試，部分結果目錄需重新生成。OpenIEX 未找到獨立外部準確度／自動回歸證據。

未來可信度須分解為：參數來源可信度、化學結構／方法 domain、資料校正殘差、求解器收斂、模型失配。需留出新分子、新方法／管柱及條件外測試，按模式報告 MAE／偏差／elution order／coverage；不得只用隨機 row split。沒有校準資料時應顯示「不確定性尚未量化」，不能自行產生精確信心百分比。
