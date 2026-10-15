import {test,expect} from '@playwright/test';
import {demo} from '../src/types';

test('legacy storage migrates without loss; real peaks precede collapsed gradient; failed API hides old results',async({page},info)=>{
 test.setTimeout(180000);
 const old=structuredClone(demo) as any;old.compounds[0].source='基於模型';old.compounds[1].source='Model-based';old.compounds[2].source='Unrecognized historic provenance';old.compounds.forEach((c:any,i:number)=>c.mixture_parts=[5,3,2][i]);old.compounds[1].smiles='CCO';
 await page.addInitScript(data=>{if(!sessionStorage.getItem('repair-seeded')){localStorage.setItem('elusim-project',JSON.stringify(data));sessionStorage.setItem('repair-seeded','1');}},old);
 await page.goto('/');await expect(page.getByLabel('logKw Synthetic A')).toHaveValue('2');
 const saved=await page.evaluate(()=>({project:JSON.parse(localStorage.getItem('elusim-project')!),backup:JSON.parse(localStorage.getItem('elusim-project-before-v2-migration')!)}));
 expect(saved.project.compounds.map((c:any)=>c.source)).toEqual(['model_based','model_based','unknown_legacy']);expect(saved.project.compounds.map((c:any)=>c.id)).toEqual(['a','b','c']);expect(saved.project.compounds[1].smiles).toBe('CCO');expect(saved.project.gradient).toEqual(old.gradient);expect(saved.backup).toEqual(old);
 const response=page.waitForResponse(r=>r.url().endsWith('/api/simulate'));await page.getByRole('button',{name:'Run simulation',exact:false}).first().click();const r=await response;expect(r.ok()).toBeTruthy();const result=await r.json();expect(result.order).toHaveLength(3);expect(result.peaks.map((p:any)=>p.mixture_fraction)).toEqual([.5,.3,.2]);expect(result.traces.every((t:any)=>Math.max(...t.y)>0)).toBeTruthy();
 await expect(page.getByTestId('chromatogram').locator('canvas')).toBeVisible();await expect(page.getByTestId('gradient-profile')).not.toBeVisible();await expect(page.locator('main section').first().getByRole('heading')).toHaveText('Simulated Chromatogram');
 await page.getByText('Gradient Profile — programmed / column inlet',{exact:true}).click();await expect(page.getByTestId('gradient-profile').locator('canvas')).toBeVisible();await page.getByText('Gradient Profile — programmed / column inlet',{exact:true}).click();
 await page.screenshot({path:'../artifacts/'+info.project.name+'-repair-chromatogram.png',fullPage:true});
 await page.getByRole('navigation').getByRole('button',{name:'Compounds',exact:false}).click();await page.getByLabel('S Synthetic B',{exact:true}).fill('-1');await page.getByRole('button',{name:'Run simulation',exact:false}).first().click();await expect(page.getByRole('alert')).toContainText('Synthetic B (b) — compounds.1.s',{timeout:45000});await expect(page.getByRole('heading',{name:'LC 分離模擬未完成',exact:true})).toBeVisible();await expect(page.getByTestId('chromatogram')).toHaveCount(0);await expect(page.getByTestId('gradient-profile')).toHaveCount(0);
 await page.screenshot({path:'../artifacts/'+info.project.name+'-repair-failure.png',fullPage:true});
 await page.reload();await expect(page.getByLabel('logKw Synthetic A')).toHaveValue('2');expect(await page.evaluate(()=>JSON.parse(localStorage.getItem('elusim-project')!).compounds[2].source)).toBe('unknown_legacy');
 expect(await page.evaluate(w=>document.documentElement.scrollWidth<=w+1,page.viewportSize()!.width)).toBeTruthy();
});

test('conditions require explicit selection; incomplete retention and nonelution never masquerade as peaks',async({page})=>{
 test.setTimeout(150000);await page.goto('/');await page.getByRole('button',{name:'LC Mode & Column',exact:false}).click();await expect(page.getByText('particle_um:',{exact:false})).toBeVisible();await expect(page.getByLabel('Particle size (µm)',{exact:true})).toHaveValue('1.7');await page.getByRole('button',{name:'Use model-compatible conditions',exact:true}).click();await expect(page.getByLabel('Particle size (µm)',{exact:true})).toHaveValue('3.5');await expect(page.getByLabel('Column temperature (°C)',{exact:true})).toHaveValue('35');
 await page.getByRole('button',{name:'Reset synthetic demonstration',exact:true}).click();await page.getByRole('navigation').getByRole('button',{name:'Compounds',exact:false}).click();
 for(const name of ['Synthetic A','Synthetic B','Synthetic C'])await page.getByLabel('S '+name,{exact:true}).fill('');
 await page.getByRole('button',{name:'Run simulation',exact:false}).first().click();await expect(page.getByTestId('simulation-incomplete')).toContainText('Missing logKw / S',{timeout:45000});await expect(page.getByTestId('chromatogram')).toHaveCount(0);await expect(page.getByTestId('gradient-profile')).not.toBeVisible();
 await page.getByRole('navigation').getByRole('button',{name:'Compounds',exact:false}).click();for(const name of ['Synthetic A','Synthetic B','Synthetic C']){await page.getByLabel('logKw '+name,{exact:true}).fill('12');await page.getByLabel('S '+name,{exact:true}).fill('0');}
 await page.getByRole('button',{name:'Run simulation',exact:false}).first().click();await expect(page.getByTestId('simulation-incomplete')).toContainText('本時間窗內未洗脫',{timeout:45000});await expect(page.getByTestId('chromatogram')).toHaveCount(0);
});


test('Structure workflow simulation persists the actual resolved parameters by Compound ID',async({page})=>{
 test.setTimeout(120000);await page.goto('/');await page.getByRole('button',{name:'Retention Prediction',exact:false}).click();await page.getByRole('button',{name:'Load three experimental curve compounds'}).click();await page.getByRole('navigation').getByRole('button',{name:'Compounds',exact:false}).click();await expect(page.getByLabel('logKw Caffeine',{exact:true})).toHaveValue('');await page.getByLabel('Workflow',{exact:true}).selectOption('structure');
 await page.getByRole('button',{name:'Run simulation',exact:false}).first().click();await expect(page.getByTestId('chromatogram').locator('canvas')).toBeVisible({timeout:45000});await page.getByRole('navigation').getByRole('button',{name:'Compounds',exact:false}).click();await expect(page.getByLabel('logKw Caffeine',{exact:true})).not.toHaveValue('');const saved=await page.evaluate(()=>JSON.parse(localStorage.getItem('elusim-project')!));expect(saved.compounds.every((c:any)=>c.source==='literature_derived'&&c.logkw!=null&&c.s!=null)).toBeTruthy();expect(new Set(saved.compounds.map((c:any)=>c.id)).size).toBe(3);expect(saved.workflow).toBe('known');
});
