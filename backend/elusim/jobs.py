"""Bounded disposable processes: timed-out CPU work is actually terminated."""
import multiprocessing as mp, threading, queue
from .schemas import Simulation, Optimize, Calibration
_slots=threading.BoundedSemaphore(2)

def _worker(kind,data,output):
 try:
  from .engine import simulate,optimize,calibrate
  fn,model={'simulation':(simulate,Simulation),'optimization':(optimize,Optimize),'calibration':(calibrate,Calibration)}[kind]
  output.put({'ok':True,'result':fn(model.model_validate(data))})
 except Exception as exc:output.put({'ok':False,'error':str(exc)})

def compute(kind,data,timeout=30):
 if not _slots.acquire(blocking=False):raise RuntimeError('Server busy; two computation slots occupied')
 ctx=mp.get_context('spawn');out=ctx.Queue(maxsize=1);p=ctx.Process(target=_worker,args=(kind,data,out),daemon=True)
 try:
  p.start()
  try:result=out.get(timeout=timeout)
  except queue.Empty:raise TimeoutError('Server computation timeout')
  if not result['ok']:raise ValueError(result['error'])
  return result['result']
 finally:
  if p.is_alive():p.terminate()
  if p.pid:p.join(timeout=3)
  out.close();_slots.release()
