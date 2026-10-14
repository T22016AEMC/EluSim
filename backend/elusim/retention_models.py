"""Retention adapters. Method-specific Rt is deliberately not a k(phi) model."""
import math

class LSSModel:
    family = 'LSS'
    def __init__(self, compound):
        if compound.logkw is None or compound.s is None:
            raise ValueError('Missing identifiable LSS parameters')
        self.logkw, self.s = compound.logkw, compound.s

    def k(self, phi, conditions):
        if not math.isfinite(phi) or not 0 <= phi <= 1:
            raise ValueError('Organic fraction must be in [0, 1]')
        return 10 ** (self.logkw - self.s * phi)

def retention_model(compound):
    """Only verified model families can enter the migration solver."""
    return LSSModel(compound)
