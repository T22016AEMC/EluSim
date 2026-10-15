export function validationMessage(detail:unknown,body?:unknown):string {
 if(!Array.isArray(detail))return typeof detail==='string'?detail:JSON.stringify(detail);
 return detail.map((item:any)=>{const path=(item.loc||[]).filter((p:unknown)=>p!=='body');let node:any=body;let compound:any;
  for(let i=0;i<path.length;i++){node=node?.[path[i]];if(path[i-1]==='compounds')compound=node;}
  return (compound?String(compound.name||compound.id)+' ('+String(compound.id)+') — ':'')+path.join('.')+': '+item.msg;
 }).join('\n');
}
export async function api<T>(path:string,body?:unknown,signal?:AbortSignal):Promise<T>{
 const response=await fetch('/api/'+path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:undefined,body:body?JSON.stringify(body):undefined,signal});
 let data:any;try{data=await response.json();}catch{throw Error('API '+path+' returned a non-JSON response (HTTP '+response.status+').');}
 if(!response.ok)throw Error('API '+path+' (HTTP '+response.status+') — '+validationMessage(data.detail,body));return data;
}
