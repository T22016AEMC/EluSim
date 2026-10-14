# EluSim_V2 模型、資料與授權審查
日期：2026-10-14。這是 V1 的增量升級；V1 核心、校正、最佳化與所有測試保留。

## 實際核對的固定版本
|專案|commit|授權／實際輸出／決策|
|---|---|---|
|[GRIP](https://github.com/gurevichlab/grip)|4247e26580d6ad050125741833dedae8e9ba5370|無 LICENSE，雖有 CPU checkpoint 與條件化梯度 Rt，不複製原始碼／權重；僅閱讀。需作者授權|
|[PyLSS](https://github.com/gmrandazzo/PyLSS)|d2cda850fa0b0881fc3cf1cd68c4d93b59dac04f|AGPL；已有參數梯度參考，不是 SMILES 預測器；保留 V1 固定參考，NLSS 不啟用|
|[DeepLC](https://github.com/compomics/DeepLC)|e24a5822bdb5304fcb1beb9ee5b307e1ab643221|Apache2，肽序列／修飾至 Rt、PyTorch 權重；非一般小分子 logKw/S。未安裝重複框架，模型權重條款仍需逐檔核對後才整合|
|[TIMPANI](https://github.com/josiehong/TIMPANI)|6db95fa96129b27d7a8fb999f27ff4451553a92d|Apache2，目標條件少量資料微調 Rt，無可直接使用通用 LSS 權重。核心依賴 Torch/DGL；不預設對低 RAM CPU 有效|
|[2-step](https://github.com/boecker-lab/2-step)|74c2675e8482f3d588bf8bb4bc47433f9200e68f|AGPL，分子表示與方法轉移需校正，輸出 Rt 不是 logKw/S；公開 models 不等於免校正。未部署其權重|
|[UVVisML](https://github.com/learningmatter-mit/uvvisml)|72b2a3ea391f39b8300cefeafd71cae340634740|MIT 程式，實驗吸收最大波長／TDDFT 電子能量，非完整光譜；Zenodo 與多來源資料權重必須獨立核對。未將 λmax 重建假 Gaussian|
|[PNNL ML_UVvisModels](https://github.com/PNNL-CompBio/ML_UVvisModels)|b61855b53bdae841ac38b820554d8f8e2a412ace|BSD2 根授權，完整光譜資料與權重；部分模型需 QM 特徵／3D、10 模型 ensemble及舊 Torch/CUDA。未整包安裝，重用其實驗資料訓練輕量 RF；不是聲稱重現上游 MPNN|
|[RepoRT](https://github.com/michaelwitting/RepoRT)|9de8d603377bbb6cc0f74e250eb7533fd8874df1|CC-BY-SA4；使用 example0259 的結構、Rt、梯度與metadata，衍生資料／權重同授權。其缺 pH、dwell、t0，故只建 exact-method Rt，不硬擬合 LSS|

原始碼檢查證據見 docs/v2-evidence/：核心推論／訓練流程、依賴、逐檔 Git tree、LICENSE。GRIP 未授權原始碼只本機閱讀，證據只保留檔名/hash與決策。這些候選沒有實際安裝者不報為推論通過。

## 實際科學模型與證據
平台 AGPL3-or-later；既有 SciPy LSS 保持版本 elusim-lss-migration/1.0.0。新模型使用 scikit-learn1.7.2 離線訓練，訓練演算法採 BSD3，不要求服務端安裝 sklearn/Torch。服務端使用既有 NumPy/RDKit 和唯讀壓縮 JSON 決策樹；每個留出輸入已比較 JSON 推論與 sklearn 輸出數值一致。

描述子固定 10項（MW、cLogP、TPSA、HBD/HBA、可旋轉鍵、芳香原子數、形式電荷、環数、重原子）＋Morgan radius2/256bits及SMARTS子結構。没有 pKa/logD 模型，明示只讀形式電荷，不調整電離微狀態。

資料原始檔保留，manifest以固定 URL/commit/SHA256追溯；canonical重复平均标签，只由training data擬合描述子尺度；Murcko scaffold群組分割 seeds41/42，train/validation/test互斥。不用test選模型，不將其當作跨實驗室外部驗證。不同管柱／溶劑未測泛化，直接拒絕轉移。詳細 split SMILES與metrics見 *-validation.json。

RepoRT：307有效unique structures，197train/70validation/40test；以validation RMSE選gradient boosting：test MAE0.375483min、RMSE0.523318min、R²0.941224。RF testRMSE0.532925、Ridge0.938827，meanbaseline2.176494。order pair agreement0.925065是留出配對統計，不是個人信心百分比。只適用Waters BEH C18 100×2.1mm/1.7µm/40°C/0.4mLmin、水/ACN+formic酸與原梯度；來源酸濃度單位、pH、dwell未完整標示，必須再實驗核對。不可推廣到所有C18或改梯度。

UV：932rawrecords、930unique；603train/181validation/146test。RF full-spectrum testMAE0.120152、RMSE0.181653、R²0.215410，meanbaselineRMSE0.207983，Ridge0.245516。Window-maximum MAE15.582192nm，僅在220–400nm窗內，無全域λmax保證。這些是模型aggregate留出評估，不是使用者個別結果的誤差條／預測區間。泛化程度有限，始終Experimental model prediction；沒有外部實驗室驗證。

## UV 能力邊界
Level1：SMARTS芳香環／alkene／carbonyl／nitro／azo／conjugateddiene定性，無匹配不生成強峰，但不宣稱所有farUV吸收為零。
Level2：完整曲線的窗內最大值與bands，沒有獨立經外部驗證的λmax權重。
Level3：多輸出RF直接預測181個實驗相對吸收標籤，不是從λmax生成Gaussian。有效220–400nm/1nm；預設view190–800，範圍外不補零／補峰。單位normalized relative absorption dimensionless，非定量吸光度／ε；不支持solvent/pH調整，有指定條件時回報不足並保留定性。DAD僅獨立光譜比較、不耦合LC峰高。

## logKw/S 接線與缺口
retention_data 正確處理 isocratic k=Rt/t0−1、log10(k)；至少兩個不同φ且同結構／scope才能識別LSS直線，单筆gradientRt明示不可。train_lss_model提供合法实验曲線的可執行訓練入口，需≥40結構、完整scope/source/license。prepared structure adapter的輸出可真正進入V1 migration與optimization；接線測試使用明示合成fixture，不等於已有外部驗證SMILES→LSS模型。
**公開版沒有可用 logKw/S 权重**；没有合規識別資料或適用GRIP權重授權。此路徑未完成定量模型驗收。不同梯度的定量模擬仍用Known Parameters/Experimental Calibration，不拿directRt代換。新增模型錯誤或domain拒絕不会阻斷V1手動路徑。

## 授權部署
保留 LICENSE/NOTICE 與 /api/source；相應原始碼包含訓練script、data原檔、分割、權重和完整獨立授權。RepoRT及derivedLC權重／labels採CC-BY-SA4，獨立於AGPL程式；PNNL資料／derivedUV權重保留BSD2通知。不得把程式授權推定為其他外部權重授權。訓練資料跨來源權利及未來商業／追加資料集仍需逐筆審核，特別GRIP需明確許可。

## 已完成本機驗證
V1基準20項通過；V2全部backend29項通過。TypeScript/Vite正式建置成功；本機桌面＋Pixel7尺寸8項完整流程通過，含V1科學UI、真實留出Rt、方法拒絕、UV光譜、原始實驗匯入、PNG/SVG/CSV/JSON下載。初輪7通過/1手機失敗：UV SVG預設三欄自然寬750px造成頁面擴張；限制img尺寸並用實際viewport寬驗證後全部8通過。沒有用force click掩蓋錯誤。公開／容器驗證另記，不把本機通過當作公開部署成功。
