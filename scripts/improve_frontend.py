"""Targeted interface fixes; avoid changing research documents."""
import pathlib
root=pathlib.Path(__file__).resolve().parents[1]
p=root/'frontend/src/main.tsx';s=p.read_text(encoding='utf8')
s=s.replace("request.current?.abort();if(!auto)return;", "request.current?.abort();setBusy(b=>b==='Simulating'?'':b);if(!auto)return;")
s=s.replace("stationary_phase:config.column.stationary_phase,mobile_b:config.mobile.b,ph:config.mobile.ph,temperature_c:config.column.temperature_c", "stationary_phase:config.column.stationary_phase,mobile_a:config.mobile.a,buffer:config.mobile.buffer,mobile_b:config.mobile.b,ph:config.mobile.ph,temperature_c:config.column.temperature_c")
s=s.replace("JSON.stringify({input:config,result},null,2)", "JSON.stringify({input:result.input,result},null,2)")
s=s.replace("async function optimize(){const r=", "async function optimize(){const inputFingerprint=JSON.stringify(current.current);const r=")
s=s.replace("if(r)setCandidates(r.candidates);", "if(r&&inputFingerprint===JSON.stringify(current.current))setCandidates(r.candidates);else if(r)setError('Method changed during optimization; rerun for current inputs.');")
p.write_text(s,encoding='utf8')
p=root/'frontend/src/types.ts';s=p.read_text(encoding='utf8').replace("stationary_phase:string;mobile_b:","stationary_phase:string;mobile_a:string;buffer:string;mobile_b:").replace("export type Result={model:string;", "export type Result={input:Config;model:string;");p.write_text(s,encoding='utf8')
print('Scope, stale request and export fixes applied')
