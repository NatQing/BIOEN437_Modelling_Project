"""Model data structures, propensities and the stoichiometry matrix."""
from dataclasses import dataclass
from math import factorial

import numpy as np


@dataclass
class Reaction:
    name: str
    reactants: dict  # species name -> positive integer stoichiometry
    products: dict
    rate_name: str   # name of the rate constant
    line: int = 0    # source line (for error messages)


@dataclass
class Model:
    species: list      # species names in order of first appearance
    initial: dict      # species name -> initial count (int)
    boundary: set      # species that never change
    reactions: list    # list of Reaction
    constants: dict    # rate constant name -> value (float >= 0)

    def initial_counts(self):
        return [self.initial[s] for s in self.species]

    def stoichiometry_matrix(self):
        """Integer matrix (species x reactions): products minus reactants. Boundary rows are 0."""
        index = {s: i for i, s in enumerate(self.species)}
        N = np.zeros((len(self.species), len(self.reactions)), dtype=np.int64)
        for j, r in enumerate(self.reactions):
            for s, n in r.reactants.items():
                if s not in self.boundary:
                    N[index[s], j] -= n
            for s, n in r.products.items():
                if s not in self.boundary:
                    N[index[s], j] += n
        return N

    def propensities(self, counts):
        """Propensity of every reaction for `counts` (list/array in species order)."""
        index = {s: i for i, s in enumerate(self.species)}
        out = []
        for r in self.reactions:
            pairs = [(index[s], n) for s, n in r.reactants.items()]
            out.append(propensity(self.constants[r.rate_name], pairs, counts))
        return out

    def compile(self):
        """Plain lists used by the simulation loop: (k, [(species_idx, stoich)], [(species_idx, delta)])."""
        index = {s: i for i, s in enumerate(self.species)}
        N = self.stoichiometry_matrix()
        compiled = []
        for j, r in enumerate(self.reactions):
            pairs = [(index[s], n) for s, n in r.reactants.items()]
            changes = [(i, int(N[i, j])) for i in range(len(self.species)) if N[i, j] != 0]
            compiled.append((self.constants[r.rate_name], pairs, changes))
        return compiled


def ways(n, s):
    """Number of distinct ways to pick s molecules out of n: n(n-1)...(n-s+1)/s!.
    s=1 -> n;  s=2 -> n(n-1)/2.  Zero whenever n < s."""
    v = 1.0
    for i in range(s):
        v *= n - i
    return v / factorial(s)


def propensity(k, reactant_pairs, counts):
    """Mass-action propensity: k times the product of ways(count, stoich) over reactants."""
    a = k
    for i, s in reactant_pairs:
        a *= ways(counts[i], s)
    return a


def mass_action_text(rate_name, reactants):
    """Explicit mass-action expression, e.g. k3*A*(A-1)/2 (used by the Antimony export)."""
    factors = []
    denom = 1
    for s, n in reactants.items():
        factors.append(s)
        for i in range(1, n):
            factors.append(f"({s}-{i})")
        denom *= factorial(n)
    expr = "*".join([rate_name] + factors)
    return f"{expr}/{denom}" if denom > 1 else expr
