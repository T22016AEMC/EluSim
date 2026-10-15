# 開源、權重與公開部署授權審查

日期：2026-10-13。這是固定版本的工程授權初審，未取代法律意見。判斷依據是 LICENSE、檔頭、套件宣告與權重來源；GitHub 公開、星數或 README 的「freely available」不是完整重用授權。

## 項目與重用決策

| 專案 | 審查發現 | 公開服務決策 |
|---|---|---|
| PyLSS | LICENSE、核心檔头是 AGPL v3 or later，pyproject 簡寫 AGPL | 可有條件整合；衍生／結合範圍、網路互動的 source offer 與完整來源須落實 |
| GRIP | 固定 tree 無 LICENSE，pyproject 無 license，checkpoint 也無獨立授權 | **不可直接重用碼或權重**；作者明確授權後重新審查 |
| STLC | LICENSE GPL-3.0，Python 檔頭 GPL v3；需按檔案確認 only／later | 可有條件使用；分發結合程式／容器時公開相應來源，GPL 本身沒有 AGPL 的網路觸發條款 |
| OpenIEX | LICENSE MIT | 保留著作權及授權文本；允許修改／服務，但科學問題仍待修復 |
| 2-step | LICENSE AGPL-3.0，models/*.pt 在同 repo，未見獨立權重條款 | 程式可有條件整合；权重是否明確受同授權、來源資料及第三方參數仍要確認 |
| TIMPANI | 根 LICENSE Apache-2.0，無隨 repo 預訓練 .pt／.ckpt | 程式可重用，保留 License／NOTICE（如有）和修改標記；資料／未來權重分開審查 |
| MDL-TL | 固定 tree 無根授權，只有模型／依賴程式 | **不可直接重用**；程式、模型與 14 組資料都須另確認 |
| NonlinearGradientsUI | 無自有根 LICENSE；lib/jmzml 有 Apache 檔 | **不可直接重用自有碼**；相依庫授權不會授權整個專案 |
| CADET-Core | 根 LICENSE.txt 是 AGPL-3.0；pyproject classifiers 與多個核心 C++ 檔頭仍 GPL v3 or later | **授權衝突待釐清**；先按 AGPL 嚴格預估，正式整合前確認選定 release／檔案鏈，不擅自判定純 GPL |
| CADET-Process（FAU 實際 repo） | LICENSE.md GPL-3.0，pyproject GPLv3；cadet 組織的同名 repo 只是轉址 | 可有條件使用；Core 的不一致不能被 Process 的 GPL 宣告消除 |
| Graphormer-RT | 根無 LICENSE；部分 Graphormer 檔頭 MIT、fairseq 子樹有 MIT 授權 | 不把局部檔頭推廣到作者修改、預處理及完整工作流；**整體直接重用暫不批准** |
| Graphormer-RT 權重 | [Zenodo record](https://zenodo.org/records/15021743) 有公開下載，瀏覽結果 Rights/License 欄沒有可識別授權 | 獨立授權仍未確認，不能以程式碼 MIT 推論權重自由重用 |
| DeepLC | 根 LICENSE Apache-2.0，CNN／校正碼與模型 package_data 有來源 | 程式可重用；挑選權重版本時確認 artifact 授權與訓練資料權利，不將程式授權自動視為所有外部權重條款 |
| RepoRT | 根 LICENSE CC-BY-SA-4.0 | 可用並署名；改編／再發布資料需相同或相容授權，個別資料來源及模型衍生問題須再審 |
| mzrtsim | GitHub API license=null，但 DESCRIPTION 明確 `GPL-2` | 不是無授權；按 GPL-2.0-only 的保守理解查核。不得直接與 GPLv3／AGPLv3 形成不相容結合作品 |
| 舊 Java HPLC simulator | 無明確專案授權；依賴 JFreeChart 不等於授權自有碼 | **不可直接重用**；只能借鑑公開科學論文中的算法 |
| AutoLC-BO | license.md 是 CC-BY-NC-SA-4.0 | 有 NC，並非符合任意用途的開源授權；預設排除公開商業服務與 AGPL 結合。商業許可另議 |
| GNN-TL | 無根 LICENSE | **不可直接重用碼／權重**；不因論文與測試資料公開而授權 |
| hplc-retention-prediction | 根 LICENSE MIT，套件亦 MIT；資料聲稱 CC0 | 程式可重用；資料與 release joblib 權重須逐 artifact 核對，README 聲稱不是供應鏈清單 |

固定 commit、原檔永久連結與 LICENSE 路徑見 [調查報告](github-research-report.md)，JSON 證據包含 tree，因此「未找到」限於本次固定快照，而不是斷言作者永遠沒有授權。

## GPL、AGPL、MIT、Apache 的實際差異

GPL 的 source 義務主要隨 convey／分發觸發；僅在伺服器內運行而不傳送程式副本，不等同分發。給客戶容器、安裝包、瀏覽器 WASM 或其他副本，須另評估对应來源、建置脚本及安裝資訊。不能只給 diff 或依賴未來仍存在的上游連結。[GPL FAQ](https://www.gnu.org/licenses/gpl-faq.en.html)

AGPL §13 對修改版本的遠端網路互動有來源提供義務；將 AGPL 科學引擎包 API 所形成的衍生／結合作品，需要評估。實務上首選規劃為可交付的開源科學服務，附部署版本 source offer、完整來源、依賴與建置資料；不拿「純 SaaS」當作免公開理由。[AGPL 原文](https://www.gnu.org/licenses/agpl-3.0.html)

同 process 的 Python import／link、緊密 RPC 契約、資料結構與控制流程可能影響結合作品判斷。**另開 process／Docker／HTTP port 並不自動免除 copyleft**；React 是否屬獨立作品須看實際結合，不僅看副檔名。不能把「整個網站一定 AGPL」或「HTTP 一定完全隔離」當既定結論。

MIT 要保留著作權／授權通知。Apache-2.0 要附授權、保留相關通知、註明修改，存在 NOTICE 時處理其歸屬內容，另有專利授權與終止條款；不能使用商標冒稱背書。[Apache 原文](https://www.apache.org/licenses/LICENSE-2.0)

GPLv3 與 AGPLv3 具有明文結合安排，但仍須保留各部分授權與適用的網路來源義務。GPL-2-only 元件、NC 材料、無授權程式不能因為主專案採 AGPL 就自動相容。資料 CC-BY-SA 的分享義務，和程式 GPL／AGPL 是不同問題。[CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)

## 依賴清單、測試與尚未完成的 SBOM

三個隔離環境的實際版本記於 `*-probe.json`，安裝命令與 pip 結果記於 `*-install.log`；這不是全部候選／正式服務的完整 transitive SBOM。

| 依賴範圍 | 直接依賴與工程風險 | 授權查核範圍 |
|---|---|---|
| PyLSS | NumPy、SciPy、Matplotlib、PyYAML、PyQt6；本次 headless 刻意不裝 PyQt6 | 數值套件與打包的 BLAS/LAPACK／二進位 notices 逐 distribution 核對；PyQt6 是 GPL／商業雙授權，不當作 LGPL Qt |
| STLC | NumPy、SciPy | 除 Python 套件還要含數值原生庫 notices；正式分發須產出 lock／SBOM |
| OpenIEX | NumPy、SciPy、Matplotlib、pandas、tqdm；本次加 ipywidgets 以配合 notebook progress | MIT 上游不會覆蓋所有依賴授權；Jupyter／widget 相依仍需列出 |
| GRIP／2-step | 分別 chemprop 2.0.4／1.6.1；PyTorch、RDKit、Lightning／PuLP／statsmodels 等 | 兩個環境不能粗暴共用；CBC／其他 LP solver、訓練權重與資料另查 |
| TIMPANI／Graphormer | PyTorch、DGL、RDKit、fairseq 與 graph libraries | 程式版本、native wheels／CUDA、vendor notices 與基模型來源分别核對 |
| CADET | C++ solver 與 cadet-python；Process 的 SciPy、pymoo、hopsy、pipefunc、Numba 等 | native solver／第三方數值庫與 plugin 各自授權；Process pyproject 有 ax／bofire 版本不相容说明，不全塞一環境 |
| MDL-TL | 老 Python 3.7／TensorFlow／Keras／分子表示依賴 | 未批准碼；即使依賴可用也不能整合 |
| Java／R | jmzML、JFreeChart；R／Bioconductor、RaMS 等 | 錯把其中一份 LICENSE 當上游自有碼授權是本次重点排除的風險 |

固定快照根授權檔名、SHA256與開頭證據見 [license-file-evidence.json](research-evidence/license-file-evidence.json)。三個測試環境已另保存 [PyLSS metadata](research-evidence/pylss-dependency-license-metadata.json)、[STLC metadata](research-evidence/stlc-dependency-license-metadata.json)、[OpenIEX metadata](research-evidence/openiex-dependency-license-metadata.json)，含實際版本、License-Expression／classifier與有界License摘錄。這些是distribution自報欄位，空值不等於沒有授權；不能代替vendor／native檔案清查。[PyQt官方授權說明](https://www.riverbankcomputing.com/software/pyqt/intro)確認GPLv3／商業模式。

依賴的常見授權名稱只能作預估，**此階段未完成所有 wheel／native library／外部模型的法律清查**。不能稱目前已取得公開部署的無條件法律許可。

## 上線前必須結案的待確認項目

1. 對所選 CADET release 取得一致授權證據；根 AGPL 與檔頭 GPL 不一致時，確認是授權變更、檔頭遺漏或分檔權利。
2. 若仍希望用 GRIP／Graphormer-RT／MDL-TL／GNN-TL，取得程式、作者修改部分、checkpoint 與必要資料的明確授權；本次沒有聯絡作者或對外發訊。
3. 釐清 2-step／DeepLC／MIT QSRR 每個採用權重的授權、來源、下載校驗及商業／再發布權利；另核對 RepoRT 與個別來源資料。
4. 以最終部署拓撲判斷 derivative／combined work，制定完整 Corresponding Source 與 versioned source offer，保留 copyright、License、NOTICE、修改记录。
5. 產出最終 lock、transitive SBOM、native notices、模型／資料 inventory；以固定版本重做相容性審查。

現在允許的是研究、私有隔離測試與提出設計；沒有公開部署、對外發佈、權重再發布或作者授權確認的既成事實。
