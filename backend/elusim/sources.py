"""Stable provenance codes; display labels and legacy text are not scientific evidence."""
from typing import Literal
Source = Literal['measured','calibrated','model_based','screening_only','insufficient_data','unsupported','experimental','literature_derived','validated_model_prediction','experimental_model_prediction','qualitative_screening','unknown_legacy']
LABELS = {'measured':'Measured','calibrated':'Calibrated','model_based':'Model-based','screening_only':'Screening only','insufficient_data':'Insufficient data','unsupported':'Unsupported','experimental':'Experimental','literature_derived':'Literature-derived','validated_model_prediction':'Validated model prediction','experimental_model_prediction':'Experimental model prediction','qualitative_screening':'Qualitative screening','unknown_legacy':'Unknown / Legacy'}
ALIASES = {label.casefold():code for code,label in LABELS.items()}
ALIASES.update({'基於模型':'model_based','基于模型':'model_based','實測':'measured','实测':'measured','已校正':'calibrated','校正':'calibrated','僅供篩選':'screening_only','資料不足':'insufficient_data','不支援':'unsupported','未知':'unknown_legacy','legacy':'unknown_legacy','unknown':'unknown_legacy'})
def source_code(value):
    if isinstance(value,str):
        stripped=value.strip()
        if stripped in LABELS:return stripped
        return ALIASES.get(stripped.casefold(),'unknown_legacy')
    return 'unknown_legacy'
