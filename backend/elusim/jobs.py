"""Bounded disposable processes; timeout or request cancellation stops CPU work."""

import multiprocessing as mp
import queue
import threading
import time

from .schemas import (
    Calibration,
    Optimize,
    OptimizeMap,
    OptimizeMultiSegment,
    Simulation,
)

_slots = threading.BoundedSemaphore(2)


def _worker(kind, data, output):
    """Resolve one typed operation inside a disposable process."""
    try:
        from .engine import calibrate, optimize, simulate
        from .optimizer import optimize_map, optimize_multisegment

        operations = {
            "simulation": (simulate, Simulation),
            "optimization": (optimize, Optimize),
            "calibration": (calibrate, Calibration),
            "optimization_map": (optimize_map, OptimizeMap),
            "optimization_multisegment": (optimize_multisegment, OptimizeMultiSegment),
        }
        function, model = operations[kind]
        output.put({"ok": True, "result": function(model.model_validate(data))})
    except Exception as exc:
        output.put({"ok": False, "error": str(exc)})


def compute(kind, data, timeout=30, cancelled=None):
    """Run within two slots; terminate on timeout or a set cancellation event."""
    if not _slots.acquire(blocking=False):
        raise RuntimeError("Server busy; two computation slots occupied")
    context = mp.get_context("spawn")
    output = context.Queue(maxsize=1)
    process = context.Process(target=_worker, args=(kind, data, output), daemon=True)
    deadline = time.monotonic() + timeout
    try:
        process.start()
        while True:
            if cancelled is not None and cancelled.is_set():
                raise RuntimeError("Computation cancelled")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Server computation timeout")
            try:
                result = output.get(timeout=min(0.1, remaining))
                break
            except queue.Empty:
                continue
        if not result["ok"]:
            raise ValueError(result["error"])
        return result["result"]
    finally:
        if process.is_alive():
            process.terminate()
        if process.pid:
            process.join(timeout=3)
        output.close()
        _slots.release()
