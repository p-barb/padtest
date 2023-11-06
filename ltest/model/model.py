from abc import ABC, abstractmethod
import copy
import numpy as np
import matplotlib.pyplot as plt
import numbers
import pandas as pd
import pickle
import sys

from ltest.material.plate import PlateMaterial
from ltest.material.soil import SoilMaterial


class Model(ABC):
    """Base class for models.
    
    Parameters
    ----------
    s_i : Server
        Plaxis Input Application remote sripting server.
    g_i : PlxProxyGlobalObject
        Global object of the current open Plaxis model in Input.
    g_o : PlxProxyGlobalObject
        Global object of the current open Plaxis model in Output.
    model_type : str
        Model type: 'axisymmetry' or 'planestrain'.
    element_type : str
        Element type: '6-Noded' or '15-Noded'.
    title : str
        Model title in Plaxis.
    comments : str
        Model comments in Plaxis.
    soil : soil : dict, list
        Dictionary with the material properties or list of
        dictionaries.
    fill : fill : dict, list
        Dictionary with the fill properties or list of dictionaries.
    ratchetting_material  : dict, None
        Dictionary with the material properties after ratchetting.
    ratchetting_threshold : float, None
        Upwards displacement threshold that when surpassed by any
        output location under the foundation the material under
        it is replaced by the ratchetting material.
    mesh_density : float
        Mesh density.
    locations : array-like
        Location of output points in the foundation bottom, measured
        as [0, 1] where 0 is the center of the foundation and 1 the
        edge.
    excavation : bool
        If True in models with fill, the excavation and fill
        processes are included in the initial phases.

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
    """

    def __init__(self, s_i, g_i, g_o, model_type, element_type, title,
                 comments, soil, fill, ratchetting_material,
                 ratchetting_threshold, mesh_density, locations, excavation):
        """Init method.

        Parameters
        ----------
        s_i : Server
            Plaxis Input Application remote sripting server.
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        g_o : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Output.
        model_type : str
            Model type: 'axisymmetry' or 'planestrain'.
        element_type : str
            Element type: '6-Noded' or '15-Noded'.
        title : str
            Model title in Plaxis.
        comments : str
            Model comments in Plaxis.
        soil : soil : dict, list
            Dictionary with the material properties or list of
            dictionaries.
        fill : fill : dict, list
            Dictionary with the fill properties or list of dictionaries.
        ratchetting_material  : dict, None
            Dictionary with the material properties after ratchetting.
        ratchetting_threshold : float
            Upwards displacement threshold that when surpassed by any
            output location under the foundation the material under
            it is replaced by the ratchetting material.
        mesh_density : float
            Mesh density.
        locations : array-like
            (nloc, 1) location of output points in the foundation
            bottom, measured as [0, 1] where 0 is the center of the
            foundation and 1 the edge.
        excavation : bool
            If True in models with fill, the excavation and fill
            processes are included in the initial phases.        
        """
        self._s_i = s_i
        self._g_i = g_i
        self._g_o = g_o
        self._soil_material = {} # inputs required to create the materials
        self._plate_material = {} # inputs required to create the materials
        self._soil_material_plx = {} # Plaxis objects of the materials
        self._plate_material_plx = {} # Plaxis objects of the materials
        self._iphases = {}
        self._init_model_settings(title, comments, model_type, element_type)
        self._init_strata_materials(soil)
        self._init_fill_materials(fill)
        self._init_ratchetting_material(ratchetting_material, ratchetting_threshold)
        self._init_mesh(mesh_density)
        self._init_output(locations)
        self._build_excavation = excavation
    
    #===================================================================
    # PRIVATE METHODS
    #===================================================================
    def _init_model_settings(self, title, comments, model_type, element_type):
        """Initialize model settings.

        Parameters
        ----------
        title : str, None
            Model title in Plaxis.
        comments : str, None
            Model comments in Plaxis.
        model_type : str
            Model type: `axisymmetry` or `planestrain`.
        element_type : str
            Element type: '6-Noded' or '15-Noded'.
        """
        self._title = title
        self._comments = comments
        self._model_type = model_type
        self._element_type = element_type

    def _init_strata_materials(self, soil):
        """Initializes the materials for the stratigraphy.

        Parameters
        ----------
        soil : dict, list
            Dictionary with the material properties or list of
            dictionaries.

        Raises
        ------
        RuntimeError
            Numer of provided materials does not match the number of
            soil layers.
        """
        if isinstance(soil, dict):
            soil = [soil]
        if len(soil) != self._nstrata:
            msg = "A material must be specified for each of the {:.0f} soil layers."
            msg = msg.format(self._nstrata)
            raise RuntimeError(msg)
        for idx, strata in enumerate(soil):
            label = "strata_{:.0f}".format(idx + 1)
            self._soil_material[label] = strata

    def _init_fill_materials(self, fill):
        """Initializes fill materials.

        Parameters
        ----------
        fill : dict, list
            Dictionary with the fill properties or list of dictionaries.

        Raises
        ------
        RuntimeError
            No fill material provided.
        RuntimeError
            Numer of provided fill materials does not match the number
            of fill layers.
        """
        if self._fill is None:
            return
        if fill is None:
            raise RuntimeError('Fill material must be specified.')
        if isinstance(fill, dict):
            fill = [fill]
        if len(fill) != self._nfill:
            msg = "A material must be specified for each of the {:.0f} fill layers."
            msg = msg.format(self._nfill)
            raise RuntimeError(msg)
        for idx, mat in enumerate(fill):    
            label = "fill_{:.0f}".format(idx + 1)
            self._soil_material[label] = mat

    def _init_ratchetting_material(self, ratchetting_material, ratchetting_threshold):
        """Initializes the ratchetting material.

        Parameters
        ----------
        ratchetting_material  : dict
            Dictionary with the material properties after ratchetting.
        ratchetting_threshold : float
            Upwards displacement threshold that when surpassed by any
            output location under the foundation the material under
            it is replaced by the ratchetting material.

        Raises
        ------
        RuntimeError
            Ratchetting material missing.
        """
        if self._ratchetting is None:
            self._ratchetting_threshold = np.inf
            return
        if ratchetting_material is None:
            raise RuntimeError('The post ratchetting material must be specified.')
        self._soil_material['ratchetting'] = ratchetting_material
        self._ratchetting_threshold = ratchetting_threshold

    @abstractmethod
    def _init_foundation_material(self):
        return NotImplementedError
    
    def _init_mesh(self, mesh_density):
        """Initializes mesh settings.

        Parameters
        ----------
        mesh_density : float
            Mesh density.
        """
        self._mesh_density = mesh_density

    def _init_output(self, locations):
        """Initializes output.

        Parameters
        ----------
        locations : array-like
            (nloc, 1) location of output points in the foundation
            bottom, measured as [0, 1] where 0 is the center of the
            foundation and 1 the edge.
        """
        self._ophases = {}
        self._test_log = {}
        results_df = pd.DataFrame(columns=['test', 'phase', 'previous', 'plx id',
                                           'previous plx id', 'location', 'step',
                                           'load start', 'load end', 'load',
                                           'uy', 'sumMstage', 'fy', 'qy', 'uy',
                                           'ratchetting'])
        self._results = results_df
        self._ophases = {}
        self._ouput_location = locations
        self._ouput_point = {}

    def _set_model(self):
        """General model settings.
        """
        self._s_i.new()
        self._g_i.SoilContour.initializerectangular(0, -self._model_depth, self._model_width, 0)
        self._g_i.setproperties("Title",self._title,
                                "Comments",self._comments,
                                "ModelType",self._model_type,
                                "ElementType",self._element_type)

    def _build_geometry(self):
        """Builds model in Plaxis
        """
        self._structure_polygons = []
        self._structure_soil = []
        self._phase_polygons = []
        for poly in self._polygons:
            struct_poly, struct_soil, phase_poly = poly.add_2_model(self._g_i)
            self._structure_polygons.append(struct_poly)
            self._structure_soil.append(struct_soil)
            self._phase_polygons.append(phase_poly)

        if self._global_wt is not None:
            self._g_i.gotoflow()
            self._waterlevel = self._g_i.waterlevel([0, -self._global_wt],
                                                    [self._model_width, -self._global_wt])
        else:
            self._waterlevel = None
        
        self._g_i.gotostructures()
        self._column_plx = None
        self._footing_plx = None
        if self._column is not None:
            self._column_plx = self._g_i.plate(*[list(v) for v in self._column])
        if self._footing is not None:
            self._footing_plx = self._g_i.plate(*[list(v) for v in self._footing])
        self._interface = []
        for vertex in self._interface_vertex:
            self._interface.append(self._g_i.neginterface(list(vertex[0]), list(vertex[1])))

    def _build_materials(self):
        """Creates soil and plate materials in the model.
        """
        for matid in self._soil_material:
            self._soil_material_plx[matid] = SoilMaterial.set(self._g_i, matid, self._soil_material[matid])
        for matid in self._plate_material:
            self._plate_material_plx[matid] = PlateMaterial.set(self._g_i, matid, self._plate_material[matid])

    @abstractmethod
    def _set_load(self):
        return NotImplementedError
    
    def _set_mesh(self):
        """Mesh the model.
        """
        self._g_i.gotomesh()
        self._mesh = self._g_i.mesh(self._mesh_density)

    def _build_initial_phases(self):
        """Add the initial phases to the model.
        """
        if self._fill is not None and self._excavation:
            self._initial_phases_with_excavation()
        elif self._fill is not None and not self._excavation:
            self._initial_phases_no_excavation(fill=True)
        else:
            self._initial_phases_no_excavation()
                 
    def _initial_phases_with_excavation(self):
        """Adds the initial, excavation and construction phases in a
        model with excavation.
        """

        self._g_i.gotostages()
        self._start_phase = 'construction'
        self._start_phase_idx = 2
        self._nphase = 3
        # Initial phase
        self._iphases['Initial Phase'] = self._g_i.InitialPhase
        self._g_i.Model.CurrentPhase = self._g_i.InitialPhase

        for poly in self._structure_polygons:
            self._g_i.activate(poly, self._g_i.Model.CurrentPhase)
        
        if self._footing is not None:
            self._g_i.deactivate(self._footing_plx[2], self._g_i.Model.CurrentPhase)
        if self._column is not None:
            self._g_i.deactivate(self._column_plx[2], self._g_i.Model.CurrentPhase)

        for strata_idx, poly_idxs in self._excavation.items():
            for poly_idx in poly_idxs:
                self._set_soil_material(self._g_i, poly_idx + 1, 0, 'strata_{:.0f}'.format(strata_idx + 1))
        for strata_idx, poly_idxs in self._strata.items():
            for poly_idx in poly_idxs:
                self._set_soil_material(self._g_i, poly_idx + 1, 0, 'strata_{:.0f}'.format(strata_idx + 1))
        if self._ratchetting is not None:
            for strata_idx, poly_idxs in self._ratchetting.items():
                for poly_idx in poly_idxs:
                    self._set_soil_material(self._g_i, poly_idx + 1, 0, 'strata_{:.0f}'.format(strata_idx + 1))

        # Excavation phase
        self._iphases['excavation'] = self._g_i.phase(self._g_i.InitialPhase)
        self._iphases['excavation'].Identification = "excavation"
        self._g_i.Model.CurrentPhase = self._iphases['excavation']
        self._g_i.set(self._g_i.Model.CurrentPhase.MaxStepsStored, 1000)

        for strata_idx, poly_idxs in self._excavation.items():
            for poly_idx in poly_idxs:
                self._g_i.deactivate(self._structure_polygons[poly_idx], self._g_i.Model.CurrentPhase)

        # construction phase
        self._iphases['construction'] = self._g_i.phase(self._iphases['excavation'])
        self._iphases['construction'].Identification = "construction"
        self._g_i.Model.CurrentPhase = self._iphases['construction']
        self._g_i.set(self._g_i.Model.CurrentPhase.MaxStepsStored, 1000)
        self._activate_foundation(2)
        for strata_idx, poly_idxs in self._fill.items():
            for poly_idx in poly_idxs:
                self._g_i.activate(self._structure_polygons[poly_idx], self._g_i.Model.CurrentPhase)

        for strata_idx, poly_idxs in self._fill.items():
            for poly_idx in poly_idxs:
                self._set_soil_material(self._g_i, poly_idx + 1, 2, 'fill_{:.0f}'.format(strata_idx + 1))

        if self._interface is not None:
            for interface in self._interface:
                self._g_i.activate(interface[2], self._g_i.Model.CurrentPhase)
    
    def _initial_phases_no_excavation(self, fill=False):
        """Adds the initial phase to a model without excavation.

        Parameters
        ----------
        fill : bool
            Sets excavated material to fill. By default False.
        """
        self._g_i.gotostages()
        self._start_phase = 'construction'
        self._start_phase_idx = 0
        self._nphase = 1
        # Initial phase
        self._iphases['Initial Phase'] = self._g_i.InitialPhase
        self._g_i.Model.CurrentPhase = self._g_i.InitialPhase

        for poly in self._structure_polygons:
            self._g_i.activate(poly, self._g_i.Model.CurrentPhase)

        self._activate_foundation(0)

        for strata_idx, poly_idxs in self._strata.items():
            for poly_idx in poly_idxs:
                self._set_soil_material(self._g_i, poly_idx + 1, 0, 'strata_{:.0f}'.format(strata_idx + 1))
        
        if self._ratchetting is not None:
            for strata_idx, poly_idxs in self._ratchetting.items():
                for poly_idx in poly_idxs:
                    self._set_soil_material(self._g_i, poly_idx + 1, 0, 'strata_{:.0f}'.format(strata_idx + 1))

        if self._interface is not None:
            for interface in self._interface:
                self._g_i.activate(interface[2], self._g_i.Model.CurrentPhase)

        if fill and self._fill is not None:
            for strata_idx, poly_idxs in self._fill.items():
                for poly_idx in poly_idxs:
                    self._set_soil_material(self._g_i, poly_idx + 1, 2, 'fill_{:.0f}'.format(strata_idx + 1))
        
        # construction phase
        self._iphases['construction'] = self._g_i.phase(self._iphases['Initial Phase'])
        self._iphases['construction'].Identification = "construction"
        self._g_i.Model.CurrentPhase = self._iphases['construction']
        self._g_i.set(self._g_i.Model.CurrentPhase.
                      MaxStepsStored, 1000)

    def _set_soil_material(self, g_i, soil_idx, phase_idx, material):
        """Assings a soil material to a polygon in a given phase. g_i
        must be passed as an argument so it is in the variable space.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        soil_idx : int
            Numer that identifies the soil, e.g. Soil_#.
        phase_idx : int
            Index of the phase in the self._g_i.phases list.
        material : str
            Material key in the soil material dictionary.
        """
        material = "self._soil_material_plx['{}']".format(material)
        txt = "self._g_i.setmaterial(self._g_i.Soil_{:.0f}, self._g_i.phases[{:.0f}], {})"
        txt = txt.format(soil_idx, phase_idx, material)
        exec(txt)

    @abstractmethod
    def _activate_foundation(self, phase):
        return NotImplementedError
    
    @abstractmethod
    def _set_output_precalc(self):
        """Select output points before calcualtion. Used for points in
        the soil."""
        return NotImplementedError
    
    @abstractmethod
    def _set_output_postcalc(self):
        """Select output points before calcualtion. Used for points in
        structural elements."""
        return NotImplementedError
    
    def _calculate_initial_phases(self):
        """Computs initial phases.

        Raises
        ------
        RuntimeError
            Phase calculation error.
        """
        
        for phase in self._iphases:
            phaseid = phase
            status = self._g_i.calculate(self._iphases[phase])
            if status != 'OK':
                raise RuntimeError(status)
        
        self._g_i.view(self._g_i.Model.CurrentPhase)
        self._set_output_postcalc()

        self._ophases[phaseid] = self._g_o.phases[-1]
        nstep = len(list(self._ophases[phaseid].Steps.value))
        Uy = np.zeros((len(self._ouput_location) + 1, nstep))
        sumMstage = np.zeros(nstep)
        Fy = np.zeros(nstep)
        qy = np.zeros(nstep)
        steps = np.linspace(1, nstep, nstep)
        load_start = 0
        load_end = 0


        sumMstage, Uy = self._extract_initial_phase_results(phaseid, sumMstage, Uy)
        
        # ad results to dataframe
        for locidx, loc in enumerate(self._ouput_point):
            df = pd.DataFrame({'test':[None] * nstep,
                               'phase':[self._iphases[phase].Identification.value] * nstep,
                               'previous':[None] * nstep,
                               'plx id':[self._iphases[phase].Name.value] * nstep,
                               'previous plx id':[None] * nstep,
                               'location': [loc] * nstep,
                               'step': steps,
                               'load start':[load_start] * nstep,
                               'load end':[load_end] * nstep,
                               'load':[0] * nstep,
                               'sumMstage':sumMstage, 
                               'fy': Fy,
                               'qy': qy,
                               'uy': Uy[locidx, :],
                               'ratchetting': [False] * nstep})
            if len(self._results) == 0:
                self._results = df
            else:
                self._results = pd.concat([self._results, df])
            self._results.reset_index(inplace=True, drop=True)

    @abstractmethod
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
        return NotImplementedError
               
    def _calculate_load_phase(self, testid, phaseid, prevphaseid, load, ratchetting):
        """Computes a phase in a load test.

        Parameters
        ----------
        testid : str
            Test id.
        phaseid : str
            Phase id
        prevphaseid : str
            If of the previous phase.
        load : numeric
            Load value at the end of the phase [kN].
        ratchetting : bool
            Flag indicating that ratchetting has alredy occured in any
            previous phase.

        Returns
        -------
        str
            Calculation status, 'OK' or error message.
        """
        self._test_log[testid]['phase'].append(phaseid)
        self._iphases[phaseid] = self._g_i.phase(self._iphases[prevphaseid])
        self._iphases[phaseid].Identification = phaseid

        self._g_i.Model.CurrentPhase = self._iphases[phaseid]
        self._g_i.set(self._g_i.Model.CurrentPhase.MaxStepsStored, 1000)
        self._update_ratchetting_material(testid, ratchetting, phaseid, prevphaseid)
        
        if self._foundation_type == 'solid':
            self._g_i.activate(self._g_i.LineLoad_1_1, self._g_i.Model.CurrentPhase)
            self._g_i.set(self._g_i.LineLoad_1_1.qy_start, self._g_i.Model.CurrentPhase, load / self._b1)
        else:
            self._g_i.activate(self._g_i.PointLoad_1_1, self._g_i.Model.CurrentPhase)
            self._g_i.set(self._g_i.PointLoad_1_1.Fy, self._g_i.Model.CurrentPhase, load)
            # self._g_i.activate(self['load'][0], self._g_i.Model.CurrentPhase)
            # self._g_i.set(self['load'][1].Fy, self._g_i.Model.CurrentPhase, load)
        status = self._g_i.calculate(self._g_i.Model.CurrentPhase)
        return status
    
    def _update_ratchetting_material(self, testid, ratchetting, phaseid, prevphaseid):
        """Sets the ratchetting material under the base if ratchetting
        occured in the previous phase.

        Parameters
        ----------
        testid : str
            Test id.
        ratchetting : bool
            Flag indicating that ratchetting has alredy occured in any
            previous phase.
        phaseid : str
            Phase id
        prevphaseid : str
            If of the previous phase.
        """
        if not ratchetting:
            return
        idx = (self._results['test'] == testid) \
              & (self._results['phase'] != phaseid) \
              & (self._results['phase'] != prevphaseid)
        if any(self._results.loc[idx, 'ratchetting'].to_list()):
            return
        for _, poly_idxs in self._ratchetting.items():
            for poly_idx in poly_idxs:
                self._set_soil_material(self._g_i, poly_idx + 1, self._iphases[phaseid].Number.value, 'ratchetting')

    def _check_phase_status(self, status, testid, phaseid, delete_phases):
        """Checks calculation status.

        Parameters
        ----------
        status : str
            Calculation status, 'OK' or error message.
        testid : str
            Test id.
        phaseid : str
            Phase id
        delete_phases : bool, optional
            Deletes test phases from model if there is a calculation
            error, by default True.

        Raises
        ------
        RuntimeError
            Calculation failed.
        """
        if status == 'OK':
            self._g_i.view(self._g_i.Model.CurrentPhase)
            self._ophases[phaseid] = self._g_o.phases[-1]
            return
        self.delete_test(testid, delete_phases=delete_phases)
        raise RuntimeError(status + ' <{}>'.format(phaseid))
    
    def _check_ratchetting(self, testid, phaseid, ratchetting):
        """Checks if ratchetting occurred in a calculation phase.

        Parameters
        ----------
        testid : str
            Test id.
        phaseid : str
            Phase id
        ratchetting : bool
            Flag indicating that ratchetting has alredy occured in any
            previous phase.

        Returns
        -------
        Bool
            True if ratchetting occured in the phase.
        """
        if ratchetting or self._ratchetting is None:
            return ratchetting
        idx = (self._results['test'] == testid) \
              & (self._results['phase'] == phaseid) \
              & (self._results['location'] != 'top') \
              & (self._results['uy']<0)
        if -self._results.loc[idx, 'uy'].min() >= self._ratchetting_threshold:
            ratchetting = True
            idx = (self._results['test'] == testid) \
                  & (self._results['phase'] == phaseid) 
            self._results.loc[idx, 'ratchetting'] = True
        return ratchetting

    def _set_phase_results(self, testid, load_value, phaseid, prevphaseid):
        """Adds phase results to the results dataframe.

        Parameters
        ----------
        testid : str
            Test id.
        load_value : numeric
            Load value at the end of the phase [kN].
        phaseid : str
            Phase id
        prevphaseid : str
            If of the previous phase.
        ratchetting : bool
            Flag indicating that ratchetting has alredy occured in any
            previous phase.
        """
        iphase = self._iphases[phaseid]
        previphase = self._iphases[prevphaseid]
        ophase = self._ophases[phaseid]

        nstep = len(list(ophase.Steps.value))
        Uy = np.zeros((len(self._ouput_location) + 1, nstep + 1))
        sumMstage = np.zeros(nstep + 1)
        Fy = np.zeros(nstep + 1)
        steps = np.linspace(0, nstep, nstep + 1)
        
        # start with last step from previous phase
        idx1 = (self._results['phase'] == prevphaseid)
        f0 = self._results.loc[idx1].take([-1])['fy'].to_list()[0]
        Fy[0] = f0
        for locidx, node in enumerate(self._ouput_point.keys()):
            idx2 = idx1 & (self._results['location'] == node)
            U0 = self._results.loc[idx2].take([-1])['uy'].to_list()[0]
            Uy[locidx, 0] = U0

        # get current phase results
        sumMstage, Fy, qy, Uy, load_start, load_end = self._extract_phase_results(iphase, previphase, ophase, sumMstage, Fy, Uy)
        
        # ad results to dataframe
        for locidx, loc in enumerate(self._ouput_point):
            df = pd.DataFrame({'test':[testid] * (nstep + 1),
                               'phase':[iphase.Identification.value] * (nstep + 1),
                               'previous':[previphase.Identification.value] * (nstep + 1),
                               'plx id':[iphase.Name.value] * (nstep + 1),
                               'previous plx id':[previphase.Name.value] * (nstep + 1),
                               'location': [loc] * (nstep + 1),
                               'step': steps,
                               'load start':[load_start] * (nstep + 1),
                               'load end':[load_end] * (nstep + 1),
                               'load':[load_value] * (nstep + 1),
                               'sumMstage':sumMstage, 
                               'fy': Fy,
                               'qy': qy,
                               'uy': Uy[locidx, :],
                               'ratchetting': [False] * (nstep + 1)})
            if len(self._results) == 0:
                self._results = df
            else:
                self._results = pd.concat([self._results, df])
            self._results.reset_index(inplace=True, drop=True)

    @abstractmethod
    def _extract_phase_results(self, iphase, previphase, ophase, sumMstage, Fy, Uy):
        """Extracts results form the output of the initial phases calculation.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        g_o : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Output.
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
        return NotImplementedError

    def query_yes_no(self, question, default="yes"):
        """Ask yes/no question, keeps asking until acceptable answer.

        Parameters
        ----------
        question : str
            Question asked.
        default : str, optional
            Default answer value, "yes" or "no. By default "yes".

        Returns
        -------
        bool
            Answer.

        Raises
        ------
        ValueError
            Invalid default.
        """
        valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
        if default is None:
            prompt = " [y/n] "
        elif default == "yes":
            prompt = " [Y/n] "
        elif default == "no":
            prompt = " [y/N] "
        else:
            raise ValueError("invalid default answer: '%s'" % default)

        while True:
            sys.stdout.write(question + prompt)
            choice = input().lower()
            if default is not None and choice == "":
                return valid[default]
            elif choice in valid:
                return valid[choice]
            else:
                sys.stdout.write("Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n")
    #===================================================================
    # PUBLIC METHODS
    #===================================================================
    def build(self):
        """Builds the model in Plaxis.
        """
        self._set_model()
        self._build_geometry()
        self._build_materials()
        self._set_load()
        self._set_mesh()
        self._build_initial_phases()
        self._set_output_precalc()
        self._calculate_initial_phases()
    
    def regen(self, s_i, g_i, g_o, test=False):
        """Regenerates the model in Plaxis. Optinoally it recalculates
        previous load tests.

        Parameters
        ----------
        s_i : Server
            Plaxis Input Application remote sripting server.
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        g_o : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Output.
        test : bool, optional
            Reclaculate all load tests in Plaxis. By default False.
        """
        self._s_i = s_i
        self._g_i = g_i
        self._g_o = g_o
        idx = (self._results['phase']=='construction') | (self._results['phase']=='excavation')
        self._results = self._results[~idx]
        self._results.reset_index(drop=True, inplace=True)
        self.build()
        if not test:
            return
        idx = (self._results['phase']=='construction') | (self._results['phase']=='excavation')
        self._results = self._results[idx]
        self._results.reset_index(drop=True, inplace=True)
        test_log = copy.deepcopy(self._test_log)
        self._test_log = {}
        for test in test_log:
            if test['type'] == 'load':
                self.load_test(test['id'], test['load'])
            else:
                self.failure_test(test['id'], test['load'],
                                  max_load=test['max_load'], start_load=test['start_load'],
                                  load_factor=test['load_factor'], load_increment=test['load_increment'])

    def save(self, filename):
        """Saves model to file. Plaxis objects cannot be stored, only
        input properties and results. When loaded, the model can
        be regenerated with <regen> method.

        Parameters
        ----------
        filename : str
            File name.
        """
        question = ("WARNIGN: Saving the load test to memory whipes out the Plaxis "
                    "objects. Test results and input parameters will still "
                    "be avaiable, but no further interaction with Plaxis "
                    "will be possible. The model can be restored with the "
                    "<regen> method, but load tests will have to be recalculated "
                    "to access the results whitin Plaxis.\n\n Do you whish to proceed:")
        proceed = self.query_yes_no(question, default="yes")
        if not proceed:
            return
        self._s_i = None
        self._g_i = None
        self._g_o = None
        self._soil_material_plx = {} # Plaxis objects of the materials
        self._plate_material_plx = {} # Plaxis objects of the materials
        self._iphases = {}
        self._ophases = {}
        self._structure_polygons = None
        self._structure_soil = None
        self._phase_polygons = None
        self._waterlevel = None
        self._column_plx = None
        self._footing_plx = None
        self._interface = None
        self._load = None
        self._mesh = None
        self._ouput_point = {}
        with open(filename, 'wb') as handle:
            pickle.dump(self, handle, protocol=pickle.HIGHEST_PROTOCOL)

    @classmethod
    def load(cls, filename):
        """Loads saved test.

        Parameters
        ----------
        filename : str
            File name.

        Raises
        ------
        RuntimeError
            File does not contain load test.
        """
        with open(filename, 'rb') as handle:
            model = pickle.load(handle)
            if not isinstance(model, Model):
                raise RuntimeError('File <{}> does not contain a load test.'.format(filename))
            return model
    
    def failure_test(self, testid, test, max_load=np.inf,
                     start_load=50, load_factor=2, load_increment=0):
        """Test the foundation until the model does not converge. A
        first trial is done using the start_load value. If lack of
        convergence is not achieved, the load is incremented as: 

        load = load_factor * load + load_increment.

        Parameters
        ----------
        testid : str
            Test id.
        test : str
            Test type: 'compression' or 'pull out'.
        max_load : numeric, optional
            Maximum load to be analyzed (in absolute value) [kN].
            By default np.inf
        start_load : numeric, optional
            Initial load applied to the model (in absolute value) [kN].
            By default 50
        load_factor : numeric, optional
            Multiplicative factor applied to the previous load when
            iteration is required. By default 2.
        load_increment : numeric, optional
            Load increment applied to the previous load when iteration
            is required. By default 0.

        Raises
        ------
        RuntimeError
            Duplicated test id.
        RuntimeError
            Invalid test type.
        """
        if testid in self._test_log.keys():
            raise RuntimeError('Duplicated test id <{}>.'.format(testid))
        self._test_log[testid] = {}
        self._test_log[testid]['id'] = testid
        self._test_log[testid]['type'] = 'failure'
        self._test_log[testid]['load'] = test
        self._test_log[testid]['phase'] = []
        self._test_log[testid]['max_load'] = max_load
        self._test_log[testid]['start_load'] = start_load
        self._test_log[testid]['load_factor'] = load_factor
        self._test_log[testid]['load_factor'] = load_factor

        if test not in ('compression', 'pull out'):
            msg = "Test type can either be <'compression'> or <'pull out'>."
            raise RuntimeError(msg)
        if test == 'compression':
            load = -np.abs(start_load)
        else:
            load = np.abs(start_load)
        phaseid = testid
        previous_phase = self._start_phase
        status = 'OK'
        while status == 'OK' and np.abs(load) <= max_load:
            status = self._calculate_load_phase(testid, phaseid, previous_phase, load, False)
            load = load_factor * load + np.sign(load) * load_increment
            if status == 'OK':
                for phase in self._g_i.phases:
                    if phase.Identification.value == phaseid:
                        self._g_i.delete(phase)
                _ = self._iphases.pop(phaseid)
                self._test_log[testid]['phase'] = []
        self._g_i.view(self._g_i.Model.CurrentPhase)
        self._ophases[phaseid] = self._g_o.phases[-1]
        self._set_phase_results(testid, load, phaseid, previous_phase)

    def load_test(self, testid, load, delete_phases=True):
        """Conducts a load test in the model.

        Parameters
        ----------
        testid : str
            Test id.
        load : numeric, array-like
            (nl,) Loads applied in each phase of the test [kN].
        delete_phases : bool, optional
            Deletes test phases from model if there is a calculation
            error, by default True.

        Raises
        ------
        RuntimeError
            Test id alredy in model.
        """
   
        if testid in self._test_log.keys():
            raise RuntimeError('Duplicated test id <{}>.'.format(testid))
        self._test_log[testid] = {}
        self._test_log[testid]['id'] = testid
        self._test_log[testid]['type'] = 'load'
        self._test_log[testid]['load'] = load
        self._test_log[testid]['phase'] = []
        
        if isinstance(load, numbers.Number):
            load = [load]
        test_phases = [testid + '_stage_{:.0f}'.format(idx) for idx in range(len(load))]
        previous_phase = [self._start_phase] + test_phases[:-1]
        ratchetting = False
        for load_value, phaseid, prevphaseid in zip(load, test_phases, previous_phase):
            status = self._calculate_load_phase(testid, phaseid, prevphaseid,
                                                load_value, ratchetting)
            self._check_phase_status(status, testid, phaseid, delete_phases)
            self._set_phase_results(testid, load_value, phaseid, prevphaseid)
            ratchetting = self._check_ratchetting(testid, phaseid, ratchetting)
    
    def delete_test(self, testid, delete_phases=True):
        """Deletes a test from the model.

        Parameters
        ----------
        testid : str
            Test id.
        delete_phases : bool, optional
            Deletes test phases from model, by default True

        Raises
        ------
        RuntimeError
            Test not present in model.
        """
        if testid not in self._test_log:
            msg = 'Test <{}> not in results'.format(testid)
            raise RuntimeError(msg)
        test_phases = self._test_log[testid]['phase']
        _ = self._test_log.pop(testid)
        if delete_phases:
            test_phases.reverse()
            for phaseid in test_phases:
                for phase in self._g_i.phases:
                    if phase.Identification.value == phaseid:
                        self._g_i.delete(phase)
                for phase in self._g_o.phases:
                    if phase.Identification.value == phaseid:
                        self._g_i.delete(phase)
            test_phases.reverse()
        for phaseid in test_phases:
            if phaseid in self._iphases:
                _ = self._iphases.pop(phaseid)
            if phaseid in self._ophases:
                _ = self._ophases.pop(phaseid)
        self._results = self._results[self._results['test']!=testid]
        self._results.reset_index(drop=True, inplace=True)

    def plot_test(self, testid, phase=None, location=None, 
                  compression_positive=True, pullout_positive=False,
                  reset_start=False, legend=False, figsize=(6, 4)):
        """Plots test results.

        Parameters
        ----------
        testid : str
            Test id.
        phase : str, int, list, None, optional
            Phase id or list of them. If None all phases are plotted.
            By default None.
        location : str, float, optional
            Location. If None all locations are plotted. By default 
            None.
        compression_positive : bool, optional
            Compresive force is plotted as positive. By default True.
        pullout_positive : bool, optional
            Pull out displacement is plotted as positive. By default
            False.
        reset_start : bool, optional
            Resets the first point of the load-displacement curve to
            (0, 0). By default False
        legend : bool, optional
            Shows legend. By default False
        figsize : tuple, optional
            Figure size. By default (6, 4).

        Returns
        -------
        Figure
            Figure with the test plot.

        Raises
        ------
        RuntimeError
            Test id not in restuls.
        RuntimeError
            Phase not in results.
        """
        if testid not in self._results['test'].to_list():
            raise RuntimeError('Test <{}> not available in restuls.'.format(testid))
        idx = self._results['test'] == testid
        if phase is None:
            phase = self._results[idx]['phase'].unique()
        elif isinstance(phase, (str, numbers.Number)):
            phase = [phase]
        phase_order = []
        for pidx in range(len(phase)):
            if isinstance(phase[pidx], numbers.Number):
                phase[pidx] = '{}_stage_{:.0f}'.format(testid, phase[pidx])
            if phase[pidx] not in self._results[idx]['phase'].to_list():
                msg = 'Phase <{}> not available in test <{}> not available in restuls'
                msg = msg.format(phase[pidx], testid)
                raise RuntimeError(msg)
            idx2 = idx & (self._results['phase']==phase[pidx])
            phase_order.append(int(self._results[idx2]['plx id'].unique()[0][6:]))
        phase = [x for _, x in sorted(zip(phase_order, phase))]

        if location is None:
            location = self._results[idx]['location'].unique()
        elif isinstance(location, (str, numbers.Number)):
            location = [location]
            
        fig, ax = plt.subplots(1, 1, figsize=figsize)
        
        fsign = 1
        dsign = 1
        
        if compression_positive:
            fsign = -1
        if not pullout_positive:
            dsign =- 1
        for loc in location:
            for phaseid in phase:
                idx2 = idx & (self._results['phase']==phaseid) * (self._results['location']==loc)
                u0 = 0
                if reset_start:
                    u0 = self._results.loc[idx2, 'uy'].to_numpy()[0]
                ax.plot(dsign * (self._results.loc[idx2, 'uy'] - u0)  *100,
                        fsign * self._results.loc[idx2, 'fy'],
                        label='{} - {}'.format(loc, phaseid))
        if legend:
            ax.legend()
        ax.set_ylabel('Axial force [kN]')
        ax.set_xlabel('Vertical displacement [cm]')
        ax.grid(alpha=0.2)
        plt.close(fig)
        return fig