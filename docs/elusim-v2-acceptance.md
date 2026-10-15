# EluSim_V2 最終交付與科學验收
日期：2026-10-14（Asia/Taipei）。公開入口沿用[EluSim](https://elusim-v1.onrender.com/)。**V2增量功能已公開部署；通用SMILES→logKw/S→任意梯度的定量路徑仍未完成，不能聲稱全部V2科學目標完成。**

## A. Repository、commit與PR
[Repository](https://github.com/T22016AEMC/EluSim)、[Draft PR #2](https://github.com/T22016AEMC/EluSim/pull/2)，獨立feature/elusim-v2分支，base release/elusim-v1-stable以呈現增量差異。main未合併。V1保留分支b685d6b1baca45caac8c169859fa0f626f6646d8只有文件比原V1已部署d42594a0c80834080e0d3bdf8cf638f4c8ed6abc更新，程式相同。

最終實際部署[commit b994d4406c1873d2373b19059e63bc5270a42d96](https://github.com/T22016AEMC/EluSim/commit/b994d4406c1873d2373b19059e63bc5270a42d96)。後續验收文件提交不改變此部署來源。服務仍沿用既有feature/elusim-v1部署分支，僅在V2全部Linux檢查通過後以非強推fast-forward更新；V2與V1保留分支都保留。

## B. 真正使用的科學模組及獨立授權
|元件|實際角色／版本|授權|
|---|---|---|
|原EluSim LSS|elusim-lss-migration/1.0.0，SciPy遷移、已知／校正參數、峰形／Rs及最佳化保留|平台AGPL-3.0-or-later|
|RDKit|2026.09.1；真實結構、10描述子、Morgan2/256bits、SMARTS發色團|原BSD通知及runtime license inventory|
|NumPy/SciPy|2.5.4/1.18.1；只使用既有production lockfile|原BSD通知|
|scikit-learn|1.7.2離線訓練Ridge/RF/GradientBoosting；服務端只讀安全JSON，不安裝Torch或sklearn|BSD3，SCIKIT_LEARN_LICENSE.txt|
|report0259-rt|2.0.0，本專案真實RepoRT資料訓練的GB Rt模型，不是假稱上游預訓練模型|資料與衍生權重CC-BY-SA4|
|pnnl-uv-shape|2.0.1，本專案由可追溯UV-adVISor/PNNL數據訓練的RF相對光譜，不是上游MPNN權重|原始數據及衍生權重CC-BY4；PNNL程式BSD2通知獨立保留|
|PyLSS|V1固定AGPL參考d2cda850fa0b0881fc3cf1cd68c4d93b59dac04f；不當作SMILES預測器|AGPL原通知與source保留|

GRIP沒有明確授權不使用；DeepLC肽模型、TIMPANI目標方法微調、2-step Rt轉移、UVVisML λmax及PNNL大型ensemble均閱讀原始碼／授權，但沒有实际安裝／推論者不報為測試通過。詳見[固定commit科學審查](elusim-v2-model-review.md)。原UV資料Figshare15217512.v3明確CCBY4，930/932逐結構及181波長數值核對，2不匹配記錄從最終訓練及公開資料排除，原檔保留本機artifacts/與upstream；不能只靠repository程式BSD推定資料權利。

## C. QSRR真實資料、输入、输出及驗證
RepoRT0259原始324筆，307有效unique結構；197train、70validation、40test。10個固定描述子＋256bitMorgan。scaffold群組切分、canonical重复聚合、不用test選模型。以validation RMSE選GB：test MAE0.375483min、RMSE0.523318min、R²0.941224；RF testRMSE0.532925、Ridge0.938827、meanbaseline2.176494min。Rt pairwise order agreement0.925065，非個人準確百分比。

**输出是特定方法Rt(min)，不是logk、logKw或S。** 匹配原WatersBEHC18 100×2.1mm/1.7µm/40°C、0.4mLmin、水／ACN+0.1%甲酸及原始梯度才可返回；官方DataDescription的甲酸欄位單位為%。pH、dwell与t0未報，明确警示無法驗證；不支持这些参数变化的外推。cross-column/cross-solvent外部泛化没有验证，不产生排名或偽參數。

Applicability：train描述子min/max和Morgan最大Tanimoto，threshold=train leave-one-out近邻10th-percentile，LC0.2963068／UV0.3882893；是启發式域篩選，不是confidence percentage。所有模型保持Experimental model prediction，沒有獨立實驗室驗證／預測區間。

## D. logKw/S可否跨管柱／流動相
**不能。公開版本沒有經驗證的SMILES→logKw/S權重。** Retention Prediction工作區是C型directRt，只能原方法；不會從一筆Rt硬求兩自由參數。A/B可訓練接口、原始k/logk資料標準化、辨識不同φ至少兩點、LSSadapter已建立。adapter输出真的會进入現有遷移與最佳化，但目前接線測試是明示合成fixture，不能算已完成真實結構→LSS驗收。需要有權利的可識別實驗曲線或取得GRIP等符合定義的模型授權後再驗證。

V1手動KnownParameters與ExperimentalCalibration仍可使用；參數scope不匹配時拒絕。pKa/logD微狀態模型未部署，不假裝已準確處理電離。

## E. UV-Vis實際能力
930verified records／930unique，603train、181validation、146test，RF多输出181點。Model2.0.1 testMAE0.120113、RMSE0.181635、R²0.215959（dimensionless normalized shape），meanbaselineRMSE0.207978、Ridge0.245608；窗內最大波長MAE15.575342nm。優於此基準，但形狀泛化有限，未與原大模型實際跑相同基準，不宣稱其性能優於預訓練ensemble。

有效220–400nm／1nm；預設view190–800，範圍外不補峰／補零。λmax是完整模型有效窗內最大值，不保證全域λmax；裁切視窗不另以局部最大冒稱。提供發色團定性、相對光譜、bands、分子圖、波長掃描、多譜比較、PNG/SVG/CSV/JSON與實驗CSV（原始數字與CSV保留，輸入不會重訓／覆蓋模型）。未支持solvent/pH條件化，要求这些條件時不輸出偽條件光譜；沒有molar ε／Beer-Lambert／LC峰高耦合。

## F. 結果分類
- Known/calibrated RP：真正參數化數值Rt；Gaussian峰寬/Rs仍是screening approximation，非實測峰形驗證。
- Structure Rt：exact-method experimental regression，AD／方法失配返回Insufficient data，不能外推任意梯度。
- UV Level1：Qualitative screening。
- UV相對形狀及窗內maximum：Experimental model prediction，不是定量摩爾吸收係數。
- 匯入光譜：Experimental (user supplied, not independently verified)，原檔不變。
- NP/HILIC/IEX/SEC、缺少LSS权重、pKa/logD及溶劑UV變化：Unsupported／Insufficient data。

## G. 真正執行的驗證
|項目|實際結果|
|---|---|
|V1 baseline|20 backend通過|
|最終Backend|本機30通過；[Linux CI38512241269](https://github.com/T22016AEMC/EluSim/actions/runs/38512241269)成功，容器30通過/1非失敗deprecationwarning、7.83s|
|模型訓練／推論|Ridge/RF/GB真实资料验证；所有test输入的JSON vs sklearn parity通過；未見於train結構、domain、方法失配、單Rt不可辨識、LSS接線／手動回退測試|
|Frontend|本機及Linux TypeScript/Vite正式build成功；bundle>500kB非失敗提示|
|Docker|本機沒有Docker，不冒稱本機成功；GitHubLinux實際Dockerbuild及512MiB容器全測／health通過|
|本機browser|最終資料版桌面＋Pixel7尺寸8項通過；截图及JSON保留artifacts/|
|公開V1 smoke|PASS_PUBLIC_API_SMOKE，2026-10-14T06:05:02Z；同一b994revision，真实RDKit、三成分模擬、梯度／流速／柱長敏感性、Rs/trace、最佳化、source|
|公開V2 smoke|PASS_PUBLIC_V2_SMOKE，2026-10-14T06:06:14Z；验证UV2.0.1/CCBY4、181點、domain、方法拒絕、無chromophore不造峰、原始匯入。留出Rt樣本0.8808036088min；UV窗內maximum260nm|
|公開browser|最終版本八項完整桌面／手機尺寸全部通過，2.7min；含真實Rt／UV、匯入匯出、V1計算與最佳化、重新整理、unsupported、JSerror與實際viewport溢出檢查|
|實機手机／行動網路|未執行V2實機測試；V1使用者只確認基本UI，不能沿用成V2科学驗證|

## H. 真正公開部署與資源
Render existing service srv-db6s5n59fdbs73e5oj7g、Singapore free 512MiB、同一[HTTPS入口](https://elusim-v1.onrender.com/)。最終deploy dep-db7hli59fdbs73e9vbvg，2026-10-14T06:02:50Z live；/api/health實測b994revision。前端+Python计算在同一容器，開發電腦不需要開機。

/api/source已下載、解包核對177files、UV2.0.1、930verifiedrecords、独立CCBY license，沒有.venv/node_modules/.env。线上记忆体採样約97–190MB、limit536870900bytes，非压力或併發容量保证。未付費升級；免費閒置可能coldstart，限制造成大型任务会拒絕／逾時。既有限制（1MiB、20成分、40nodes、24候选、2slot/30s、30POSTmin）保留。autoDeploy與deployhook仍未启用，發布由連接器手動trigger；main沒有合併。

## I. 尚未完成及下一步
1. 真正有實驗识别和独立验证的SMILES→logKw/S／logk曲线模型與梯度鏈完整定量功能。
2. 独立实驗室／跨管柱／跨溶劑／跨化合物類型测试、可靠pKa/logD、統計prediction intervals。
3. 更好的UV模型外部benchmark、solvent/pH条件化、190–800完整範圍與absolute ε，不能以现有相對曲線冒稱。
4. 實機手機／行動網路驗證；V3才耦合UV到LC峰高／Beer-Lambert與3D DAD。

本次没有虚构这些功能完成；已有可公开运行的V2增量科学能力、可重现数据管线、测试与合规source交付。
