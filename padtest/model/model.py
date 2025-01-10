from abc import ABC, abstractmethod
import copy
import numpy as np
import matplotlib.pyplot as plt
import numbers
import pandas as pd
import pickle
import sys

from padtest.material.plate import PlateMaterial
from padtest.material.soil import SoilMaterialSelector


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
    deformation_boundary_condition : dict, None, optional
        Deformation boundary conditions of the model. If None the
        default setting is adopted. Dictionary with keys `XMin`,
        `XMax`, `YMin` and `YMax`, with supported values
        'Free',  'Normally fixed',  'Horizontally fixed',
        'Vertically fixed' and 'Fully fixed'. By default None.
    dynamic_boundary_condtions : dict, None, optional
        Dynamic boundary conditions of the model used in dynamic load
        tests. If None the default setting is adopted. Dictionary
        with keys `XMin`, `XMax`, `YMin` and `YMax`, with supported
        values 'None' and 'Viscous'. By default None.
    shake_boundary_condtions : dict, None, optional
        Dynamic boundary conditions of the model used in base shake
        tests. If None the default setting is adopted. Dictionary
        with keys `XMin`, `XMax`, `YMin` and `YMax`, with supported
        values 'None', 'Viscous', 'Free-field' and 'Compliant base'.
        By default None.

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
    failure_test(testid, load, max_load=[np.inf, np.inf, np.inf], load_factor=2, load_increment=[0, 0, 0], qsurf=None, start_from='construction', delete_fail=True)
        Test the foundation until the model does not converge.
    load_test(testid, load, start_from='construction', qsurf=None, delete_fail=True)
        Conducts a load test in the model.
    safety_test(testid, start_from, test='incremental', SumMsf=None, Msf=0.1, qsurf=None, delete_fail=True)
        Conducts a safety test on the model.
    dynamic_test(testid, time, load, start_from='construction', nsubstep=10, qsurf=None, delete_fail=True)
        Apply a dynamic load to the foundation.
    shake_test(testid, time, acceleration, start_from='construction', qsurf=None, nsubstep=10, delete_fail=True)
        Apply a displacement time history at the model base.
    delete_test( testid, delete_fail=True) 
        Deletes a test from the model.
    plot_test(testid, force=None, displacement=None, phase=None, location=None, compression_positive=True, pullout_positive=False, reset_start=False, legend=False, xlim=None, ylim=None, figsize=(4, 3))
        Plots test results.
    plot_safety_test(testid, location=None, pullout_positive=False, reset_start=False, legend=False, figsize=(6, 4))
        Plots safety test.
    plot_dynamic_test(testid, displacement=None, force=None, location=None, compression_positive=True, pullout_positive=False, xlim=None, ylim=None, legend=False, figsize=(8, 2))
        Plot dynamic test resutls versus time.
    plot_shake_test(self, testid, displacement=None, acceleration=None, location=None, pullout_positive=False, xlim=None, ylim=None, legend=False, figsize=(8, 2))
        Plot shake test results versus time.
    """

    def __init__(self, s_i, g_i, g_o, model_type, element_type, title,
                 comments, soil, fill, ratchetting_material,
                 ratchetting_threshold, mesh_density, locations, excavation,
                 deformation_boundary_condition=None,
                 dynamic_boundary_condtions=None, 
                 shake_boundary_condtions=None, boundary_interface=False,
                 license='ultimate'):
        """Initialize a new instance of `Model`.

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
        deformation_boundary_condition : dict, None, optional
            Deformation boundary conditions of the model. If None the
            default setting is adopted. Dictionary with keys `XMin`,
            `XMax`, `YMin` and `YMax`, with supported values
            'Free',  'Normally fixed',  'Horizontally fixed',
            'Vertically fixed' and 'Fully fixed'. By default None.
        dynamic_boundary_condtions : dict, None, optional
            Dynamic boundary conditions of the model used in dynamic load
            tests. If None the default setting is adopted. Dictionary
            with keys `XMin`, `XMax`, `YMin` and `YMax`, with supported
            values 'None' and 'Viscous'. By default None.
        shake_boundary_condtions : dict, None, optional
            Dynamic boundary conditions of the model used in base shake
            tests. If None the default setting is adopted. Dictionary
            with keys `XMin`, `XMax`, `YMin` and `YMax`, with supported
            values 'None', 'Viscous', 'Free-field' and 'Compliant base'.
            By default None.
        boundary_interface : bool, optional
            Include boundary interfaces needed for a base shake test.
            This requires a much denser mesh and more computationally
            demanding models. By default False.
        license : str
            Plaxis lincese: 'advanced' or 'ultimate'. By default 'ultimate'.
        """
        self._s_i = s_i
        self._g_i = g_i
        self._g_o = g_o
        self._license = license
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
        self._init_boundary_conditions(deformation_boundary_condition, dynamic_boundary_condtions, shake_boundary_condtions, boundary_interface)
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
            strata['Identification'] = label
            self._soil_material[label] = copy.deepcopy(strata)

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
            mat['Identification'] = label
            self._soil_material[label] = copy.deepcopy(mat)

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
        ratchetting_material['Identification'] = 'ratchetting'
        self._soil_material['ratchetting'] = copy.deepcopy(ratchetting_material)
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
                                           'time', 'sumMstage', 'SumMsf', 'uy',
                                           'ux', 'Fy', 'Fx', 'M', 'qy0', 'qy1',
                                           'qx', 'agx', 'agy',
                                           'Fy target', 'Fx target',
                                           'M target', 'ratchetting'])
        self._results = results_df
        self._ophases = {}
        locations = np.array(locations)
        if self._b2 == 0:
            locations = locations[locations>=0]
        elif self._b2 == self._b:
            locations = locations[locations<=0]
        self._output_location = locations
        self._output_location_xcoord = (self._b * (self._output_location>0) - self._b2) * np.abs(self._output_location)
        self._output_point = {}

    def _init_boundary_conditions(self, deformation_boundary_condition,
                                  dynamic_boundary_condtions,
                                  shake_boundary_condtions, boundary_interface):
        """Initializes the boundary conditions.

        Parameters
        ----------
        deformation_boundary_condition : dict, None
            Deformation boundary conditions of the model. If None the
            default setting is adopted. Dictionary with keys `XMin`,
            `XMax`, `YMin` and `YMax`, with supported values
            'Free',  'Normally fixed',  'Horizontally fixed',
            'Vertically fixed' and 'Fully fixed'. 
        dynamic_boundary_condtions : dict, None
            Dynamic boundary conditions of the model used in dynamic load
            tests. If None the default setting is adopted. Dictionary
            with keys `XMin`, `XMax`, `YMin` and `YMax`, with supported
            values 'None' and 'Viscous'.
        shake_boundary_condtions : dict, None
            Dynamic boundary conditions of the model used in base shake
            tests. If None the default setting is adopted. Dictionary
            with keys `XMin`, `XMax`, `YMin` and `YMax`, with supported
            values 'None', 'Viscous', 'Free-field' and 'Compliant base'.
        boundary_interface : bool
            Include boundary interfaces needed for a base shake test.
            This requires a much denser mesh and more computationally
            demanding models.

        Raises
        ------
        RuntimeError
            Wrong deformation boundary id.
        RuntimeError
            Unsuported deformation boundary condition.
        RuntimeError
            Wrong dynamic boundary id.
        RuntimeError
            Unsuported dynamic boundary condition.
        RuntimeError
            Wrong shake boundary id.
        RuntimeError
            Unsuported shake boundary condition.
        """
        # Deformation
        self._deformation_bc = copy.deepcopy(self._DEFAULT_DEFORMATION_BC)
        if isinstance(deformation_boundary_condition, dict):
            supported = ["Free",  "Normally fixed",  "Horizontally fixed", "Vertically fixed", "Fully fixed"]
            for boundary in deformation_boundary_condition:
                if boundary not in self._deformation_bc:
                    msg = ("Boundary <{}> not supported in deformation "
                           "boundary conditions. Supported values are: "
                           "'XMin', 'XMax', 'YMin' and 'YMax'.")
                    msg = msg.format(boundary)
                    raise RuntimeError(msg)
                if deformation_boundary_condition[boundary] not in supported:
                    msg = ("Deformation boundary condition <{}> not supported. "
                           "Suported values are: {}.")
                    msg = msg.format(deformation_boundary_condition[boundary], ','.join(supported))
                self._deformation_bc[boundary] = deformation_boundary_condition[boundary]
        
        # Dynamic
        self._dynamic_bc = copy.deepcopy(self._DEFAULT_DYNAMIC_BC)
        if isinstance(dynamic_boundary_condtions, dict):
            supported = ["None",  "Viscous"]
            for boundary in dynamic_boundary_condtions:
                if boundary not in self._dynamic_bc:
                    msg = ("Boundary <{}> not supported in dynamic "
                           "boundary conditions. Supported values are: "
                           "'XMin', 'XMax', 'YMin' and 'YMax'.")
                    msg = msg.format(boundary)
                    raise RuntimeError(msg)
                if dynamic_boundary_condtions[boundary] not in supported:
                    msg = ("Dynamic boundary condition <{}> not supported. "
                           "Suported values are: {}.")
                    msg = msg.format(dynamic_boundary_condtions[boundary], ','.join(supported))
                self._dynamic_bc[boundary] = dynamic_boundary_condtions[boundary]

        # Shake
        self._shake_bc = copy.deepcopy(self._DEFAULT_SHAKE_BC)
        if isinstance(shake_boundary_condtions, dict):
            supported = ["None",  "Viscous", "Free-field"]
            for boundary in shake_boundary_condtions:
                if boundary not in self._shake_bc:
                    msg = ("Boundary <{}> not supported in shake "
                           "boundary conditions. Supported values are: "
                           "'XMin', 'XMax', 'YMin' and 'YMax'.")
                    msg = msg.format(boundary)
                    raise RuntimeError(msg)
                if shake_boundary_condtions[boundary] not in supported:
                    msg = ("Shake boundary condition <{}> not supported. "
                           "Suported values are: {}.")
                    msg = msg.format(shake_boundary_condtions[boundary], ','.join(supported))
                self._shake_bc[boundary] = shake_boundary_condtions[boundary]
        self._boundary_interface_flag = boundary_interface

    def _set_model(self):
        """General model settings.
        """
        self._s_i.new()
        self._g_i.SoilContour.initializerectangular(self._xlim[0], self._ylim[0], self._xlim[1], self._ylim[1])
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
        
        self._interfaces.build_geometry(self._g_i)

        if self._boundary_interface_flag:
            self._boundary_interface = []
            self._boundary_interface.append(self._g_i.neginterface((self._xlim[1], self._ylim[1]), (self._xlim[1], self._ylim[0])))
            self._boundary_interface.append(self._g_i.neginterface((self._xlim[1], self._ylim[0]), (self._xlim[0], self._ylim[0])))
            self._boundary_interface.append(self._g_i.neginterface((self._xlim[0], self._ylim[0]), (self._xlim[0], self._ylim[1]))) 

            self._acceleration = self._g_i.linedispl((self._xlim[0], self._ylim[0]), (self._xlim[1], self._ylim[0]))
    
    def _build_materials(self):
        """Creates soil and plate materials in the model.
        """
        for matid in self._soil_material:
            self._soil_material_plx[matid] = SoilMaterialSelector.create_material(self._g_i, copy.deepcopy(self._soil_material[matid]), self._license)
        for matid in self._plate_material:
            self._plate_material_plx[matid] = PlateMaterial.create_material(self._g_i, copy.deepcopy(self._plate_material[matid]), self._license)
        self._interfaces.build_material(self._g_i, self._license)

    @abstractmethod
    def _build_load(self):
        return NotImplementedError
    
    @abstractmethod
    def _build_surface_load(self):
        return NotImplementedError
    
    def _build_mesh(self):
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
        self._set_deformation_boundary_conditions()

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

        self._interfaces.activate(self._g_i)
    
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
        self._set_deformation_boundary_conditions()

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

        self._interfaces.activate(self._g_i)

        if fill and self._fill is not None:
            for strata_idx, poly_idxs in self._fill.items():
                for poly_idx in poly_idxs:
                    self._set_soil_material(self._g_i, poly_idx + 1, 2, 'fill_{:.0f}'.format(strata_idx + 1))
        
        # construction phase
        self._iphases['construction'] = self._g_i.phase(self._iphases['Initial Phase'])
        self._iphases['construction'].Identification = "construction"
        self._g_i.Model.CurrentPhase = self._iphases['construction']
        self._g_i.set(self._g_i.Model.CurrentPhase.MaxStepsStored, 1000)

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
        
        sumMstage, Uy, Ux = self._extract_initial_phase_results(phaseid, nstep)
        
        # ad results to dataframe
        for locidx, loc in enumerate(self._output_point):
            df = pd.DataFrame({'test':[None] * nstep,
                               'phase':[self._iphases[phase].Identification.value] * nstep,
                               'previous':[None] * (nstep),
                               'plx id':[self._iphases[phase].Name.value] * nstep,
                               'previous plx id':[None] * nstep,
                               'location': [loc] * nstep,
                               'step': np.linspace(1, nstep, nstep),
                               'time': [None] * nstep,
                               'sumMstage':sumMstage, 
                               'SumMsf': [None] * nstep,
                               'uy': Uy[locidx, :],
                               'ux': Ux[locidx, :],
                               'Fy': [0] * nstep,
                               'Fx': [0] * nstep,
                               'M': [0] * nstep,
                               'qy0': [0] * nstep,
                               'qy1': [0] * nstep,
                               'qx': [0] * nstep,
                               'agx':[0] * nstep,
                               'agy':[0] * nstep,
                               'Fy target': [0] * nstep,
                               'Fx target':[0] * nstep,
                               'M target': [0] * nstep,                            
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

    def _load_format(self, load):
        """Format input load.

        Parameters
        ----------
        load : array-like, numeric
            (3,) array-like with (Fy, Fx, M) applied to the foundaiton.
            Numeric value is assumed as Fy, returning (Fy, 0, 0).
            Symmetric foundations only allow for numeric values.

        Returns
        -------
        np.ndarray
            (3,)  (Fy, Fx, M) applied to the foundaiton.

        Raises
        ------
        RuntimeError
            Non-numeric load value in symmetric foundation.
        """
        if self._symmetric and not isinstance(load, numbers.Number):
            if load[1] != 0  and load[2] != 0:
                msg = 'Symmetric models only allow for vertical loads.'
                raise RuntimeError(msg)
            return np.array(load)
        if isinstance(load, numbers.Number):
            return np.array([load, 0, 0])
        return load

    def _get_phase_load(self, phaseid, when, target=False):
        """Retrieves the start or end load of a calcualted phase from
        the results.

        Parameters
        ----------
        phaseid : str
            Phase id
        when : str
            'start' or 'end'.
        target : bool, optinal
            Get target load values, instead of applied load inferred
            from Plaxis output. By default False.  

        Returns
        -------
        np.ndarray
            (3,) load applied at the end of the phase (Fy, Fx, M).
        """
        idx = self._results['phase'] == phaseid
        locs = self._results.loc[idx, 'location'].unique()
        idx = idx & (self._results['location'] == locs[0])

        if when=='end':
            idx = np.max(self._results.loc[idx].index.to_numpy())
        elif when=='start':
            idx = np.min(self._results.loc[idx].index.to_numpy())
        
        if target:
            load = [self._results.loc[idx, 'Fy target'],
                    self._results.loc[idx, 'Fx target'],
                    self._results.loc[idx, 'M target']]
        else:
            load = [self._results.loc[idx, 'Fy'],
                    self._results.loc[idx, 'Fx'],
                    self._results.loc[idx, 'M']]
        return np.array(load)

    def _set_deformation_boundary_conditions(self):
        """Sets deformation conditions in the current phase.
        """
        self._g_i.set(self._g_i.Deformations.BoundaryXMin, self._g_i.Model.CurrentPhase,  self._deformation_bc['XMin'])
        self._g_i.set(self._g_i.Deformations.BoundaryXMax, self._g_i.Model.CurrentPhase,  self._deformation_bc['XMax'])
        self._g_i.set(self._g_i.Deformations.BoundaryYMin, self._g_i.Model.CurrentPhase,  self._deformation_bc['YMin'])
        self._g_i.set(self._g_i.Deformations.BoundaryYMax, self._g_i.Model.CurrentPhase,  self._deformation_bc['YMax'])

    def _set_dynamic_test_phase(self, testid, time, start_phaseid, nsubstep, shake):
        """Set up a dynamic design phase in the model

        Parameters
        ----------
        testid : str
            Test id.
        time : np-array
            (nt,) time array.
        start_phaseid : str
            Id of the test start phase.
        nsubstep : int
            Substests in each time step.
        shake : bool
            True if base shake test.
        """
        self._iphases[testid] = self._g_i.phase(self._iphases[start_phaseid])
        self._iphases[testid].Identification = testid
        self._g_i.Model.CurrentPhase = self._iphases[testid]
        self._g_i.set(self._g_i.Model.CurrentPhase.DeformCalcType, "Dynamic")
        self._g_i.set(self._g_i.Model.CurrentPhase.Deform.TimeIntervalSeconds, time[-1])
        self._g_i.set(self._g_i.Model.CurrentPhase.Deform.UseDefaultIterationParams, False)
        self._g_i.set(self._g_i.Model.CurrentPhase.Deform.TimeStepDetermType, "Manual")
        self._g_i.set(self._g_i.Model.CurrentPhase.Deform.MaxSteps, len(time))
        self._g_i.set(self._g_i.Model.CurrentPhase.Deform.SubSteps, nsubstep)
        self._g_i.set(self._g_i.Model.CurrentPhase.MaxStepsStored, len(time))

        if shake:
            self._g_i.set(self._g_i.Dynamics.BoundaryXMin, self._g_i.Model.CurrentPhase,  self._shake_bc['XMin'])
            self._g_i.set(self._g_i.Dynamics.BoundaryXMax, self._g_i.Model.CurrentPhase,  self._shake_bc['XMax'])
            self._g_i.set(self._g_i.Dynamics.BoundaryYMax, self._g_i.Model.CurrentPhase,  self._shake_bc['YMax'])
            self._g_i.set(self._g_i.Dynamics.BoundaryYMin, self._g_i.Model.CurrentPhase,  self._shake_bc['YMin'])
        else:
            self._g_i.set(self._g_i.Dynamics.BoundaryXMin, self._g_i.Model.CurrentPhase,  self._dynamic_bc['XMin'])
            self._g_i.set(self._g_i.Dynamics.BoundaryXMax, self._g_i.Model.CurrentPhase,  self._dynamic_bc['XMax'])
            self._g_i.set(self._g_i.Dynamics.BoundaryYMax, self._g_i.Model.CurrentPhase,  self._dynamic_bc['YMax'])
            self._g_i.set(self._g_i.Dynamics.BoundaryYMin, self._g_i.Model.CurrentPhase,  self._dynamic_bc['YMin'])
        
    def _get_start_phase(self, start):
        """Get the phase id to be used as the start conditions for
        a new load test.

        Parameters
        ----------
        start : str, tuple
            'construction', 'excavation', Plaxis phase id or test id
            used as the start conditions for a new test. If a test with
            multiple stages is requested, the last test phase is
            selected. Specific test stages are selected by providing a
            tuple (test id, stage number), where the phase number is an
            integer starting from 0. Failure and safety tests cannot be
            used start configurations.

        Returns
        -------
        str
            Phase id.

        Raises
        ------
        RuntimeError
            Start phase or test not available.
        RuntimeError
            Failure or safety test requested as start configurations.
        RuntimeError
            Start test not available.
        RuntimeError
            Failure or safety test requested as start configurations.
        RuntimeError
            Wrong stage input type. 
        RuntimeError
            Stage not available in test.
        RuntimeError
            Wrong input format.
        """
        if isinstance(start, str):
            if start in self._iphases and start not in self._test_log:
                return start
            if start in self._test_log:
                if self._test_log[start] in ['failure', 'safety incremental', 'safety target']:
                    raise RuntimeError('Failure and safety tests cannot be used as start configurations.')
                phaseid = self._test_log[start]['phase'][-1]
                return phaseid
            else:
                raise RuntimeError('Requested start phase or test <{}> not available.'.format(start))
        elif isinstance(start, tuple):
            testid = start[0]
            phaseid = start[1]
            if testid not in self._test_log:
                raise RuntimeError('Requested start test <{}> not available.'.format(testid))
            if self._test_log[testid] in ['failure', 'safety incremental', 'safety target']:
                raise RuntimeError('Failure and safety tests cannot be used as start configurations.')
            if not isinstance(phaseid, int):
                raise RuntimeError('A stage within a test must be specified by its number as an integer.')
            phaseid = "{}_stage_{:.0f}".format(testid, phaseid)
            if phaseid not in self._test_log[testid]['phase']:
                raise RuntimeError('Requested start stage <{}> not available in test <{}>.'.format(phaseid, testid))
            return phaseid
        msg = "Test start phase must be specified as a test id string, or a tuple (test id, stage number)."
        raise RuntimeError(msg)

    def _calculate_surface_load(self, testid, qsurf, start_phaseid, delete_phases): 
        """Calcualtes the surface load stage.

        Parameters
        ----------
        testid : str
            Test id.
        qsurf : numeric, None
            Surface load.
        start_phaseid : str
            Id of the test start phase.
        delete_phases : bool, optional
            Deletes test phases from model if there is a calculation
            error, by default True.

        Returns
        -------
        str
            Id of the test start phase.
        """
        if qsurf is None:
            return start_phaseid
        phaseid = testid + '_qsurf'
        self._test_log[testid]['phase'].append(phaseid)
        self._iphases[phaseid] = self._g_i.phase(self._iphases[start_phaseid])
        self._iphases[phaseid].Identification = phaseid

        self._g_i.Model.CurrentPhase = self._iphases[phaseid]
        self._g_i.set(self._g_i.Model.CurrentPhase.MaxStepsStored, 1000)
        self._set_surface_load(qsurf)
        status = self._g_i.calculate(self._g_i.Model.CurrentPhase)
        self._check_phase_status(status, testid, phaseid, delete_phases)
        self._set_phase_results(testid, phaseid, start_phaseid, [0, 0, 0])
        
        return phaseid

    def _calculate_load_phase(self, testid, phaseid, prevphaseid, load, ratchetting):
        """Computes a phase in a load test.

        Parameters
        ----------
        testid : str
            Test id.
        phaseid : str
            Phase id
        prevphaseid : str
            Id of the previous phase.
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
        
        self._set_load(load)
        status = self._g_i.calculate(self._g_i.Model.CurrentPhase)
        return status

    @abstractmethod
    def _set_dynamic_load(self, time, load):
        """Sets dynamic load."""
        return NotImplementedError
    
    @abstractmethod
    def _calculate_dynamic_load_phase(self, time, load):
        """Calcualtes a dynamic load phase."""
        return NotImplementedError
    
    @abstractmethod
    def _set_dynamic_load_result(self, testid, time, load):
        """Adds dynamic load values to results dataframe."""
        return NotImplementedError

    @abstractmethod
    def _set_load(self, load):
        """Sets load value in the current phase.

        Parameters
        ----------
        load : float, array-like
            (3,) Fy, Fx and M [kN]. If float, the value is assuemd to be
            Fy and Fx and M are set to 0.
        """
        return NotImplementedError
    
    @abstractmethod
    def _set_surface_load(self, qsurf):
        """Activates and sets a value to the surface load in the
        curernt phase. 

        Parameters
        ----------
        qsurf : numeric
            Surface load.
        """
        return NotImplementedError

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
            Id of the previous phase.
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

    @abstractmethod
    def _set_phase_results(self, testid, phaseid, prevphaseid, load):
        """Adds phase results to the results dataframe.

        Parameters
        ----------
        testid : str
            Test id.
        phaseid : str
            Phase id
        prevphaseid : str
            Id of the previous phase.
        load : np.ndarray
            (3,) load applied at the end of the phase (Fy, Fx, M).
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
    @property
    def results(self):
        """Calculation results.

        Renturs
        -------
        pd.DataFrame
            Calculation results.
        """
        return self._results

    def build(self):
        """Builds the model in Plaxis.
        """
        self._set_model()
        self._build_geometry()
        self._build_materials()
        self._build_load()
        self._build_surface_load()
        self._build_mesh()
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
        for testid, test in test_log.items():
            if test['type'] == 'load':
                self.load_test(test['id'], test['load'], start_from=test['start phaseid'], qsurf=test['qsurf'])
            elif test['type'] == 'failure':
                self.failure_test(test['id'], test['load'],
                                  max_load=test['max_load'], start_load=test['start_load'],
                                  load_factor=test['load_factor'], load_increment=test['load_increment'],
                                  start_from=test['start phaseid'], qsurf=test['qsurf'])
            elif test['type'] == 'safety incremental':
                self.safety_test(test['id'], test['start phaseid'], test='incremental', Msf=test['Msf'], qsurf=test['qsurf'])
            elif test['type'] == 'safety target':
                self.safety_test(test['id'], test['start phaseid'], test='target', SumMsf=test['SumMsf'], qsurf=test['qsurf'])
            elif test['type'] == 'dynamic':
                self.dynamic_test(test['id'], test['time'], test['load'], start_from=test['start phaseid'], qsurf=test['qsurf'], nsubstep=test['nsubstep'])
            elif test['type'] == 'shake':
                self.shake_test(test['id'], test['time'], test['load'], start_from=test['start phaseid'], qsurf=test['qsurf'], nsubstep=test['nsubstep'])

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
        self._interfaces.remove_plaxis_objects()
        self._load = None
        self._mesh = None
        self._surface_load = None
        self._output_point = {}
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

    def load_test(self, testid, load, start_from='construction', qsurf=None, 
                  delete_fail=True):
        """Conducts a load test in the model.

        Parameters
        ----------
        testid : str
            Test id.
        load : numeric, array-like
            (nl, ncomp) Loads applied in each phase of the test [kN].
            Each load can be an array-like with (Fy, Fx, M) applied to
            the foundaiton or a numeric value wich is assue as Fy, with
            Fx and M being zero. Symmetric foundations only allow for
            vertical loading, thus the load must be a (n1, 1) array or
            a numeric value. For a single load phase with the 3 load
            components, the load should be specified as [[Fy, Fx, M]].
        start_from : str, tuple, optional
            'construction', 'excavation', Plaxis phase id or test id
            used as the start conditions for a new test. If a test with
            multiple stages is requested, the last test phase is
            selected. Specific test stages are selected by providing a
            tuple (test id, stage number), where the phase number is an
            integer starting from 0. Failure and safety tests cannot be
            used start configurations. By default 'construction'.
        qsurf : numeric, None, optional
            Vertical surface load. By default None.
        delete_fail : bool, optional
            Deletes test phases from model if there is a calculation
            error, by default True.

        Raises
        ------
        RuntimeError
            Duplicated test id.
        """
    
        if isinstance(load, numbers.Number):
            load = [load]
        load = [self._load_format(l) for l in load]
        
        start_phaseid = self._get_start_phase(start_from)
        if testid in self._test_log.keys():
            raise RuntimeError('Duplicated test id <{}>.'.format(testid))
        self._test_log[testid] = {}
        self._test_log[testid]['id'] = testid
        self._test_log[testid]['type'] = 'load'
        self._test_log[testid]['load'] = load
        self._test_log[testid]['phase'] = []
        self._test_log[testid]['qsurf'] = qsurf
        self._test_log[testid]['start phaseid'] = copy.deepcopy(start_phaseid)
        
        start_phaseid = self._calculate_surface_load(testid, qsurf, start_phaseid, delete_fail)
        
        test_phases = [testid + '_stage_{:.0f}'.format(idx) for idx in range(len(load))]
        previous_phase = [start_phaseid] + test_phases[:-1]
        ratchetting = False
        for load_value, phaseid, prevphaseid in zip(load, test_phases, previous_phase):
            status = self._calculate_load_phase(testid, phaseid, prevphaseid,
                                                load_value, ratchetting)
            self._check_phase_status(status, testid, phaseid, delete_fail)
            self._set_phase_results(testid, phaseid, prevphaseid, load_value)
            ratchetting = self._check_ratchetting(testid, phaseid, ratchetting)
    
    def failure_test(self, testid, load, max_load=[np.inf, np.inf, np.inf],
                     load_factor=2, load_increment=[0, 0, 0], qsurf=None,
                     start_from='construction', delete_fail=True):
        """Test the foundation until the model does not converge. A
        first trial is done using the start_load value. If lack of
        convergence is not achieved, the load is incremented as: 

        load = load_factor * load + load_increment.

        Parameters
        ----------
        testid : str
            Test id.
        load : numeric, array-like, optional
            (3,) Initial load applied to the model (Fy, Fx, M). Numeric
            input is assue as Fy , with Fx and M being zeros. Symmetric
            foundations only allow for vertical loading.
        max_load : numeric, array-like, optional
            (3,) maximum load to be applied to the model (Fy, Fx, M) in
            absolute value. Numeric input is assue as Fy , with Fx and M
            being infinity. By default [inf, inf, inf].
        load_factor : numeric, optional
            Multiplicative factor applied to the previous load when
            iteration is required. By default 2.
        load_increment : array-like, optional
            (3,) load increment applied to the previous load when
            iteration is required (Fy, Fx, M). By default [0, 0, 0].
        qsurf : numeric, None, optional
            Vertical surface load. By default None.
        start_from : str, tuple, optional
            'construction', 'excavation', Plaxis phase id or test id
            used as the start conditions for a new test. If a test with
            multiple stages is requested, the last test phase is
            selected. Specific test stages are selected by providing a
            tuple (test id, stage number), where the phase number is an
            integer starting from 0. Failure and safety tests cannot be
            used start configurations. By default 'construction'.
        delete_fail : bool, optional
            Deletes surface load phase from model if there is a
            calculation error, by default True.

        Raises
        ------
        RuntimeError
            Duplicated test id.
        """
        start_phaseid = self._get_start_phase(start_from)
        load = self._load_format(load)
        load_increment = self._load_format(load_increment)
        if testid in self._test_log.keys():
            raise RuntimeError('Duplicated test id <{}>.'.format(testid))
        self._test_log[testid] = {}
        self._test_log[testid]['id'] = testid
        self._test_log[testid]['type'] = 'failure'
        self._test_log[testid]['load'] = copy.deepcopy(load)
        self._test_log[testid]['load_factor'] = load_factor
        self._test_log[testid]['load_increment'] = copy.deepcopy(load_increment)
        self._test_log[testid]['phase'] = []
        self._test_log[testid]['start phaseid'] = copy.deepcopy(start_phaseid)
        self._test_log[testid]['max_load'] = max_load
        self._test_log[testid]['qsurf'] = qsurf
        

        start_phaseid = self._calculate_surface_load(testid, qsurf, start_phaseid, delete_fail)

        phaseid = testid
        status = 'OK'
        status = self._calculate_load_phase(testid, phaseid, start_phaseid, load, False)
        while status == 'OK' and not any(np.greater_equal(np.abs(load), max_load)):
            for phase in self._g_i.phases:
                if phase.Identification.value == phaseid:
                    self._g_i.delete(phase)
            _ = self._iphases.pop(phaseid)
            self._test_log[testid]['phase'] = []
            load = load_factor * load + load_increment
            status = self._calculate_load_phase(testid, phaseid, start_phaseid, load, False)
        self._g_i.view(self._g_i.Model.CurrentPhase)
        self._ophases[phaseid] = self._g_o.phases[-1]
        self._set_phase_results(testid, phaseid, start_phaseid, load)

    def safety_test(self, testid, start_from, test='incremental', SumMsf=None,
                    Msf=0.1, qsurf=None, delete_fail=True):
        """Conducts a safety test on the model.

        Parameters
        ----------
        testid : str
            Test id.
        start_from : str, tuple
            'construction', Plaxis phase id or test id used as the start
            conditions for a new test. If a test with multiple stages is
            requested, the last test phase is selected. Specific test
            stages are selected by providing a tuple (test id, stage number),
            where the phase number is an integer starting from 0.
            Failure and safety tests cannot be used start
            configurations.
        test : str, optional
            Safety test type: 'incremental' or 'target'. By default
            'incremental'.
        SumMsf : float, optional
            Strength reduction factor target value in a target test. By
            default None.
        Msf : float, optional
            Strength reduction factor ncrement in an incremental test.
            By default 0.1.
        qsurf : numeric, None, optional
            Vertical surface load. By default None.
        delete_fail : bool, optional
            Deletes surface load phase from model if there is a
            calculation error, by default True.

        Raises
        ------
        RuntimeError
            Duplicated test id
        RuntimeError
            Unsuported test type.
        RuntimeError
            SumMsf wrong type.
        RuntimeError
            SumMsf wrong type.
        """
        start_phaseid = self._get_start_phase(start_from)
        if testid in self._test_log.keys():
            raise RuntimeError('Duplicated test id <{}>.'.format(testid))
        if test not in ['incremental', 'target']:
            raise RuntimeError("Supported test types are 'incremental' and 'target'.")
        self._test_log[testid] = {}
        self._test_log[testid]['id'] = testid
        self._test_log[testid]['type'] = 'safety ' + test
        if test == 'target':
            if not isinstance(SumMsf, numbers.Number):
                raise RuntimeError('A numeric value must be provided for the target Msf <SumMsf>.')
            self._test_log[testid]['SumMsf'] = SumMsf
        else:
            if not isinstance(Msf, numbers.Number):
                raise RuntimeError('A numeric value must be provided for the Msf increase <Msf>.')
            self._test_log[testid]['Msf'] = Msf
        self._test_log[testid]['phase'] = []
        self._test_log[testid]['start phaseid'] = copy.deepcopy(start_phaseid)
        self._test_log[testid]['qsurf'] = qsurf
        

        start_phaseid = self._calculate_surface_load(testid, qsurf, start_phaseid, delete_fail)
        self._iphases[testid] = self._g_i.phase(self._iphases[start_phaseid])
        self._iphases[testid].Identification = testid

        self._g_i.Model.CurrentPhase = self._iphases[testid]
        self._g_i.set(self._g_i.Model.CurrentPhase.DeformCalcType, "Safety")
        self._g_i.set(self._g_i.Model.CurrentPhase.MaxStepsStored, 1000)
        if test == 'target':
            self._g_i.set(self._g_i.Model.CurrentPhase.Deform.LoadingType, "Target SumMsf")
            self._g_i.set(self._g_i.Model.CurrentPhase.Deform.Loading.SumMsf, SumMsf)
        else:
            self._g_i.set(self._g_i.Model.CurrentPhase.Deform.LoadingType, "Incremental multipliers")
            self._g_i.set(self._g_i.Model.CurrentPhase.Deform.Loading.Msf, Msf)
        _ = self._g_i.calculate(self._g_i.Model.CurrentPhase)
        self._g_i.view(self._g_i.Model.CurrentPhase)
        self._ophases[testid] = self._g_o.phases[-1]
        self._set_phase_results(testid, testid, start_phaseid, self._get_phase_load(start_phaseid, 'end', target=False))

    def dynamic_test(self, testid, time, load, start_from='construction',
                     nsubstep=10, qsurf=None, delete_fail=True):
        """Apply a dynamic load to the foundation.

        Parameters
        ----------
        testid : str
            Test id.
        time : array-like
            (nt,) time array.
        load : array-like
            (ncomp, nt) force array (Fy, Fx) for solid models or
            (Fx, Fy, M) for plate models.. If only Fy is provided, the
            other components are assumed as 0.
        start_from : str, tuple, optional
            'construction', 'excavation', Plaxis phase id or test id
            used as the start conditions for a new test. If a test with
            multiple stages is requested, the last test phase is
            selected. Specific test stages are selected by providing a
            tuple (test id, stage number), where the phase number is an
            integer starting from 0. Failure and safety tests cannot be
            used start configurations. By default 'construction'.
        nsubstep : int, optional
            Substests in each time step, by default 10.
        qsurf : numeric, None, optional
            Vertical surface load. By default None.
        delete_fail : bool, optional
            Deletes test phases from model if there is a calculation
            error, by default True.

        Raises
        ------
        RuntimeError
            Duplicated test id.
        """
        start_phaseid = self._get_start_phase(start_from)
        time, input_load, load = self._set_dynamic_load(time, load)
        
        if testid in self._test_log.keys():
            raise RuntimeError('Duplicated test id <{}>.'.format(testid))
        self._test_log[testid] = {}
        self._test_log[testid]['id'] = testid
        self._test_log[testid]['type'] = 'dynamic'
        self._test_log[testid]['time'] = time
        self._test_log[testid]['load'] = input_load
        self._test_log[testid]['nsubstep'] = nsubstep
        self._test_log[testid]['phase'] = []
        self._test_log[testid]['start phaseid'] = copy.deepcopy(start_phaseid)
        self._test_log[testid]['qsurf'] = qsurf

        start_phaseid = self._calculate_surface_load(testid, qsurf, start_phaseid, delete_fail)
        
        self._set_dynamic_test_phase(testid, time, start_phaseid, nsubstep, False)

        status = self._calculate_dynamic_load_phase(time, load)
        self._check_phase_status(status, testid, testid, delete_fail)
        self._set_phase_results(testid, testid, start_phaseid, [0, 0, 0])
        self._set_dynamic_load_result(testid, time, load)

    def shake_test(self, testid, time, acceleration, start_from='construction',
                   qsurf=None, nsubstep=10, delete_fail=True):
        """Apply a displacement time history at the model base.

        Parameters
        ----------
        testid : str
            Test id.
        time : array-like
            (nt,) time array.
        acceleration : array-like
            (ncomp, nt) displacement time history (ux, uy). If a 1D
            array (nt,) is provided it is adopted as ux and is assumed
            that uy = 0.
        start_from : str, tuple, optional
            'construction', 'excavation', Plaxis phase id or test id
            used as the start conditions for a new test. If a test with
            multiple stages is requested, the last test phase is
            selected. Specific test stages are selected by providing a
            tuple (test id, stage number), where the phase number is an
            integer starting from 0. Failure and safety tests cannot be
            used start configurations. By default 'construction'.
        nsubstep : int, optional
            Substests in each time step, by default 10.
        qsurf : numeric, None, optional
            Vertical surface load. By default None.
        delete_fail : bool, optional
            Deletes test phases from model if there is a calculation
            error, by default True.

        Raises
        ------
        RuntimeError
            Model lacks boundary interfaces.
        RuntimeError
            Duplicated test id.
        RuntimeError
            Time is not 1-dimensional.
        RuntimeError
            More than 10,000 time steps.
        RuntimeError
            Length of base displacement array does not match the time
            array.
        """
        if not self._boundary_interface_flag:
            msg = ("Boundary interfaces must be included in the model, set "
                   "the <boundary_interface> parameter to True at the model creation.")
            raise RuntimeError(msg)
        
        if testid in self._test_log.keys():
            raise RuntimeError('Duplicated test id <{}>.'.format(testid))
        
        time = np.array(time)
        if time.ndim != 1:
            raise RuntimeError('Time must be defined by a 1-dimensional array.')
        if len(time) > 10000:
            raise RuntimeError('Number of time steps must be <=10,000.')
        
        acceleration = np.array(acceleration)
        if acceleration.ndim == 1:
            acceleration = np.vstack([acceleration, np.zeros_like(acceleration)])
        if acceleration.shape[1] != len(time):
            msg = 'Base acceleration and time arrays must have the same length.'
            raise RuntimeError(msg)

        start_phaseid = self._get_start_phase(start_from)
        self._test_log[testid] = {}
        self._test_log[testid]['id'] = testid
        self._test_log[testid]['type'] = 'shake'
        self._test_log[testid]['time'] = time
        self._test_log[testid]['load'] = acceleration
        self._test_log[testid]['nsubstep'] = nsubstep
        self._test_log[testid]['phase'] = []
        self._test_log[testid]['start phaseid'] = copy.deepcopy(start_phaseid)
        self._test_log[testid]['qsurf'] = qsurf

        start_phaseid = self._calculate_surface_load(testid, qsurf, start_phaseid, delete_fail)
        
        self._set_dynamic_test_phase(testid, time, start_phaseid, nsubstep, True)
        
        accel_x = self._g_i.displmultiplier()
        self._g_i.set(accel_x.Signal, "Table")
        self._g_i.set(accel_x.DataType, "Accelerations")
        for idx, (t, accel) in enumerate(zip(time, acceleration[0])):
            accel_x.Table.add()
            self._g_i.set(accel_x.Table[idx].Time, t)
            self._g_i.set(accel_x.Table[idx].Multiplier, accel)
        
        accel_y = self._g_i.displmultiplier()
        self._g_i.set(accel_y.Signal, "Table")
        self._g_i.set(accel_y.DataType, "Accelerations")
        for idx, (t, accel) in enumerate(zip(time, acceleration[1])):
            accel_y.Table.add()
            self._g_i.set(accel_y.Table[idx].Time, t)
            self._g_i.set(accel_y.Table[idx].Multiplier, accel)

        self._g_i.activate(self._g_i.DynLineDisplacement_1_1, self._g_i.Model.CurrentPhase)
       
        self._g_i.set(self._g_i.DynLineDisplacement_1_1.Multiplierx, self._g_i.Model.CurrentPhase, accel_x)
        self._g_i.set(self._g_i.DynLineDisplacement_1_1.Multipliery, self._g_i.Model.CurrentPhase, accel_y)
        self._g_i.set(self._g_i.LineDisplacement_1_1.Displacement_x, self._g_i.Model.CurrentPhase, "Prescribed")
        self._g_i.set(self._g_i.LineDisplacement_1_1.Displacement_y, self._g_i.Model.CurrentPhase, "Prescribed")
        self._g_i.set(self._g_i.LineDisplacement_1_1.ux_start, self._g_i.Model.CurrentPhase, 1)
        self._g_i.set(self._g_i.LineDisplacement_1_1.uy_start, self._g_i.Model.CurrentPhase, 1)
        
        if not self._symmetric:
            self._g_i.activate(self._g_i.DynLineDisplacement_1_2, self._g_i.Model.CurrentPhase)
            self._g_i.set(self._g_i.DynLineDisplacement_1_2.Multiplierx, self._g_i.Model.CurrentPhase, accel_x)
            self._g_i.set(self._g_i.DynLineDisplacement_1_2.Multipliery, self._g_i.Model.CurrentPhase, accel_y)
            self._g_i.set(self._g_i.LineDisplacement_1_2.Displacement_x, self._g_i.Model.CurrentPhase, "Prescribed")
            self._g_i.set(self._g_i.LineDisplacement_1_2.Displacement_y, self._g_i.Model.CurrentPhase, "Prescribed")
            self._g_i.set(self._g_i.LineDisplacement_1_2.ux_start, self._g_i.Model.CurrentPhase, 1)
            self._g_i.set(self._g_i.LineDisplacement_1_2.uy_start, self._g_i.Model.CurrentPhase, 1)

        status = self._g_i.calculate(self._g_i.Model.CurrentPhase)
        self._check_phase_status(status, testid, testid, delete_fail)
        self._set_phase_results(testid, testid, start_phaseid, [0, 0, 0])
        idx = (self._results['test'] == testid)
        for loc in self._output_point.keys():
            idx2 = idx & (self._results['location']==loc)
            result_time = self._results.loc[idx2, 'time'].to_numpy(dtype='float64')
            self._results.loc[idx2, 'agx'] = np.interp(result_time, time, acceleration[0])
            self._results.loc[idx2, 'agy'] = np.interp(result_time, time, acceleration[1])

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
                        self._g_o.delete(phase)
            test_phases.reverse()
        for phaseid in test_phases:
            if phaseid in self._iphases:
                _ = self._iphases.pop(phaseid)
            if phaseid in self._ophases:
                _ = self._ophases.pop(phaseid)
        self._results = self._results[self._results['test']!=testid]
        self._results.reset_index(drop=True, inplace=True)

    def plot_test(self, testid, force=None, displacement=None,
                  phase=None, location=None, 
                  compression_positive=True, pullout_positive=False,
                  reset_start=False, legend=False, xlim=None, ylim=None,
                  figsize=(4, 3)):
        """Plots test results.

        Parameters
        ----------
        testid : str
            Test id.
        force : str, list, None, optional
            Force components to plot: 'Fy', 'Fx', 'M'. If None, default
            settings based on foundation type are adopted.
        displacement : str, list, None, optional
            Displacement components to plot: 'ux', 'uy'. If None,
            default settings based on foundation type are adopted.
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
        xlim : array-like, dict, None, optional
            If (2,) array then it is applied as the x axis limits to 
            all plots. Dictiornay with keys 'ux' and 'uy' with
            the desired limits for each displacement component. By
            default None.
        ylim : array-like, dict, None, optional
            If (2,) array then it is applied as the y axis limits to 
            all plots. Dictiornay with keys 'Fx', 'Fy' and 'M' with
            the desired limits for each force component. By default
            None.
        figsize : tuple, optional
            Figure size of a single plot. By default (4, 3).

        Returns
        -------
        Figure
            Figure with the test plot.

        Raises
        ------
        RuntimeError
            Invalid force component.
        RuntimeError
            Invalid displacement component.
        RuntimeError
            Test id not in restuls.
        RuntimeError
            Phase not in results.
        """
        if force is None and self._symmetric:
            force = 'Fy'
        elif force is None:
            force = ['Fy', 'Fx', 'M']
        if isinstance(force, str):
            force = [force]
        for f in force:
            if f not in ['Fx', 'Fy', 'M']:
                msg = ("Invalid force component <{}>. Supported values are "
                    "'Fy', 'Fx' and 'M'.")
                msg = msg.format(f)
                raise RuntimeError(msg)
        nf = len(force)

        if displacement is None and self._symmetric:
            displacement = 'uy'
        elif displacement is None:
            displacement = ['uy', 'ux']
        if isinstance(displacement, str):
            displacement = [displacement]
        for d in displacement:
            if d not in ['ux', 'uy']:
                msg = "Invalid displacement component <{}>. Supported values are 'ux' and 'uy'."
                msg = msg.format(d)
                raise RuntimeError(msg)
        nd = len(displacement)

        if self._model_type == 'planestrain':
            ylabel = {'Fx':'H [kN/m]', 'Fy': 'V [kN/m]', 'M':'M [kN/m/m]'}
        else:
            ylabel = {'Fx':'H [kN]', 'Fy': 'V [kN]', 'M':'M [kN/m]'}
        xlabel = {'ux': 'ux [cm]', 'uy': 'uy [cm]'}

        x_lim = {'ux':None, 'uy':None}
        if isinstance(xlim, dict):
            for key in x_lim:
                if key in xlim:
                    x_lim[key] = xlim[key]
        else:
            for key in x_lim:
                x_lim[key] = xlim

        y_lim = {'Fx':None, 'Fy':None, 'M':None}
        if isinstance(ylim, dict):
            for key in y_lim:
                if key in ylim:
                    y_lim[key] = ylim[key]
        else:
            for key in y_lim:
                y_lim[key] = ylim

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

        fsign = {'Fy':1, 'Fx':1, 'M':1}
        dsign = {'uy':1, 'ux':1}

        if compression_positive:
            fsign['Fy'] = -1
        if not pullout_positive:
            dsign['uy'] =- 1

        fig, axes = plt.subplots(nf, nd, figsize=(figsize[0] * nd, figsize[1] * nf))
        if nd ==1 and nf == 1:
            axes = np.array([[axes]])
        elif nd == 1:
            axes = np.array([axes]).T
        elif nf == 1:
            axes = np.array([axes])
        for idxf, f in enumerate(force):
            for idxd, d in enumerate(displacement): 
                ax = axes[idxf, idxd]
                for loc in location:
                    for phaseid in phase:
                        idx2 = idx & (self._results['phase']==phaseid) * (self._results['location']==loc)
                        u0 = 0
                        if reset_start:
                            u0 = self._results.loc[idx2, d].to_numpy()[0]
                        ax.plot(dsign[d] * (self._results.loc[idx2, d] - u0)  *100,
                                fsign[f] * self._results.loc[idx2, f],
                                label='{} - {}'.format(loc, phaseid))
                ax.set_xlim(x_lim[d])
                ax.set_ylim(y_lim[f])
                ax.grid(alpha=0.2)
                if legend:
                    ax.legend()
                axes[-1, idxd].set_xlabel(xlabel[d])
            axes[idxf, 0].set_ylabel(ylabel[f])
        plt.tight_layout()
        plt.close(fig)
        return fig
    
    def plot_safety_test(self, testid,  displacement=None, location=None, pullout_positive=False,
                         reset_start=False, legend=False,  xlim=None, ylim=None, figsize=(6, 4)):
        """Plots safety test

        Parameters
        ----------
        testid : str
            Test id.
        displacement : str, list, None, optional
            Displacement components to plot: 'ux', 'uy'. If None,
            default settings based on foundation type is adopted.
        location : str, float, optional
            Location. If None all locations are plotted. By default 
            None.
        pullout_positive : bool, optional
            Pull out displacement is plotted as positive. By default
            False.
        reset_start : bool, optional
            Resets the first point of the load-displacement curve to
            (0, 0). By default False
        legend : bool, optional
            Shows legend. By default False
        xlim : array-like
            Limit of the vertical axis of the plot.
        ylim : array-like, dict, None, optional
            If (2,) array then it is applied as the y axis limits to 
            all plots. Dictiornay with keys 'ux' and 'uy' with
            the desired limits for each displacement component. By
            default None.
        figsize : tuple, optional
            Figure size. By default (6, 4).

        Returns
        -------
        Figure
            Figure with the safety test plot.

        Raises
        ------
        RuntimeError
            Invalid displacement component.
        RuntimeError
            Test id not in restuls.
        RuntimeError
            Non safety test.
        """
        if displacement is None and self._symmetric:
            displacement = 'uy'
        elif displacement is None:
            displacement = ['uy', 'ux']
        if isinstance(displacement, str):
            displacement = [displacement]
        for d in displacement:
            if d not in ['ux', 'uy']:
                msg = "Invalid displacement component <{}>. Supported values are 'ux' and 'uy'."
                msg = msg.format(d)
                raise RuntimeError(msg)
        nd = len(displacement)

        ylabel = {'ux': 'ux [cm]', 'uy': 'uy [cm]'}

        y_lim = {'ux':None, 'uy':None}
        if isinstance(xlim, dict):
            for key in y_lim:
                if key in xlim:
                    y_lim[key] = ylim[key]
        else:
            for key in y_lim:
                y_lim[key] = ylim

        if testid not in self._results['test'].to_list():
            raise RuntimeError('Test <{}> not available in restuls.'.format(testid))
        if self._test_log[testid]['type'] not in ['safety incremental', 'safety target']:
            raise RuntimeError('Only safety tests can be plotted.')
        
        idx = self._results['test'] == testid

        if location is None:
            location = self._results[idx]['location'].unique()
        elif isinstance(location, (str, numbers.Number)):
            location = [location]

        dsign = {'uy':1, 'ux':1}
        if pullout_positive:
            dsign['uy'] =- 1

        fig, axes = plt.subplots(1, nd, figsize=(figsize[0], figsize[1] * nd))
        if nd==1:
            axes = [axes]
        
        for idxd, d in enumerate(displacement): 
            ax = axes[idxd]
            for loc in location:
                idx2 = (self._results['test']==testid) * (self._results['location']==loc)
                u0 = 0
                if reset_start:
                    u0 = self._results.loc[idx2, d].to_numpy()[0]
                ax.plot(self._results.loc[idx2, 'SumMsf'], 
                        dsign[d] * (self._results.loc[idx2, d] - u0) * 100,
                        label='{}'.format(loc))
            if legend:
                ax.legend()
            ax.set_xlabel(r"$\sum$Msf [ ]")
            ax.set_ylabel(ylabel[d])
            ax.set_xlim(xlim)
            ax.set_ylim(y_lim[d])
            ax.grid(alpha=0.2)
        plt.tight_layout()
        plt.close(fig)
        return fig

    def plot_dynamic_test(self, testid, displacement=None, force=None,
                          location=None, compression_positive=True,
                          pullout_positive=False, xlim=None, ylim=None,
                          legend=False, figsize=(8, 2)):
        """Plot dynamic test resutls versus time.

        Parameters
        ----------
        testid : str
            Test id.
        displacement : str, list, None, optional
            Displacement components to plot: 'ux', 'uy'. If None,
            default settings based on foundation type are adopted.
        force : str, list, None, optional
            Force components to plot: 'Fy', 'Fx', 'M'. If None, default
            settings based on foundation type are adopted.
        location : str, float, optional
            Location. If None all locations are plotted. By default 
            None.
        compression_positive : bool, optional
            Compresive force is plotted as positive. By default True.
        pullout_positive : bool, optional
            Pull out displacement is plotted as positive. By default
            False.
        xlim : array-like, None, optional
            (2,) limits of x axis. By default None.
        ylim : array-like, dict, None, optional
            If (2,) array then it is applied as the y axis limits to 
            all plots. Dictiornay with keys 'ux', 'uy', 'Fx', 'Fy' and
            'M' with the desired limits for each variable. By default
            None.
        legend : bool, optional
            Shows legend. By default False
        figsize : tuple, optional
            Figure size of a single plot. By default (8, 2).

        Returns
        -------
        Figure
            Figure with the test plot.

        Raises
        ------
        RuntimeError
            Invalid displacement component.
        RuntimeError
            Invalid force component.
        """

        if displacement is None and self._symmetric:
            displacement = 'uy'
        elif displacement is None:
            displacement = ['uy', 'ux']
        if isinstance(displacement, str):
            displacement = [displacement]
        for d in displacement:
            if d not in ['ux', 'uy']:
                msg = "Invalid displacement component <{}>. Supported values are 'ux' and 'uy'."
                msg = msg.format(d)
                raise RuntimeError(msg)
        nd = len(displacement)

        if force is None and self._symmetric:
            force = 'Fy'
        elif force is None and self._foundation_type == 'plate':
            force = ['Fy', 'Fx', 'M']
        elif force is None:
            force = ['Fy', 'Fx']
        if isinstance(force, str):
            force = [force]
        if self._foundation_type == 'plate':
            valid_forces = ['Fy', 'Fx', 'M']
        else:
            valid_forces = ['Fy', 'Fx']
        for f in force:
            if f not in valid_forces:
                msg = "Invalid force component <{}>. Supported values are {}."
                msg = msg.format(f, ', '.join(valid_forces))
                raise RuntimeError(msg)
        nf = len(force)        

        idx = self._results['test'] == testid
        if location is None:
            location = self._results[idx]['location'].unique()
        elif isinstance(location, (str, numbers.Number)):
            location = [location]


        if self._model_type == 'planestrain':
            axis_label = {'Fx':'H [kN/m]', 'Fy': 'V [kN/m]', 'M':'M [kN/m/m]'}
        else:
            axis_label = {'Fx':'H [kN]', 'Fy': 'V [kN]', 'M':'M [kN/m]'}
        axis_label = {**axis_label, **{'ux': 'ux [cm]', 'uy': 'uy [cm]'}}
        scale_factor = {'ux':100, 'uy':100, 'Fx':1, 'Fy':1, 'M':1}
        sign = {'ux':1, 'uy':1, 'Fx':1, 'Fy':1, 'M':1}
        if not pullout_positive:
            sign['uy'] = -1
        if compression_positive:
            sign['Fy'] = -1
            
        y_lim = {'ux':None, 'uy':None, 'Fx':None, 'Fy':None, 'M':None}
        if isinstance(ylim, dict):
            for key in y_lim:
                if key in ylim:
                    y_lim[key] = ylim[key]
        else:
            for key in y_lim:
                y_lim[key] = ylim
        
        
        fig, axes = plt.subplots(nd + nf, 1, figsize=(figsize[0], figsize[1] * (nd + nf)))
        for var, ax in zip(displacement + force, axes):
            if var in valid_forces:
                idx2 = idx & (self._results['location']=='top')
                ax.plot(self._results.loc[idx2, 'time'],
                        self._results.loc[idx2, var] * scale_factor[var] * sign[var])
            else:
                for loc in location:
                    idx2 = idx & (self._results['location']==loc)
                    ax.plot(self._results.loc[idx2, 'time'],
                            self._results.loc[idx2, var] * scale_factor[var] * sign[var],
                            label=loc)
                if legend:
                    ax.legend()
            ax.set_xlim(xlim)
            ax.set_ylim(y_lim[var])
            ax.set_ylabel(axis_label[var])
            ax.grid(alpha=0.2)
        axes[-1].set_xlabel('time [s]')
        plt.tight_layout()
        plt.close(fig)
        return fig

    def plot_shake_test(self, testid, displacement=None, acceleration=None,
                          location=None, pullout_positive=False,
                          xlim=None, ylim=None, legend=False, figsize=(8, 2)):
        """Plot shake test results versus time.

        Parameters
        ----------
        testid : str
            Test id.
        displacement : str, list, None, optional
            Displacement components to plot: 'ux', 'uy'. If None,
            default settings based on foundation type is adopted.
        acceleration : str, list, None, optional
            Base acceleration components to plot: 'agx', 'agy'. If None
            both are plotted. By default None.
        location : str, float, optional
            Location. If None all locations are plotted. By default 
            None.
        pullout_positive : bool, optional
            Pull out displacement is plotted as positive. By default
            False.
        xlim : array-like, None, optional
            (2,) limits of x axis. By default None.
        ylim : array-like, dict, None, optional
            If (2,) array then it is applied as the y axis limits to 
            all plots. Dictiornay with keys 'ux', 'uy', 'agx' and 'agy'
            with the desired limits for each variable. By default
            None.
        legend : bool, optional
            Shows legend. By default False
        figsize : tuple, optional
            Figure size of a single plot. By default (4, 3).

        Returns
        -------
        Figure
            Figure with the test plot.

        Raises
        ------
        RuntimeError
            Invalid displacement component.
        RuntimeError
            Invalid bace acceleration component.
        """

        if displacement is None and self._symmetric:
            displacement = 'uy'
        elif displacement is None:
            displacement = ['uy', 'ux']
        if isinstance(displacement, str):
            displacement = [displacement]
        for d in displacement:
            if d not in ['ux', 'uy']:
                msg = "Invalid displacement component <{}>. Supported values are 'ux' and 'uy'."
                msg = msg.format(d)
                raise RuntimeError(msg)
        nd = len(displacement)

        if acceleration is None :
            acceleration = ['agx', 'agy']
        if isinstance(acceleration, str):
            acceleration = [acceleration]
        for a in acceleration:
            if a not in ['agx', 'agy']:
                msg = "Invalid base acceleration component <{}>. Supported values are 'agx' and 'agy'."
                msg = msg.format(a)
                raise RuntimeError(msg)
        na = len(acceleration)

        idx = self._results['test'] == testid
        if location is None:
            location = self._results[idx]['location'].unique()
        elif isinstance(location, (str, numbers.Number)):
            location = [location]

        axis_label = {'ux': 'ux [cm]', 'uy': 'uy [cm]', 
                    'agx': "base horizontal\nacceleration [m/s/s]",
                    'agy': "base vertical\nacceleration [m/s/s]"}
        scale_factor = {'ux':100, 'uy':100, 'agx':1, 'agy':1}
        sign = {'ux':1, 'uy':1, 'agx':1, 'agy':1}
        if not pullout_positive:
            sign['uy'] = -1

        y_lim = {'ux':None, 'uy':None, 'agx':None, 'agy':None}
        if isinstance(ylim, dict):
            for key in y_lim:
                if key in ylim:
                    y_lim[key] = ylim[key]
        else:
            for key in y_lim:
                y_lim[key] = ylim

        fig, axes = plt.subplots(nd + na, 1, figsize=(figsize[0], figsize[1] * (nd + na)))
        for var, ax in zip(displacement + acceleration, axes):
            if var in ['agx', 'agy']:
                idx2 = idx & (self._results['location']=='top')
                ax.plot(self._results.loc[idx2, 'time'],
                        self._results.loc[idx2, var] * scale_factor[var] * sign[var])
            else:
                for loc in location:
                    idx2 = idx & (self._results['location']==loc)
                    ax.plot(self._results.loc[idx2, 'time'],
                            self._results.loc[idx2, var] * scale_factor[var] * sign[var],
                            label=loc)
                if legend:
                    ax.legend()
            ax.set_xlim(xlim)
            ax.set_ylim(y_lim[var])
            ax.set_ylabel(axis_label[var])
            ax.grid(alpha=0.2)
        axes[-1].set_xlabel('time [s]')
        plt.tight_layout()
        plt.close(fig)
        return fig