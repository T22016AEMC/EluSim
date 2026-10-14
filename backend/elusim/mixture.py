"""Linear uncalibrated detector response: amount -> area -> Gaussian height."""
def signal_amounts(req):
    compounds=req.compounds
    if req.mixture_basis=='parts':
        total=sum(c.mixture_parts for c in compounds)
        if total<=0:raise ValueError('Total mixture parts must be positive')
        amounts={c.id:c.mixture_parts/total*req.mobile.injection_ul for c in compounds}
        unit='relative amount'
    else:
        units={c.concentration_unit for c in compounds}
        if len(units)!=1:raise ValueError('Use one concentration unit throughout the mixture')
        if any(c.concentration is None for c in compounds):raise ValueError('Concentration required for every component')
        amounts={c.id:c.concentration*req.mobile.injection_ul for c in compounds}
        unit='nmol' if units=={'mM'} else 'µg'
        total=sum(c.concentration for c in compounds)
        if total<=0:raise ValueError('Total concentration must be positive')
    return {c.id:{'mixture_fraction':(c.mixture_parts if req.mixture_basis=='parts' else c.concentration)/total,
                  'injected_amount':amounts[c.id],'amount_unit':unit,
                  'response_factor':c.response_factor,'peak_area':amounts[c.id]*c.response_factor,
                  'signal_unit':'uncalibrated relative response',
                  'signal_assumption':'Equal relative response by default; parts mode assumes total concentration 1 relative amount/µL; linear dilute response, no calibrated UV absorptivity or overload model'} for c in compounds}
