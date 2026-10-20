"""Generate audit report from fixed GitHub evidence and manually reviewed findings."""
import json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parents[2]; OUT=ROOT/'docs/research-evidence'
# Fields: license; environment; execution; model; output; experimental requirement;
# structure; API; assets; validation; disposition. Maintenance is computed separately.
P={
'gmrandazzo/PyLSS':[
'完整 Python 原始碼；AGPL-3.0-or-later（LICENSE 與檔案標頭）。',
'Python；NumPy、SciPy、Matplotlib、PyYAML；GUI 另有 PyQt6。隔離測試採 Python 3.12.14，省略 GUI。',
'本機 editable 安裝及 headless probe 成功；上游 pytest 6 項通過。NLSS 匯入失敗，不能宣稱全套成功。',
'LSS：log10(k)=logKw−Sφ；解析梯度 Rt；simplex 擬合參數與梯度搜尋。',
'真正由參數計算 Rt、峰寬、Rs；Gaussian 圖形是理想化重建。零梯度回傳 9999；寬度／Rs 定義需校驗。',
'已有 logKw/S 可直接運作；從未知樣本估計參數需多個實驗梯度 Rt。',
'沒有 SMILES／名稱推斷 logKw/S；未知結構零資料無法可靠預測。',
'原生 Python 可呼叫，適合薄 API 包裝； GUI 與數值計算分離。',
'無結構預訓練權重；範例、測試、管柱／LSS 参数可重用；參數不能跨模式自動移植。',
'測試證明執行與參數敏感性，不是外部 Rt 準確度；六個單元測試不能代表實驗驗證。',
'優先整合 RP 科學核心。AGPL 網路互動相應原始碼義務須履行；NLSS、欄轉移及 Rs 須另驗證。'],
'gurevichlab/grip':[
'核心與 checkpoint 可見；固定版本未找到專案 LICENSE，不能當作可直接重用開源。',
'Python ≥3.10（環境檔較新）；PyTorch、Lightning、Chemprop 2.0.4、RDKit、NumPy<2。pyproject dependencies 空，環境檔才有完整依賴。',
'原始碼／資產檢查；未安裝或下載 checkpoint，未重現推論。',
'圖神經網路預測 ln(k0)、ln(S)，以梯度积分条件求 Rt；結構與方法特徵共同輸入。',
'計算梯度 Rt；沒有完整傳輸峰形、峰寬／Rs 引擎；查找分段梯度與未洗脫處理需審查。',
'預訓練模型推論不要求該未知化合物實測 Rt，但訓練依賴歷史實驗與方法描述，並非純物理零資料模型。',
'程式接受結構資訊／SMILES，需模型與方法特徵；本次未實測。',
'可包 Python 推論 API，但環境重、wheel 子套件打包須驗證，且授權先阻擋。',
'model/model-i6kwrq9u.ckpt 約12.4 MB 存在；未獨立确认權重與訓練資料授權。',
'有研究／資料拆分程式；未重現外部驗證，不能轉述準確度為本平台效能；輸出的 q 是梯度段索引，不是可信度。',
'科學設計很值得借鑑；先向作者取得程式、權重、資料明確授權，未取得前排除直接整合。'],
'sartorius-research/STLC':[
'完整 Python 原始碼；GPL-3.0。',
'Python、NumPy、SciPy、Matplotlib；正交配置（collocation）空間離散。',
'本機安装与3成分傳輸測試成功；長度與步長變化已測；無原生溶劑梯度映射可測。',
'Lumped Kinetic Model／General Rate Model；對流、軸向擴散、吸附動力學及顆粒傳輸。',
'解濃度波形並取峰頂 Rt；FWHM 與 Rs 是本次外加分析。是真實傳輸方程，非單純示意圖。',
'給定吸附／動力學／傳輸參數可無實測 Rt 執行；參數辨識仍需資料或可信來源。',
'沒有 SMILES；無法从結構自動取得 a、b、k、D。',
'Python 可直接 import；適合作為數值對照與教學後端，API 單位規範需補。',
'範例與數值實作，沒有分子預訓練模型／通用固定相資料庫。',
'本測試三條有限波形有微小負濃度；dt減半峰寬改變，尚未達網格收斂。源碼文件時間積分描述與實作需核對。',
'可作峰形對照。GPL 分發／衍生程式義務見授權文件；不建議承擔整個多模式架構。'],
'jonkeeley/openiex':[
'完整 Python 包與範例；MIT。',
'Python、NumPy、SciPy、Matplotlib、pandas、tqdm；notebook進度條本測試另需ipywidgets。',
'隔離安裝初次300秒超時，重試成功；三個案例完成，狀態EXECUTED_REVIEW_REQUIRED。序列化不一致，梯度敏感性未證實。',
'IEX：鹽／蛋白質的運輸、位點佔用與多價離子交換動力學；BDF solve_ivp。',
'多蛋白鹽梯度濃度曲線可求峰頂／寬度；本次外加 FWHM-Rs，不可當作原生 Rs API。',
'不強制實測 Rt，但需 lnK、價數、容量、擴散等蛋白／固定相參數。',
'沒有任意 SMILES／蛋白序列到吸附參數模型。',
'原生 Python；可包 API，但 solver 失敗狀態應保留。',
'物種、柱、方法物件及教學範例；沒有經驗證通用蛋白參數庫／權重。',
'set_equilibrium 的 reverse lnK 寫成1−lnK；to_dict/from_dict往返需審查。solve_ivp成功／錯誤訊息未暴露。無外部准确度重現。',
'MIT 元件有價值，適合後續修正與驗證的 IEX 備選；不能直接當作可靠蛋白設計引擎。'],
'boecker-lab/2-step':[
'完整核心、容器與模型；AGPL-3.0。',
'Python3.12、Chemprop1.6.1、PyTorch、RDKit、PuLP、statsmodels、NumPy<2；與 GRIP/TIMPANI 環境不宜混裝。',
'檢查原始碼、CI與權重清單；本次未安装／推論，不宣稱容器測試通過。',
'D-MPNN 排序模型預測 retention order index，再用目標方法 anchor Rt 映射；LAD限制係數／可選OLS。',
'排序／Rt 校正，不計算任意梯度機理、峰寬、Rs。',
'可結構預測排序 index；可信目標方法 Rt 需已知化合物 anchors，不能稱零實驗方法轉移。',
'支持 SMILES 小分子；未知結構的排序推論需落在訓練適用域。',
'Python CLI／核心可封 API；需容器或獨立依賴環境。',
'3個 .pt 模型約各3.8 MB，以及映射／測試資料；權重獨立條款未完整確定。',
'存在模型評估流程與 container CI；本次未重現論文或外部資料準確度，不能證明 Rs 或跨模式能力。',
'值得做可選少量 anchors 校正；AGPL 與模型／資料個別授權確認後再納入。'],
'josiehong/TIMPANI':[
'完整訓練／特徵編碼原始碼；Apache-2.0。',
'Python≥3.9、PyTorch≥2、RDKit、DGL／圖網路；裝置與套件版本需獨立環境。',
'程式與測試檔分析；無本機訓練／推論重現。',
'Target-informed meta-learning；分子GNN／Graphormer + chromatography encoder；以任務梯度相似度調整訓練權重。',
'條件 Rt regression；沒有機理峰形／Rs／任意梯度最佳化。',
'需要來源訓練集及少量目標實測 Rt；目標資料導引是方法核心。',
'結構編碼支持小分子；無權重／完成訓練不能僅輸入SMILES立即推論。',
'可以 Python API，但先建立訓練、模型版本與參數資料流程。',
'本 snapshot 未見可直接使用 checkpoint；有設定、資料處理、RESULTS文件。',
'tests涵蓋encoder／trainer；未有可量化coverage。cosine任務權重不是prediction interval；RESULTS為上游自報未獨立重現。',
'Apache 路線的結構／方法適配候選，第一階段不預設安裝；資料與產出權重授權另確認。'],
'DLUT-datas/MDL-TL':[
'有CPEncoder、模型訓練及資料程式；沒有專案明確LICENSE。',
'Python3.7.10、TensorFlow／Keras舊環境、RDKit／資料處理，移植成本高。',
'只作來源分析；未建立舊環境、未載入h5或重現。',
'分子特徵 + 管柱／流動相／梯度autoencoder，DNN Rt regression與transfer learning。',
'特定方法Rt，不是流動相微分方程；無可靠峰形／Rs。',
'基礎訓練與目標fine-tuning需實驗Rt資料；不符合純原理零資料未知化合物預測。',
'可經特徵流程处理结构；未验证可部署的獨立SMILES inference CLI。',
'可研究Python包装，但相容性、特徵重現、權重與授權均為阻擋。',
'RPLC資料／訓練腳本；small_data/build.py要求base_model.h5，未確證完整權重鏈可重現。',
'資料集與論文連結為上游證據；本次未重新拆分／外部驗證，无置信區間保證。',
'只借鑑條件編碼與遷移設計，不直接複製程式／資料／權重。'],
'statisticalbiotechnology/NonlinearGradientsUI':[
'Java核心可見；沒有專案LICENSE；lib/jmzml的Apache不能授權整個專案。',
'Java≥1.7、Swing、jmzML；Elude外部可執行檔與環境設定。',
'只讀Java／範例，未安裝Java／Elude或重現GUI。',
'用線性梯度Rt分布的分位數重排%B，讓洗脫密度更均勻；可使用Elude／實測結果。',
'輸出非線性梯度表與圖；不直接計算分子Rt、物理峰寬或Rs最優解。',
'需要Rt列表、線性梯度或Elude預測結果；不是無參數未知分子引擎。',
'不支持任意SMILES；肽類Elude流程不等於小分子結構推論。',
'可用子程序或重寫已理解的數學方法，不能未經授權直接移植Java程式。',
'範例與方法配置；外部Elude模型／資料授權需獨立審核。',
'舊研究工具；未見自動測試或外部Rs最優保證。手動test說明不等於coverage。',
'僅理論參考；無LICENSE阻擋直接fork整合。'],
}
EXTRA={
'cadet/CADET-Core':('LICENSE.txt AGPL-3.0；部分C++標頭／Python classifier GPL-3.0-or-later，存在版本條款衝突待審','C++／SUNDIALS等數值依賴；Python介面','GRM/LRM/SMA與多種binding，真正運輸／峰形；參數辨識、敏感度','完整測試、CI；未本機安装或驗證','最強通用傳輸引擎候選；沒有SMILES→參數；本機可用性與license衝突是採用門檻'),
'cadet/CADET-Process':('此舊repo主要README轉址，不是當前核心','不適用','指向fau-advanced-separations/CADET-Process','未执行','不可把轉址repo的舊commit當作目前Process版本'),
'fau-advanced-separations/CADET-Process':('GPL-3.0','Python≥3.10；cadet-python≥1.0.4、SciPy、hopsy、pymoo等；部分optional最佳化依賴互斥','unit operation、binding、方法事件、CADET adapter、峰分析、參數估計與最佳化','有大量tests與CI；本機未安装','最值得作為科學運算架構，非整個React產品；需Core、提供參數。避免相容性／授權未確認時直接依賴'),
'HopkinsLaboratory/Graphormer-RT':('根目錄未有LICENSE；部分Graphormer／fairseq MIT標頭不自動涵蓋修改、流程及權重','PyTorch/fairseq/CUDA版本與本地絕對路徑依賴','分開RP與HILIC graph transformer＋方法／管柱特徵；不是任意模式同模型','未安裝／未推論；沒有完整專案CI證據','Zenodo15021743約1.3GB模型，Rights欄未確認明確授權；參考跨模式分開訓練的設計，不直接整合'),
'CompOmics/DeepLC':('Apache-2.0；權重與資料須另確認','本snapshot v4.5.0 Python≥3.11、PyTorch≥2.6<3、psm-utils、scikit-learn','肽序列／修飾的原子編碼CNN、reference head選擇、校正／fine-tune','有模型與測試／工具鏈；未本機執行','生物分子中特定肽類可選API；不是任意聚合物、小分子與所有蛋白通用LC模型'),
'michaelwitting/RepoRT':('CC-BY-SA-4.0','資料標準化／Python前處理','方法metadata＋結構／實測Rt資料集，非模擬器','檢查tree與流程，未重現訓練','最有價值的可選實驗資料來源；保留來源、分享相同條款與原資料例外'),
'yufree/mzrtsim':('DESCRIPTION GPL-2，API未識別不能當作無授權；保守GPL-2-only','R≥4.3／Bioconductor、SummarizedExperiment、RaMS','指定或隨機Rt、峰與噪音／mzML合成','有testthat與CI；本次未执行','適合前端／資料流程測試，不能承擔科學Rt預測；GPL2-only與GPL3組合要特別審核'),
'jraysajulga/High-Performance-Liquid-Chromatography-Research-Programs':('無專案明確授權','Java/JFreeChart；完整build環境未證實','plate propagation、injection solvent、Neue-Kuss等供參數模擬','來源分析；未編譯、無量化測試coverage','理論參考；老舊研究程式不直接移植'),
'Jimbo994/AutoLC-BO':('CC-BY-NC-SA-4.0，含NC，非一般商業開源選項','Python／Jupyter、GPy/GPyOpt；實驗連接另有Chemstation與Slack設定','LSS分段梯度、峰寬、Rs目標与Bayesian optimization','未安裝；未執行儀器或通訊程式','梯度搜尋設計有價值；商用及整合許可受限。程式可用性不能排除NC限制'),
'Qiong-Yang/GNN-TL':('無LICENSE','舊Python3.6、PyTorch、RDKit','GNN＋MLP，訓練／HILIC transfer learning','未安裝／訓練；沒有單元／CI證據','需要來源／目標Rt、模型及授權；只能理論參考'),
'julianealdag/hplc-retention-prediction':('MIT；release joblib／MCMRT資料仍各別核對','Python/RDKit、scikit-learn；保存模型需匹配版本','RF/Ridge/Lasso QSRR，以已知method_names為條件；group split；descriptor範圍提示','有tests／CI；未安裝或推論','最值得探索的寬鬆授權小分子QSRR候選；未知method直接拒絕，不支持任意梯度物理與跨模式。range note不是校準區間'),
}
# Additional dimensions for every supplemental scientific project.
# fields: output, empirical input, structures, API, reusable assets, validation.
DETAIL={
'cadet/CADET-Core':('出口曲線可取Rt／寬度／Rs；真正梯度binding，非示意峰','無實測Rt仍可供binding／transport參數；不知道參數便不能推論','無SMILES','透過cadet-python供Python/React後端；native binary需固定','binding參數schema、數值測試、參考案例；無分子權重','上游數值回歸不是結構預測精度；本機未測'),
'cadet/CADET-Process':('非完整source版本','不適用','不適用','應使用FAU實際repo','轉址README','不能沿用此空repo評估實際功能'),
'fau-advanced-separations/CADET-Process':('Core出口曲線與peak comparisons／Rs／梯度事件、process search','需給定或估計binding與column參數；parameter estimation需實測','無SMILES到參數','原生Python API，React可接自建服務；非原生網站','process、事件、binding、优化／校正模組与範例','有單元、integration及coverage workflow；未量測coverage或重現外部資料'),
'HopkinsLaboratory/Graphormer-RT':('Rt regression；梯度僅條件特徵，無PDE峰／Rs','推論可不用target Rt但需已訓練權重與正確方法特徵；訓練需實驗','SMILES graph；RP與HILIC專模','可包Python但fairseq／CUDA／預處理強耦合；授權阻擋','Zenodo RP與5個HILIC模型；未下載，license未確認','有資料拆分／研究論文；未取得全文或重現外部精度'),
'CompOmics/DeepLC':('肽Rt regression／校正；不做物理梯度峰與Rs','原生預設reference head可無target Rt；新方法通常需校正','肽序列及修飾，非任意SMILES／聚合物','Python prediction/calibration API；可獨立worker','package_data模型、reference selection與calibration；權重license另核','論文及上游流程；本次未重現研究結果'),
'michaelwitting/RepoRT':('實測Rt資料，沒有Rt/峰/Rs求解器','本身是實驗資料來源','SMILES／structure identifiers與method metadata','資料讀取／前處理可供Python訓練，非推論API','標準化方法與Rt records；每組來源獨立核查','資料檢查workflow不是預測模型準確度'),
'yufree/mzrtsim':('指定／隨機Rt合成峰；不預測物理梯度／Rs最佳化','不需實測但需指定或抽樣Rt，不能當未知分子模型','無SMILES','R子程序或隔離服務；不必為主Python核心','mzML／LC-MS合成與測試fixture','testthat及CI驗證資料格式／數值，非LC保留精度'),
'jraysajulga/High-Performance-Liquid-Chromatography-Research-Programs':('plate propagation與injection solvent峰；完整Rt/Rs pipeline未本機證實','需要供保留模型參數','無SMILES模型','Java子程序理論上可接API；直接移植無授權','simulation.java與matrix.java；build資料不足','未見可靠自動測試／外部验证證據'),
'Jimbo994/AutoLC-BO':('真正多段梯度Rt/width/Rs與BO；不是單純色譜繪圖','需retention params與實驗校正或儀器feedback','不提供通用SMILES→LSS','核心Python可包API；不得連接儀器／Slack作本次測試','rm_code/bo_code、參數資料與notebooks；無結構預訓練','有研究示例；未驗證外部精度或部署，不把BO variance當Rt區間'),
'Qiong-Yang/GNN-TL':('固定方法Rt regression，沒有任意gradient／peak／Rs','source／target實驗Rt及訓練權重；transfer需target資料','分子圖／SMILES小分子','Python可改推論API，但舊環境與授權阻擋','來源訓練／transfer流程與數據拆分；無已核對合法權重鏈','train/val/test文件不等於單元測試；未重現外部验证'),
'julianealdag/hplc-retention-prediction':('既有method Rt regression；無物理gradient／peak／Rs','已訓練模型可無新分子target Rt；不支持未知method直接推論','SMILES＋RDKit descriptors','TrainedModel.predict原生Python，可封API','release joblib、training pipelines、MCMRT來源；版本／license逐artifact確認','group holdout評估源碼；descriptor-range／seen pair提示不等於校準置信區間；未重現上游數字'),
}
def evidence(repo):
 slug=repo.replace('/','__'); ps=[OUT/(slug+'.json'),OUT/('extra-'+slug+'.json')]
 ds=[json.loads(p.read_text(encoding='utf8')) for p in ps if p.exists()]
 d=next((x for x in ds if x.get('commit')),ds[-1]); extra=next((x for x in ds if x.get('sha')), {})
 sha=d.get('commit',{}).get('sha') or extra.get('sha') or '未取得'
 date=d.get('commit',{}).get('commit',{}).get('committer',{}).get('date')
 if not date:
  m=re.search(r'^Date: (.+)$',extra.get('commit_patch_header',''),re.M); date=(m.group(1)+'（patch作者日期；非committer日期）') if m else '未取得，不用repo更新日替代'
 return d,sha,date
idx=json.loads((OUT/'source-review-index.json').read_text(encoding='utf8'))
def source_links(repo,sha):
 rows=[r for r in idx.get(repo.replace('/','__'),[]) if not r.get('error')]
 license_path=OUT/'license-file-evidence.json'
 if license_path.exists():
  for entry in json.loads(license_path.read_text(encoding='utf8')):
   if entry['repository_snapshot']==repo.replace('/','__'):
    seen={r['path'] for r in rows}
    rows.extend({'path':p['path']} for p in entry['root_license_files'] if p['path'] not in seen)
 return '、'.join('['+r['path']+'](https://github.com/'+repo+'/blob/'+sha+'/'+r['path'].replace(' ','%20')+')' for r in rows) or '見固定commit的tree、依賴檔與LICENSE；未列來源不能視為已讀。'
def maintenance(d,date):
 m=d.get('metadata',{}); trees=d.get('tree',{}).get('tree',[])
 paths=[x['path'] for x in trees] or d.get('paths',[])
 tests=[p for p in paths if '/test' in p.lower() or p.lower().startswith('test')]
 ci=[p for p in paths if '.github' in p and 'workflow' in p]
 count=m.get('open_issues_count','未取得'); issues=d.get('issues')
 return f'固定HEAD最後提交：{date}。open_issues_count={count}（包含PR，不是純Issue數）；'+(f'已取最近{len(issues)}筆all-state issue/PR清單。' if isinstance(issues,list) else 'API限流，沒有完整issue清單。')+f' tree中測試相關路徑{len(tests)}、workflow路徑{len(ci)}；路徑數不是覆蓋率，無本次量測coverage。'
text='''# GitHub 開源專案調查報告

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

'''
labels=['1 源碼／授權','3 語言／依賴／環境','4 安裝／重現','5 方程式／模型','6 Rt／Rs／梯度／圖形','7 實驗Rt需求','8 SMILES未知化合物','9 Python／React API','10 權重／參數／資料','11 準確度／外部驗證','12 公開網頁可用性']
for repo,v in P.items():
 d,sha,date=evidence(repo); text+=f'### {repo}\n\n[GitHub](https://github.com/{repo}) · [固定commit](https://github.com/{repo}/commit/{sha})\n\n`{sha}`\n\n|評估項目|檢查結果|\n|---|---|\n'
 text+=f'|2 維護／Issue／測試|{maintenance(d,date)}|\n'
 for label,val in zip(labels,v):text+=f'|{label}|{val}|\n'
 text+='\n核心來源：'+source_links(repo,sha)+'。\n\n'
 issues=d.get('issues',[])
 if issues:
  text+='Issue／PR抽樣（不代表已解決或所有bug清單）：\n\n'
  for issue in issues[:5]:
   text+='- ['+issue['title'].replace('\n',' ').replace('[','(').replace(']',')')+']('+issue['html_url']+')：'+issue.get('state','未知')+'；更新 '+issue.get('updated_at','未取得')+'；'+('PR' if 'pull_request' in issue else 'issue')+'。\n'
  text+='\n'
text+='## 額外候選：同樣區分來源、權限與執行證據\n\n'
for repo,v in EXTRA.items():
 d,sha,date=evidence(repo); text+=f'### {repo}\n\n[GitHub](https://github.com/{repo}) · [固定commit](https://github.com/{repo}/commit/{sha})\n\n`{sha}`；{maintenance(d,date)}\n\n'
 for l,val in zip(['源碼／授權','環境','科學功能','實際執行／驗證','重用判斷'],v):text+=f'- **{l}**：{val}。\n'
 text+='\n|補充評估項目|檢查結果|\n|---|---|\n'
 for label,val in zip(['6 Rt／Rs／梯度','7 實驗Rt需求','8 結構輸入','9 Python API','10 模型／參數／資料','11 外部驗證'],DETAIL[repo]):text+='|'+label+'|'+val+'|\n'
 text+='\n核心來源：'+source_links(repo,sha)+'。\n\n'
text+='''## 證據與交付索引

- [功能與實測矩陣](open-source-comparison.md)：三個環境、命令、輸出、未通過／未測項目。
- [科學模型與A–F分類](scientific-model-comparison.md)：方程式、單位、前提與模式邊界。
- [架構與三條路線比較](recommended-architecture.md)：方案A/B/C的9項權衡，不使用無依據精確百分比。
- [第一階段修訂計畫](phase1-revised-plan.md)：可重用、需修正、自行研發與採用門檻。
- [授權審查](license-review.md)：GPL/AGPL、資料／權重、依賴與待法律確認項目。
- [核心閱讀索引](research-evidence/source-review-index.json)：已保存檔案SHA256、符號／行號；error項不是已讀證據。
- `research-evidence/<owner>__<repo>.json`：固定commit、tree、最近issue／PR、依賴檔來源。`extra-*`為限流後補充，日期證據若缺失明示未取得。
- `scripts/research/`：採集、檢查、三個隔離環境、探針、報告生成與審核腳本。上游源碼不納入本平台Repository。

完成調查後停止，待使用者確認組合；此報告不構成正式平台或正式法律意見。
'''
(ROOT/'docs/github-research-report.md').write_text(text,encoding='utf8')
print('report generated',len(text))
