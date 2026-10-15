"""Exact chemical scope; formulation pH is not an estimated ionization state."""
def method_scope(req):
    return {'mode':req.mode,'stationary_phase':req.column.stationary_phase,'mobile_a':req.mobile.a,
            'mobile_b':req.mobile.b,'buffer':req.mobile.buffer,'ph':req.mobile.ph,
            'ph_control':req.mobile.ph_control,'temperature_c':req.column.temperature_c}

def scope_matches(scope,req):
    actual=method_scope(req)
    declared=scope.model_dump() if hasattr(scope,'model_dump') else dict(scope)
    declared.setdefault('mode','RP');declared.setdefault('ph_control','fixed')
    return declared==actual


def scope_mismatches(scope, req):
    actual=method_scope(req)
    declared=scope.model_dump() if hasattr(scope,'model_dump') else dict(scope)
    declared.setdefault('mode','RP');declared.setdefault('ph_control','fixed')
    return [f'{key}: current {actual.get(key)!r}; required {value!r}' for key,value in declared.items() if actual.get(key)!=value]
