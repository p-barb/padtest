import numpy as np

from ltest.geometry.plate import Plategeometry
from ltest.model.model import Model

class PlateModel(Plategeometry, Model):

    def __init__(self, s_i, g_i, g_o, b, d, soil, footing, column,
                 model_type='axisymmetry',  title='', comments='',
                 dstrata=None, wt=None, fill_angle=None, bfill=0.5,
                 nfill=None, dfill=None, 
                 interface=None,
                 model_width=None, model_depth=None,
                 fill=None, mesh_density=0.06, 
                 dratchetting=0, ratchetting_material=None, 
                 ratchetting_threshold=np.inf,
                 locations=[0, 0.25, 0.5, 0.75, 1], build=True, excavation=True):
        
        Plategeometry.__init__(self, b, d, dstrata=dstrata, wt=wt,
                               fill_angle=fill_angle, bfill=bfill, nfill=nfill,
                               dfill=dfill, dratchetting=dratchetting,
                               interface=interface, model_width=model_width,
                               model_depth=model_depth)
        Model.__init__(self, s_i, g_i, g_o, model_type, title, comments, soil,
                       fill, ratchetting_material, ratchetting_threshold,
                       mesh_density, locations, excavation)
        self._init_foundation_material(footing, column)
        if build:
            self.build()
        
    #===================================================================
    # PRIVATE METHODS
    #===================================================================
    def _init_foundation_material(self, footing, column):
        """Initializes plate materials.

        Parameters
        ----------
        concrete : dict
            Dictionary with the properties of the material used in 
            the foundation.
        """
        self._plate_material['footing'] = footing
        if column is not None:
            self._plate_material['column'] = column

    def _set_load(self):
        """Adds the foundation load to the model.
        """
        self._load = self._g_i.pointload([0, 0])
    
    def _activate_foundation(self, phaseidx):
        """Activates the foundation.

        Parameters
        ----------
        phaseidx : int
            Intex of the phase object in which the foundation is
            activated.
        """
        self._g_i.gotostructures()
        self._footing_plx[-1].setmaterial(self._plate_material_plx['footing'])
        if self._column is not None:
            self._column_plx[-1].setmaterial(self._plate_material_plx['column'])
        self._g_i.gotostages()
        self._g_i.activate(self._footing_plx[2], self._g_i.phases[phaseidx])
        if self._column is not None:
            self._g_i.activate(self._column_plx[2], self._g_i.phases[phaseidx])
    
    def _set_output_precalc(self):
        """Select output points before calcualtion. Used for points in
        the soil."""
        pass
    
    def _set_output_postcalc(self):
        """Select output points before calcualtion. Used for points in
        structural elements."""        
        plate_column = self._g_o.get_equivalent(self._g_i.Plate_1_1)
        if self._d > 0:
            plate_footing = self._g_o.get_equivalent(self._g_i.Plate_2_1)
        else:
            plate_footing = self._g_o.get_equivalent(self._g_i.Plate_1_1)
        
        self._ouput_point['top'] = self._g_o.addcurvepoint("node", plate_column, (0, 0))
        for loc in self._ouput_location:
            self._ouput_point[loc] = self._g_o.addcurvepoint("node", plate_footing, (loc * self._b / 2,  -self._d))
        
    
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
        self._g_i.view(iphase)
        self._set_output_postcalc()
        load_start = 0
        load_end = 0
        for sidx, step in enumerate(ophase.Steps.value):
            sumMstage[sidx + 1] = step.Reached.SumMstage.value
            for locidx, node in enumerate(self._ouput_point.keys()):
                Uy[locidx, sidx + 1] = self._g_o.getcurveresults(self._ouput_point[node], step, self._g_o.ResultTypes.Plate.Uy)
        if self._g_i.PointLoad_1_1.Active[previphase] is not None:
            if self._g_i.PointLoad_1_1.Active[previphase].value:
                load_start = self._g_i.PointLoad_1_1.Fy[previphase].value
        if self._g_i.PointLoad_1_1.Active[iphase] is not None:
            if self._g_i.PointLoad_1_1.Active[iphase].value:
                load_end = self._g_i.PointLoad_1_1.Fy[iphase].value
                Fy = load_start + (load_end - load_start) * sumMstage
        qy = np.zeros_like(Fy)
        return sumMstage, Fy, qy, Uy, load_start, load_end
        
