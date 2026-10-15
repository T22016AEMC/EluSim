import {demo,type Config,type Compound} from './types';
import {sourceCode} from './sources';
export const PROJECT_VERSION=2;
export function migrateProject(input:unknown):Config {
 if(!input||typeof input!=='object')throw Error('Invalid saved project: expected an object. Original storage retained.');
 const raw=input as Record<string,any>;
 if(!Array.isArray(raw.compounds)||!Array.isArray(raw.gradient))throw Error('Invalid saved project: compounds and gradient are required. Original storage retained.');
 const ids=new Set<string>();
 const compounds=raw.compounds.map((c:any)=>{
  if(!c||typeof c!=='object')throw Error('Invalid compound record; original project retained.');
  let id=typeof c.id==='string'&&c.id.trim()?c.id:crypto.randomUUID();if(ids.has(id))id=crypto.randomUUID();ids.add(id);
  const source=sourceCode(c.source);
  return {...c,id,source,...(c.source!==undefined&&c.source!==source?{source_legacy:c.source_legacy??String(c.source)}:{}),parameter_origin:c.parameter_origin??'manual',mixture_parts:c.mixture_parts??1,response_factor:c.response_factor??1} as Compound;
 });
 return {...raw,project_schema_version:PROJECT_VERSION,compounds,column:{...demo.column,...raw.column},mobile:{...demo.mobile,...raw.mobile},gradient:raw.gradient.map((n:any)=>({...n,interpolation:n.interpolation??'linear'})),mode:raw.mode??'RP',workflow:raw.workflow??'known',points:raw.points??1500} as Config;
}
export function loadProject(storage:Storage):{config:Config;error:string}{
 const original=storage.getItem('elusim-project');if(!original)return {config:structuredClone(demo),error:''};
 try {const config=migrateProject(JSON.parse(original));if(JSON.stringify(config)!==original&&!storage.getItem('elusim-project-before-v2-migration'))storage.setItem('elusim-project-before-v2-migration',original);return {config,error:''};}
 catch(e){return {config:structuredClone(demo),error:String(e)};}
}
