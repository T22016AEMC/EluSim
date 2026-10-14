# EluSim_V2 部署與測試紀錄
日期2026-10-14；原始公開入口 https://elusim-v1.onrender.com/ 不變。沿用現有Singapore Render免費Docker服務，不建立付費資源。V1部署原commit d42594a0c80834080e0d3bdf8cf638f4c8ed6abc；GitHub b685d6b1baca45caac8c169859fa0f626f6646d8僅文件差異。

本機使用者已把根目錄程式移入EluSim_V1，導致原工作tree显示檔案刪除；未復原／刪除使用者資料夾與ZIP。EluSim_V2為同一GitHubRepository的乾淨checkout，起點完整V1，不是空白新平台。開發分支feature/elusim-v2；release/elusim-v1-stable固定保留b685，程式與已部署V1相同。

本機Python使用既有隔離venv，離線加裝單一sklearn1.7.2；Docker/production backend lock不增加sklearn或Torch。模型壓縮JSON约2.9MB UV+13KB LC；完整数据与sourcearchive可重現。服務端不下載權重或連線外部科學API，不接受模型上傳或任意URL。

候選8892bbaa11ea4d3121c2cce509ef835319736721的Linuxbackend/frontbuild/Docker/512MiB容器29項及health已通過：[CI38509189244](https://github.com/T22016AEMC/EluSim/actions/runs/38509189244)。最終一致的能力文字commit b17fbd417a0cc97587bf6b184816a891ac90ffbe亦完成同樣檢查：[CI38509426820](https://github.com/T22016AEMC/EluSim/actions/runs/38509426820)。沒有本機Docker，实际Dockerbuild是在GitHub Linux CI执行，不冒稱本機Dockerbuild。

實際測試命令：
~~~powershell
$env:PYTHONPATH='backend'
../EluSim_V1/.venv/Scripts/python.exe -m pytest -q --junitxml=artifacts/v2-backend-tests.xml
# frontend目录
pnpm install --frozen-lockfile
pnpm run build
$env:ELUSIM_BASE_URL='http://127.0.0.1:8102'
pnpm test:e2e
# 上線後才執行以下公開origin
../EluSim_V1/.venv/Scripts/python.exe scripts/public_smoke.py https://elusim-v1.onrender.com
../EluSim_V1/.venv/Scripts/python.exe scripts/public_smoke_v2.py https://elusim-v1.onrender.com
$env:ELUSIM_BASE_URL='https://elusim-v1.onrender.com'
pnpm test:e2e
~~~

公開部署完成與線上測試結果將在本文件另行追加，不能用上述計畫命令替代实际结果。至此本機backend29、browser8、frontendbuild成功，手機尺寸是Pixel7模拟，不是實機／行動網路。

既有RenderautoDeploy關閉，GitHubdeployhookSecret未配置。原生Render工具不暴露更新Gitbranch操作，因此在完全驗證後可將既有部署分支feature/elusim-v1以非強推fast-forward至驗證V2commit，再手動trigger部署；獨立V2開發分支與V1保留分支仍在，main不合併。來源包含RENDER_GIT_COMMIT追溯；失败時保持／回復可驗證V1来源，不宣稱成功。

基本资源限制保留：1MiB请求、20成分、40节点、24梯度候選、30POST/min、2科學计算slot／30shardtimeout。UV/retention是小型CPU唯讀推論，没有不受限訓練或量子化学在线任务。免费服务仍可能闲置15分鐘休眠／coldstart；沒有付費升級。正式HTTPproviderhealthCheckPath尚未由原生工具設定，DockerHEALTHCHECK与/APIhealth已測。版本CI有node20actiondeprecated與>500kBbundle提示，不影響實際測試結果。

Render部署dep-db7fvq7avr4c73843ekg已於2026-10-14T04:08:14Z回報live，來源b17fbd417a0cc97587bf6b184816a891ac90ffbe；public smoke/browser仍在實際執行。實際Git更新是非強推fast-forward、main未合併。

初次公開V2(b17)驗證：V1 PASS_PUBLIC_API_SMOKE、V2 PASS_PUBLIC_V2_SMOKE、公開桌面＋手機尺寸8項通過(2.5min)。public_v2_smoke首次在本機組裝40°C方法前誤用25°Cdefaultcolumn，Pydantic拒絕，並非伺服器計算失敗；已修正constructor順序，失敗JSON保留artifacts/public-v2-smoke-initial-failure.json。實測樣本Rt0.8808036088min（未見於train）；UV181points／窗內maximum260nm；方法／domain／無chromophore時拒絕假結果，原始匯入保留。

授權收尾另核對原始FigshareCC-BY4，從PNNL932筆移除2筆數值不能對照的記錄，重訓UVmodel2.0.1。初版仅BSD標示不完整已更正。新的來源完整性測試及容器／公開測試將另行執行；不把初版public測試冒稱新版結果。線上採樣memory97–174MB、limit536870900bytes，非stress容量保證；查詢時無errorlogs。
