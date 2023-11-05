import numpy as np

from ltest.geometry.solid import SolidGeometry
from ltest.model.model import Model

class SolidModel(Model, SolidGeometry):

    def __init__(self, s_i, g_i, g_o, b, d, b1, d1, soil, concrete,
                 model_type='axisymmetry', title='', comments='',
                 dstrata=None,
                 wt=None, fill_angle=None, bfill=0.5,
                 nfill=None, dfill=None, 
                 interface=None,
                 model_width=None, model_depth=None,
                 fill=None, mesh_density=0.06, 
                 dratchetting=0, ratchetting_material = None, 
                 ratchetting_threshold=np.inf,
                 locations=[0, 0.25, 0.5, 0.75, 1], build=True, excavation=True):
        SolidGeometry.__init__(self, b, d, b1, d1, dstrata=dstrata, wt=wt,
                               fill_angle=fill_angle, bfill=bfill, nfill=nfill,
                               dfill=dfill, dratchetting=dratchetting,
                               interface=interface, model_width=model_width,
                               model_depth=model_depth)
        Model.__init__(self, s_i, g_i, g_o, model_type, title, comments, soil,
                       fill, ratchetting_material, ratchetting_threshold,
                       mesh_density, locations, excavation)
        self._init_foundation_material(concrete)
        if build:
            self.build()

    #===================================================================
    # PRIVATE METHODS
    #===================================================================
    def _init_foundation_material(self, concrete):
        """Initializes the foundaiton material.

        Parameters
        ----------
        concrete : dict
            Dictionary with the properties of the material used in 
            the foundation.
        """
        self._soil_material['concrete'] = concrete

    def _set_load(self):
        """Adds the foundation load to the model.
        """
        if self._d > self._d1:
            self._load = self._g_i.lineload([0, 0], [self._b1 / 2, 0])
        else:
            zload = -self._d + self._d1
            self._load = self._g_i.lineload([0, zload], [self._b1 / 2, zload])
    
    def _activate_foundation(self, phaseidx):
        """Activates the foundation.

        Parameters
        ----------
        phaseidx : int
            Intex of the phase object in which the foundation is
            activated.
        """
        for poly_idx in self._foundation:
            self._g_i.activate(self._structure_polygons[poly_idx], self._g_i.phases[phaseidx])
            self._set_soil_material(self._g_i, poly_idx + 1, phaseidx, 'concrete')

    def _set_output_precalc(self):
        """Select output points before calcualtion. Used for points in
        the soil."""
        self._g_i.gotostages()
        self._g_i.set(self._g_i.Model.CurrentPhase, self._iphases[self._start_phase])
        self._g_i.selectmeshpoints()

        
        soil_idx = int(np.max(self._foundation) + 1)
        for soil in self._g_i.Soils:
            if soil.Name.value == 'Soil_{:.0f}_1'.format(soil_idx):
                soil_o = self._g_o.get_equivalent(soil)
                break
        for loc in self._ouput_location:
            self._ouput_point[loc] = self._g_o.addcurvepoint("node", soil_o, (loc * self._b / 2, -self._d))
        soil_o = self._g_o.get_equivalent(self._g_i.Soil_1_1)
        if self._d > self._d1:
            self._ouput_point['top'] = self._g_o.addcurvepoint("node", soil_o, (0, 0))
        else:
            self._ouput_point['top'] = self._g_o.addcurvepoint("node", soil_o, (0, self._d1 - self._d))
        self._g_o.update()

    def _set_output_postcalc(self):
        """Select output points before calcualtion. Used for points in
        structural elements."""
        pass

    def _extract_initial_phase_results(self, phaseid, sumMstage, Uy):
        """Extracts results form the output of the initial phases calculation.

        Parameters
        ----------
        phaseid : str
            Phase id.
        sumMstage : np.ndarray
            (nstep, 1) sumMstage of the phase.
        Uy : np.ndarray
            (nstep, nloc) displacement at the output locations.

        Returns
        -------
        np.ndarray
            (nstep, 1) sumMstage of the phase.
        np.ndarray
            (nstep, nloc) displacement at the output locations.
        """
        for sidx, step in enumerate(self._ophases[phaseid].Steps.value):
            sumMstage[sidx] = step.Reached.SumMstage.value
            for locidx, node in enumerate(self._ouput_point.keys()):
                Uy[locidx, sidx] = self._g_o.getcurveresults(self._ouput_point[node], step, self._g_o.ResultTypes.Soil.Uy)
        return sumMstage, Uy

    def _extract_phase_results(self, iphase, previphase, ophase, sumMstage, Fy, Uy):
        """Extracts results form the output of the initial phases calculation.

        Parameters
        ----------
        iphase : PlxProxyIPObject
            Plaxis object in the input interface for the current phase.
        previphase : PlxProxyIPObject
            Plaxis object in the input interface for the previous phase.
        ophase : PlxProxyIPObject
            Plaxis object in the output interface for the previous phase.
        sumMstage : np.ndarray
            (nstep + 1, 1) sumMstage of the phase.
        Fy : np.ndarray
            (nstep + 1, 1) load applied to the foundaiton.
        Uy : np.ndarray
            (nstep + 1, nloc) displacement at the output locations.

        Returns
        -------
        np.ndarray
            (nstep + 1, 1) sumMstage of the phase.
        np.ndarray
            (nstep + 1, 1) Fy of the phase.
        np.ndarray
            (nstep + 1, 1) qy of the phase.
        np.ndarray
            (nstep + 1, nloc) displacement at the output locations.
        float
            Load at the start of the phase.
        float
            Load at the end of the phase.
        """
        load_start = 0
        load_end = 0
        for sidx, step in enumerate(ophase.Steps.value):
            sumMstage[sidx + 1] = step.Reached.SumMstage.value
            for locidx, node in enumerate(self._ouput_point.keys()):
                Uy[locidx, sidx + 1] = self._g_o.getcurveresults(self._ouput_point[node], step, self._g_o.ResultTypes.Soil.Uy)
        if self._g_i.LineLoad_1_1.Active[previphase] is not None:
            if self._g_i.LineLoad_1_1.Active[previphase].value:
                load_start = self._g_i.LineLoad_1_1.qy_start[previphase].value
        if self._g_i.LineLoad_1_1.Active[iphase] is not None:
            if self._g_i.LineLoad_1_1.Active[iphase].value:
                load_end = self._g_i.LineLoad_1_1.qy_start[iphase].value
                qy = load_start + (load_end - load_start) * sumMstage
                Fy = qy * self._b1
        return sumMstage, Fy, qy, Uy, load_start, load_end
        
  

    