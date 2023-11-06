import numpy as np

from ltest.geometry.plate import Plategeometry
from ltest.model.model import Model

class PlateModel(Plategeometry, Model):
    """Shallow foundaiton Plaxis model with plate elements for the
    structure.

    Parameters
    ----------
    s_i : Server
        Plaxis Input Application remote sripting server.
    g_i : PlxProxyGlobalObject
        Global object of the current open Plaxis model in Input.
    g_o : PlxProxyGlobalObject
        Global object of the current open Plaxis model in Output.
    b : float
        foundation width [m].
    d : float
        foundation depth [m]
    soil : soil : dict, list
        Dictionary with the material properties or list of
        dictionaries.
    footing : dict
        Dictionary with the properties of the material used in 
        the footing.
    column : dict, None
        Dictionary with the properties of the material used in 
        the footing. For surface foundaitons None.
    model_type : str
        Model type: 'axisymmetry' or 'planestrain'. By default
        'axisymetry'.
    element_type : str
        Element type: '6-Noded' or '15-Noded'.
    title : str
        Model title in Plaxis. By default ''
    comments : str
        Model comments in Plaxis. By defautl ''
    dstrata : list, None
        Width of soil layers [m].
    wt : float, None
        Water tabe depth [m]. By default None.
    fill_angle : float
        Fill angle [deg].
    bfill : float
        Distance between foundation edge and the start of the fill
        slope [m]. By default 0.5.
    nfill : int, None
        Number of fill layers. By default None.
    dfill : list, None
        (nfill,) width of fill layers [m]. By default None.
    interface : bool, dict, None, optional
        If True includes all interfaces between the footing and
        soil. A dictionary with fields 'column', 'top' and 'bottom'
        can be provided. If a field is True then the interface is
        activated. Missing fields are assumed to be False.
        If None, only the column interface is activated. By default None.
    model_widht : float, optional
        User specified model width [m]. By default None.
    model_depth : float, optional
        User specified model depth [m]. By default None.
    fill : fill : dict, list
        Dictionary with the fill properties or list of dictionaries.
    mesh_density : float, optional
        Mesh density. By default 0.06
    dratchetting : float, optional
        Widht of soil under the foundation that is replaced when
        ratchetting occurs [m]. By default 0.
    ratchetting_material  : dict, None
        Dictionary with the material properties after ratchetting.
    ratchetting_threshold : float
        Upwards displacement threshold that when surpassed by any
        output location under the foundation the material under
        it is replaced by the ratchetting material. By default
        np.inf.
    locations : array-like, optional
        (nloc, 1) location of output points in the foundation
        bottom, measured as [0, 1] where 0 is the center of the
        foundation and 1 the edge. By default
        [0, 0.25, 0.5, 0.75, 1].
    build : bool, optional
        Builds Plaxis model automatically. By default True.
    excavation : bool, optional
        If True in models with fill, the excavation and fill
        processes are included in the initial phases. By default
        True.
    
    Methods
    -------
    build()
        Builds the model in Plaxis.
    regen(s_i, g_i, g_o, test=False) : 
        Regenerates the model in Plaxis. Optinoally it recalculates
        previous load tests.
    save(filename)
        Saves model to file. Plaxis objects cannot be stored, only
        input properties and results. When loaded, the model can
        be regenerated with <regen> method.
    load(filename)
        Loads saved test.
    failure_test(testid, test, max_load=np.inf, start_load=50, load_factor=2, load_increment=0)
        Test the foundation until the model does not converge.
    load_test(testid, load, delete_phases=True)
        Conducts a load test in the model.
    delete_test( testid, delete_phases=True) 
        Deletes a test from the model.
    plot_test(testid, phase=None, location=None, compression_positive=True, pullout_positive=True, reset_start=False, legend=False, figsize=(6, 4)) 
        Plots test results.
    plot(figsize=2.5, foundation=True, fill=True, soil=True, excavation=False, ratchetting=True, wt=True, interface=False)
        Foundation plot.
    """

    def __init__(self, s_i, g_i, g_o, b, d, soil, footing, column,
                 model_type='axisymmetry',  element_type='15-Noded', title='',
                 comments='', dstrata=None, wt=None, fill_angle=None, bfill=0.5,
                 nfill=None, dfill=None, interface=None, model_width=None,
                 model_depth=None, fill=None, mesh_density=0.06, 
                 dratchetting=0, ratchetting_material=None, 
                 ratchetting_threshold=np.inf,
                 locations=[0, 0.25, 0.5, 0.75, 1], build=True, excavation=True):
        """Init method.

        Parameters
        ----------
        s_i : Server
            Plaxis Input Application remote sripting server.
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        g_o : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Output.
        b : float
            foundation width [m].
        d : float
            foundation depth [m]
        soil : soil : dict, list
            Dictionary with the material properties or list of
            dictionaries.
        footing : dict
            Dictionary with the properties of the material used in 
            the footing.
        column : dict, None
            Dictionary with the properties of the material used in 
            the footing. For surface foundaitons None.
        model_type : str
            Model type: 'axisymmetry' or 'planestrain'. By default
            'axisymetry'.
        element_type : str
            Element type: '6-Noded' or '15-Noded'. By default
            `15-Noded`.
        title : str
            Model title in Plaxis. By default ''
        comments : str
            Model comments in Plaxis. By defautl ''
        dstrata : list, None
            Width of soil layers [m].
        wt : float, None
            Water tabe depth [m]. By default None.
        fill_angle : float
            Fill angle [deg].
        bfill : float
            Distance between foundation edge and the start of the fill
            slope [m]. By default 0.5.
        nfill : int, None
            Number of fill layers. By default None.
        dfill : list, None
            (nfill,) width of fill layers [m]. By default None.
        interface : bool, dict, None, optional
            If True includes all interfaces between the footing and
            soil. A dictionary with fields 'column', 'top' and 'bottom'
            can be provided. If a field is True then the interface is
            activated. Missing fields are assumed to be False.
            If None, only the column interface is activated. By default None.
        model_widht : float, optional
            User specified model width [m]. By default None.
        model_depth : float, optional
            User specified model depth [m]. By default None.
        fill : fill : dict, list
            Dictionary with the fill properties or list of dictionaries.
        mesh_density : float, optional
            Mesh density. By default 0.06
        dratchetting : float, optional
            Widht of soil under the foundation that is replaced when
            ratchetting occurs [m]. By default 0.
        ratchetting_material  : dict, None
            Dictionary with the material properties after ratchetting.
        ratchetting_threshold : float
            Upwards displacement threshold that when surpassed by any
            output location under the foundation the material under
            it is replaced by the ratchetting material. By default
            np.inf.
        locations : array-like, optional
            (nloc, 1) location of output points in the foundation
            bottom, measured as [0, 1] where 0 is the center of the
            foundation and 1 the edge. By default
            [0, 0.25, 0.5, 0.75, 1].
        build : bool, optional
            Builds Plaxis model automatically. By default True.
        excavation : bool, optional
            If True in models with fill, the excavation and fill
            processes are included in the initial phases. By default
            True.
        """
        
        Plategeometry.__init__(self, b, d, dstrata=dstrata, wt=wt,
                               fill_angle=fill_angle, bfill=bfill, nfill=nfill,
                               dfill=dfill, dratchetting=dratchetting,
                               interface=interface, model_width=model_width,
                               model_depth=model_depth)
        Model.__init__(self, s_i, g_i, g_o, model_type, element_type, title,
                       comments, soil, fill, ratchetting_material,
                       ratchetting_threshold, mesh_density, locations,
                       excavation)
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
        footing : dict
            Dictionary with the properties of the material used in 
            the footing.
        column : dict, None
            Dictionary with the properties of the material used in 
            the footing. For surface foundaitons None.
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
        
