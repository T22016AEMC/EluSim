# EluSim_V1 交付與驗收紀錄

日期：2026-10-13。**公開容器部署及HTTPS自動化驗收成功；完整的使用者跨網路實機計算驗收仍未完成。** 使用者已確認手機與電腦開啟／基本操作正常，但未手動驗證計算或提供實驗資料，見[使用者回報](elusim-v1-user-test-report.md)。依最新指示，保持程式與部署不變。

## 必須交付的13項

|項目|實際結果|
|---|---|
|1 Repository|[T22016AEMC/EluSim](https://github.com/T22016AEMC/EluSim)，功能分支 `feature/elusim-v1`；沒有合併main|
|2 科學引擎與版本|獨立 `elusim-lss-migration/1.0.0`；NumPy2.5.4、SciPy1.18.1、RDKit2026.9.1；PyLSS固定commit d2cda850fa0b0881fc3cf1cd68c4d93b59dac04f只作未修改的參考對照。Python容器3.12.12、本機3.12.14、CI3.12.15；lockfiles列完整依賴|
|3 授權|平台AGPL-3.0-or-later，完整LICENSE／NOTICE、PyLSS原版標頭及來源hash、完整依賴通知與metadata；網站Model Library及[/api/source](https://elusim-v1.onrender.com/api/source)提供部署版本相應原始碼及建置／測試檔。CADET、無授權模型及外部權重未部署|
|4 模式與功能|RP已知／校正LSS參數的等度、多段線性／step、hold、dwell、流速與幾何遷移、未洗脫；Gaussian近似峰寬/FWHM/Rs、洗脫排序、候選梯度搜尋與套用。名稱本地別名、SMILES、RDKit、基本2D繪製、CSV/SDF/MOL、多成分、通用柱／自訂、手機工作區、圖形zoom/legend/hover及PNG/CSV/JSON、瀏覽器專案保存、兩方法以上校正|
|5 不能定量預測|NP/HILIC/IEX/SEC、聚合物／肽／蛋白的正式模式未啟用；需要獨立模型與參數驗證。沒有合法且外部驗證的結構→保留參數權重，Structure-Based顯示缺模型，不生成任意Rt。pH／溫度／溶劑轉移需要matching scope；無gradient compression／過載／真實尾峰／壓力物性模型，不能聲稱其準確度|
|6 Backend|本機20通過；修正匯入後Linux CI20通過，512MiB容器內測試及health均通過。[CI run](https://github.com/T22016AEMC/EluSim/actions/runs/38352409671)。Starlette/httpx有非失敗deprecation warning|
|7 Frontend|TypeScript與Vite正式建置本機及Linux CI成功；ECharts bundle有>500kB提示，非建置錯誤|
|8 公開網址|[https://elusim-v1.onrender.com](https://elusim-v1.onrender.com)，Render Singapore免費Docker Web Service。開發電腦不需要持續開機，未使用LAN或靜態展示代替後端|
|9 線上連線|[/api/health](https://elusim-v1.onrender.com/api/health)、RDKit、三成分模擬、梯度／流速／柱長敏感性、最佳化、相應原始碼下载：PASS_PUBLIC_API_SMOKE。來源revision與部署commit一致|
|10 桌面／手機|本機4項及**公開HTTPS4項** Playwright tests通過，含桌面與Pixel7尺寸、API、圖形、最佳化套用、refresh、unsupported模式、JS error及橫向溢出。真實使用者只確認手機／電腦基本操作；未確認行動網路、未手動驗證計算。不能稱實機科學測試通過|
|11 Git／PR／版本|公開部署commit [d42594a0c80834080e0d3bdf8cf638f4c8ed6abc](https://github.com/T22016AEMC/EluSim/commit/d42594a0c80834080e0d3bdf8cf638f4c8ed6abc)，[Draft PR #1](https://github.com/T22016AEMC/EluSim/pull/1)。程式版本1.0.0；本機保留RC版本標記，GitHub公開tag未推送，不假稱已發布tag。原研究／本機開發備份分支保留|
|12 成本／限制|實際service plan=free，512MiB。免費服務15分鐘閒置後可能休眠／冷啟動，有資源與流量配額；没有建立付費DB或付費服務。[官方限制](https://render.com/docs/free)。30 POST/min、1MiB request、20成分、40節點、24候選、兩個計算程序、30秒硬逾時；proxy可能聚合IP，未宣稱大量併發capacity。Render原生建立工具未設定HTTP healthCheckPath，DockerHEALTHCHECK及API health已建立並實測；autoDeploy目前關閉，CI deploy hook未配置Secret，後續自動發佈設定見部署文件|
|13 V2 科學重點|外部RP實驗留出集與參數適用域／prediction intervals；驗證gradient compression／峰形／儀器展寬；合法QSRR參數模型；有校正資料的SEC或IEX獨立模式。這些未實作，不以V2為理由延後本次HTTPS部署|

## 測試來源與命令

所有科學fixture均為**合成参数**，未當作實驗滯留準確度。實際線上測試使用三組(logKw,S)：(2,4)、(2.5,4.5)、(3,5)。

```powershell
.venv/Scripts/python.exe -m pytest -q --junitxml=artifacts/backend-tests.xml
# frontend工作目錄
pnpm run build
$env:ELUSIM_BASE_URL='https://elusim-v1.onrender.com'
pnpm test:e2e
# Repository工作目錄
.venv/Scripts/python.exe scripts/public_smoke.py https://elusim-v1.onrender.com
```

公開API smoke於2026-10-13T05:41:49Z開始。第一成分Rt基準5.621255935 min；較慢梯度7.160486303；流量加倍4.254383661；柱長150mm為6.495955625。此表驗證條件敏感性／接線，不是外部準確度。線上browser suite四項全部通過，總時間約2.3分鐘；手機項為模擬。

本機`artifacts/`保存backend XML、local-browser-tests.json、public-smoke.json與公開browser-tests.json／PNG。公開CI保存Linux結果；原始碼含可重跑腳本。接續文件commit只是增加使用者回報，不修改或重新部署現有科學程式。

## 失敗與修正也保留

初次Linux CI19通過／1失敗：參考測試把repo父目錄加入sys.path，本機`python -m pytest`掩蓋問題；改為repo根目錄後CI通過。第一次Render部署`dep-db6s5nt9fdbs73e5oln0` runtime缺libexpat.so.1，未報為成功；補expat/freetype/fontconfig系統依賴，第二次`dep-db6s7kom7kps73b5shq0`回報live。成功service `srv-db6s5n59fdbs73e5oj7g`、workspace `tea-db6qffon74is738k4q30`。pnpm11 allowBuilds與Windows沙箱建置問題已解決，未略過TypeScript或科學檢查。

Git原始碼發布用已授權GitHub連接器；本機Git Credential Manager装置登入未完成／token到期，沒有把金鑰放進原始碼。後續公開Git fetch與工作分支對齊，不強推或合併main。

## 17項驗收對照

1–15：已完成對應程式／模型邊界、可重現測試與部署設定；其中峰形／Rs明示Gaussian screening，不宣稱外部LC準確度。16：公開HTTPS前後端與自動化流程通過。**17：公開桌面及手機尺寸自動化通過，使用者實機基本操作正常；不同網路／行動網路的實機計算驗收未完成。** 因此不能稱16、17全部實機驗收完成，也不能稱已驗證LC實驗準確度。
