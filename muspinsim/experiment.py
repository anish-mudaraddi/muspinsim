"""experiment.py

A class defining a whole muon experiment"""

import numpy as np
from numbers import Number
from scipy import constants as cnst
from soprano.calculate.powder import ZCW, SHREWD

from muspinsim.constants import MU_TAU
from muspinsim.spinop import DensityOperator, SpinOperator, Operator
from muspinsim.spinsys import MuonSpinSystem
from muspinsim.hamiltonian import Hamiltonian


def _make_rotmat(theta, phi):

    ct = np.cos(theta)
    st = np.sin(theta)
    cp = np.cos(phi)
    sp = np.sin(phi)

    return np.array([
        [cp*ct, -sp, cp*st],
        [sp*ct,  cp, sp*st],
        [-st,     0,    ct]])


class MuonExperiment(object):

    def __init__(self, spins=['e', 'mu']):
        """Create a MuonExperiment object

        Create a "virtual spectrometer" that can be used to carry out any
        number of experiments on a given SpinSystem.

        Keyword Arguments:
            spins {list} -- The spins in the system. See SpinSystem for
                            details (default: {['e', 'mu']})

        Raises:
            ValueError -- If an empty spins list is passed
        """

        if len(spins) == 0:
            raise ValueError('At least one spin must be included')

        self._spin_system = MuonSpinSystem(spins)
        self._orientations = [[0.0, 0.0]]
        self._weights = [1.0]

        # Zeeman Hamiltonian?
        zops = [self._spin_system.operator({i: 'z'})*self._spin_system.gamma(i)
                for i in range(len(spins))]

        self._Hz = zops[0]
        for o in zops[1:]:
            self._Hz += o

        self._Hz = Hamiltonian.from_spin_operator(self._Hz)
        self._B = 0

        self.set_starting_state()

    @property
    def spin_system(self):
        return self._spin_system

    @property
    def orientations(self):
        return np.array(self._orientations)

    @property
    def weights(self):
        return np.array(self._weights)

    @property
    def B(self):
        return self._B

    @property
    def rho0(self):
        return self._rho0

    def set_single_crystal(self, theta=0.0, phi=0.0):
        """Set a single crystal orientation

        Make the sample have a single specified crystallite orientation

        Keyword Arguments:
            theta {number} -- Polar angle (default: {0.0})
            phi {number} -- Azimuthal angle (default: {0.0})
        """

        self._orientations = np.array([[theta, phi]])
        self._weights = np.ones(1)

    def set_powder_average(self, N=20, scheme='zcw'):
        """Set a powder average method

        Set a scheme and a number of angles for a powder averaging algorithm,
        representing a polycrystalline or powdered sample.

        Keyword Arguments:
            N {number} -- Minimum number of orientations to use (default: {20})
            scheme {str} -- Powder averaging scheme, either 'zcw' or 'shrewd'
                            (default: {'zcw'})

        Raises:
            ValueError -- Invalid powder averaging scheme
        """

        try:
            scheme = scheme.lower()
            pwd = {'zcw': ZCW, 'shrewd': SHREWD}[scheme]('sphere')
        except KeyError:
            raise ValueError('Invalid powder averaging scheme ' +
                             scheme)

        orients, weights = pwd.get_orient_angles(N)

        self._orientations = orients
        self._weights = weights

    def set_starting_state(self, muon_axis='x', T=np.inf):
        """Set the starting quantum state for the system

        Sets the starting quantum state for the system as a coherently 
        polarized muon + a thermal density matrix (using only the Zeeman 
        terms) for every other spin.

        Keyword Arguments:
            muon_axis {str|ndarray} -- String or vector defining a direction
                                       for the starting muon polarization 
                                       (default: {'x'})
            T {number} -- Temperature in Kelvin of the state (default: {np.inf})

        Raises:
            ValueError -- Invalid muon axis
        """

        if isinstance(muon_axis, str):
            try:
                muon_axis = {
                    'x': [1, 0, 0],
                    'y': [0, 1, 0],
                    'z': [0, 0, 1]
                }[muon_axis]
            except KeyError:
                raise ValueError('muon_axis must be a vector or x, y or z')
        else:
            muon_axis = np.array(muon_axis)
            muon_axis /= np.linalg.norm(muon_axis)

        mu_i = self.spin_system.muon_index
        rhos = []

        for i, s in enumerate(self.spin_system.spins):
            I = self.spin_system.I(i)
            if i == mu_i:
                r = DensityOperator.from_vectors(I, muon_axis, 0)
            else:
                # Get the Zeeman Hamiltonian for this field
                Sz = SpinOperator.from_axes(I, 'z')
                E = np.diag(Sz.matrix)*self.spin_system.gamma(i)*self.B*1e6
                if T > 0:
                    Z = np.exp(-cnst.h*E/(cnst.k*T))
                else:
                    Z = np.where(E == np.amin(E), 1.0, 0.0)
                if np.sum(Z) > 0:
                    Z /= np.sum(Z)
                else:
                    Z = np.ones(len(E))/len(E)
                r = DensityOperator(np.diag(Z))

            rhos.append(r)

        self._rho0 = rhos[0]
        for r in rhos[1:]:
            self._rho0 = self._rho0.kron(r)

    def set_magnetic_field(self, B=0.0):
        """Set the magnetic field
        
        Set the magnetic field applied to the sample, always pointing along
        the Z axis in the laboratory frame.

        Keyword Arguments:
            B {number} -- Magnetic field in Tesla (default: {0.0})
        """
        self._B = B

    def run_experiment(self, times=[0],
                       operators=None,
                       acquire='e'):
        """Run an experiment
        
        Run an experiment by evolving or integrating the starting state under
        the Hamiltonian of the system for the given times, and measuring the
        given quantity.
        
        Keyword Arguments:
            times {list} -- Times to sample evolution at (default: {[0]})
            operators {list} -- List of operators to measure expectation values 
                                of (default: {None})
            acquire {str} -- Whether to record the evolution ('e') of the 
                             expectation values, or their integral ('i') 
                             convolved with the muon's exponential decay, 
                             or both ('ei', 'ie') (default: {'e'})
        
        Returns:
            dict -- Dictionary of results.
        """

        if operators is None:
            operators = [self.spin_system.operator({
                self.spin_system.muon_index: 'x'
            })]

        # Generate all rotated Hamiltonians
        orients, weights = self._orientations, self._weights

        rotmats = [_make_rotmat(t, p) for (t, p) in orients]
        Hz = self._Hz*self.B
        rho0 = self.rho0
        results = {'e': [], 'i': []}

        for R in rotmats:

            Hint = self.spin_system.rotate(R).hamiltonian
            H = Hz + Hint  # Total Hamiltonian

            if 'e' in acquire:
                # Evolution
                evol = H.evolve(rho0, times, operators)
                results['e'].append(evol)
            if 'i' in acquire:
                intg = H.integrate_decaying(rho0, MU_TAU, operators)/MU_TAU
                results['i'].append(intg)

        # Averaging
        for k, data in results.items():
            if k == 't' or len(data) == 0:
                continue
            results[k] = np.real(np.average(data, axis=0, weights=weights))

        return results
