from ltest.geometry import Geometry
import matplotlib.pyplot as plt
import numbers
import numpy as np
import pandas as pd


class Model(dict):

    def __init__(self, s_i, g_i, s_o, g_o, b, d, soil, model_type='axisymmetry', 
                 foundation_type='plate', b1=None, d1=None, dstrata=None,
                 wt=None, fill_angle=None, bfill=0.5,
                 nfill=None, dfill=None, 
                 interface=None,
                 model_width=None, model_depth=None,
                 title='', comments='',
                 fill=None, mesh_density=0.06, 
                 concrete=None, footing=None, column=None,
                 dratchetting=0, ratchetting_material = None,  ratchetting_threshold=np.inf,
                 locations=[0, 0.25, 0.5, 0.75, 1]):
        self._set_model(s_i, g_i, title, comments, model_type)
        self['geo'] = Geometry(g_i, b, d, foundation_type=foundation_type,
                               b1=b1, d1=d1, dstrata=dstrata, wt=wt,
                               fill_angle=fill_angle, bfill=bfill, nfill=nfill,
                               dfill=dfill, dratchetting=dratchetting, interface=interface,
                               model_width=model_width, model_depth=model_depth)
        self._set_strata_materials(g_i, soil)
        self._set_fill_materials(g_i, fill)
        self._set_ratchetting_material(g_i, ratchetting_material, ratchetting_threshold)
        self._set_foundation_materials(g_i, concrete, footing, column)
        self._set_load(g_i)
        self._mesh(g_i, mesh_density)
        self._build_initial_phases(g_i)
        self._init_output(g_i, g_o, locations)
        self._calculate_initial_phases(g_i, g_o)
        

    #===================================================================
    # PRIVATE METHODS
    #===================================================================
    def _set_model(self, s_i, g_i, title, comments, model_type):
        s_i.new()
        """General model settings.

        Parameters
        ----------
        s_i : Server
            Plaxis Input Application remote sripting server.
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        title : str
            Model title.
        comments : str
            Model comments.
        model_type : str
            Model type: `axisymmetry` or `planestrain`.
        """
        g_i.setproperties("Title",title, "Comments",comments, "ModelType",model_type)

    def _set_strata_materials(self, g_i, soil):
        """Creates materials for the natural stratigraphy.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
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
        if len(soil) != self['geo']._nstrata:
            msg = "A material must be specified for each of the {:.0f} soil layers."
            msg = msg.format(self['geo']._nstrata)
            raise RuntimeError(msg)
        for idx, strata in enumerate(soil):
            label = "strata_{:.0f}".format(idx + 1)
            self._set_soil_material(g_i, label, strata)

    def _set_fill_materials(self, g_i, fill):
        """Create fill materials.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
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
        if self['geo']._fill is None:
            return
        if fill is None:
            raise RuntimeError('Fill material must be specified.')
        if isinstance(fill, dict):
            fill = [fill]
        if len(fill) != self['geo']._nfill:
            msg = "A material must be specified for each of the {:.0f} fill layers."
            msg = msg.format(self['geo']._nfill)
            raise RuntimeError(msg)
        for idx, mat in enumerate(fill):    
            label = "fill_{:.0f}".format(idx + 1)
            self._set_soil_material(g_i, label, mat)

    def _set_ratchetting_material(self, g_i, ratchetting_material,
                                  ratchetting_threshold):
        """Creates under-base materials.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
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
        if self['geo']._ratchetting is None:
            self['ratchetting threshold'] = np.inf
            return
        if ratchetting_material  is None:
            raise RuntimeError('The post ratchetting material must be specified.')
        self._set_soil_material(g_i, 'ratchetting ', ratchetting_material)
        self['ratchetting threshold'] = ratchetting_threshold

    def _set_foundation_materials(self, g_i, concrete, footing, column):
        """Create materials for the foundation structure.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        concrete : dict, None
            Dictionary with the material properties for a 'solid'
            foundation. Only required in solid foundations. By default
            None.
        footing : dict, None
            Dictionary with the material properties for the column
            plate. Only required in plate foundation model. By default
            None.
        column : dict, None
            Dictionary with the material properties for the footing
            plate. Only required in plate foundation model. By default
            None.

        Raises
        ------
        RuntimeError
            Missing solid foundation material.
        RuntimeError
            Missing column plate material
        RuntimeError
            Missing footing plate material
        """
        if self['geo']._foundation_type == 'solid' and concrete is None:
            msg = "A 'soil' material must be speified for the foundation concrete."
            raise RuntimeError(msg)
        elif self['geo']._foundation_type == 'solid':
            self._set_soil_material(g_i, 'concrete', concrete)
            return
        
        if column is None and self['geo']._d > 0:
            msg = "A plate material must be speified for the foundation column."
            raise RuntimeError(msg)
        if column is not None:
            self._set_plate_material(g_i, 'column', column)
        if footing is None:
            msg = "A plate material must be speified for the foundation footing."
            raise RuntimeError(msg)
        self._set_plate_material(g_i, 'footing', footing)

        g_i.gotostructures()
        self['geo']._footing[-1].setmaterial(self['plate material']['footing'])
        if self['geo']._column is not None:
            self['geo']._column[-1].setmaterial(self['plate material']['column'])
        
    def _set_soil_material(self, g_i, label, material):
        """Create soil materials in the model.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        label : str
            Material label.
        material : dict
            Dictionary with material properties

        Returns
        -------
        dict
            Dictionary with model objects.

        Raises
        ------
        RuntimeError
            Duplicated material id.
        RuntimeError
            Unsuported soil model.
        """
        g_i.gotosoil()
        if 'soil material' not in self:
            self['soil material'] = {}
        if label in self['soil material']:
            raise RuntimeError("Duplicated soil material {}".format(label))

        if material["SoilModel"].lower() == 'elastic':
            self._set_elastic(g_i, label, material)
        elif material["SoilModel"].lower() in ['mohr-coulomb', 'mohr coulomb', 'mc', 'mohrcoulomb']:
            self._set_mc(g_i, label, material)
        elif material["SoilModel"].lower() in ['hardening-soil', 'hardening soil', 'hs', 'hardeningsoil']:
            self._set_hs(g_i, label, material)
        else:
            raise RuntimeError('Unsuported soil model <{}>'.format(material["SoilModel"]))

    def _set_elastic(self, g_i, label, material):
        """Creates an elastic soil material in the model.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        label : str
            Material label.
        material : dict
            Dictionary with material properties

        Returns
        -------
        dict
            Dictionary with model objects.
        """

        if 'kx' not in material:
            material['kx'] = 0
        if 'ky' not in material:
            material['ky'] = 0
        if 'Rinter' not in material:
            material['Rinter'] = 1
        
        self['soil material'][label] = g_i.soilmat("MaterialName",label,
                                                    "SoilModel", 1,
                                                    "DrainageType", material["DrainageType"] ,
                                                    "Eref", material['Eref'],
                                                    "nu", material['nu'],
                                                    "gammaSat", material['gammaSat'],
                                                    "gammaUnsat", material['gammaUnsat'],
                                                    'perm_primary_horizontal_axis', material['kx'],
                                                    'perm_vertical_axis', material['ky'],
                                                    'Rinter', material['Rinter'])

    def _set_mc(self, g_i, label, material):
        """Creates a Mohr-Coulomb soil material in the model.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        label : str
            Material label.
        material : dict
            Dictionary with material properties

        Returns
        -------
        dict
            Dictionary with model objects.
        """
        if 'kx' not in material:
            material['kx'] = 0
        if 'ky' not in material:
            material['ky'] = 0
        if 'Rinter' not in material:
            material['Rinter'] = 1
        if 'OCR' not in material:
            material['OCR'] = 1
        if 'POP' not in material:
            material['POP'] = 0
        self['soil material'][label] = g_i.soilmat("MaterialName",label,
                                                    "SoilModel", 2,
                                                    "DrainageType", material["DrainageType"] ,
                                                    "Eref", material['Eref'],
                                                    "nu", material['nu'],
                                                    'cref', material['cref'],
                                                    'phi', material['phi'],
                                                    'psi', material['psi'],
                                                    "gammaSat", material['gammaSat'],
                                                    "gammaUnsat", material['gammaUnsat'],
                                                    'OCR',material['OCR'],
                                                    'POP',material['POP'],
                                                    'perm_primary_horizontal_axis', material['kx'],
                                                    'perm_vertical_axis', material['ky'],
                                                    'Rinter', material['Rinter'])

    def _set_hs(self, g_i, label, material):
        """Creates a hardening soil material in the model.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        label : str
            Material label.
        material : dict
            Dictionary with material properties

        Returns
        -------
        dict
            Dictionary with model objects.
        """
        if 'kx' not in material:
            material['kx'] = 0
        if 'ky' not in material:
            material['ky'] = 0
        if 'Rinter' not in material:
            material['Rinter'] = 1
        if 'K0nc' not in material:
            material['K0nc'] = 1 - np.sin(np.radians(material['phi']))
        if 'OCR' not in material:
            material['OCR'] = 1
        if 'POP' not in material:
            material['POP'] = 0
        self['soil material'][label] = g_i.soilmat("MaterialName",label, 
                                                   "SoilModel", 3,
                                                   "DrainageType", material["DrainageType"] ,
                                                   "gammaSat", material['gammaSat'],
                                                   "gammaUnsat", material['gammaUnsat'],
                                                   'einit', material['e0'],
                                                   'E50ref',material['E50ref'],
                                                   'EoedRef', material['Eoedref'],
                                                   'EurRef', material['Euref'],
                                                   'powerm', material['powerm'], 
                                                   'cref', material['c'],
                                                   'phi', material['phi'],
                                                   'psi', material['psi'],
                                                   'nu', material['nu'], 
                                                   'K0nc',material['K0nc'],
                                                   'OCR',material['OCR'],
                                                   'POP',material['POP'],
                                                   'perm_primary_horizontal_axis', material['kx'],
                                                   'perm_vertical_axis', material['ky'],
                                                   'Rinter', material['Rinter'])

    def _set_plate_material(self, g_i, label, material):
        """Creates an elastic plate  material in the model.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        label : str
            Material label.
        material : dict
            Dictionary with material properties

        Returns
        -------
        dict
            Dictionary with model objects.
        """

        g_i.gotosoil()
        if 'plate material' not in self:
            self['plate material'] = {}
        if label in self['plate material']:
            raise RuntimeError("Duplicated plate material {}".format(label))
        self['plate material'][label] = g_i.platemat("MaterialName", label,
                                                     "MaterialNumber", 0,
                                                     "Elasticity", 0,
                                                     "IsIsotropic", True,
                                                     "EA", material['EA'],
                                                     "EA2", material['EA'],
                                                     "EI", material['EI'],
                                                     "nu", material['nu'],
                                                     "d", material['d'],
                                                     "Gref", material['Gref'])

    def _set_load(self, g_i):
        """Creates the foundation load.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        """
        if self['geo']._foundation_type == 'plate':
            self['load'] = g_i.pointload([0, 0])
        elif self['geo']._d > self['geo']._d1:
            self['load'] = g_i.lineload([0, 0], [self['geo']._b1 / 2, 0])
        else:
            zload = -self['geo']._d + self['geo']._d1
            self['load'] = g_i.lineload([0, zload], [self['geo']._b1 / 2, zload])

    def _mesh(self, g_i, mesh_density):
        """Mesh the model.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        mesh_density : float
            Mesh density.
        """
        g_i.gotomesh()
        self['mesh'] = g_i.mesh(mesh_density)

    def _build_initial_phases(self, g_i):
        """Sets the model initial phases.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        """
        self['iphases'] = {}
        if self['geo']._fill is not None:
            self._initial_phases_with_excavation(g_i)
        else:
            self._initial_phases_no_excavation(g_i)

    def _initial_phases_with_excavation(self, g_i):
        """Sets initial, excavation and construction phases in a model
        with excavation.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        """

        g_i.gotostages()
        self['start phase'] = 'construction'
        self['start phase idx'] = 2
        self['nphase'] = 3
        # Initial phase
        self['iphases']['Initial Phase'] = g_i.InitialPhase
        g_i.Model.CurrentPhase = g_i.InitialPhase

        for poly in self['geo']._structure_polygons:
            g_i.activate(poly, g_i.Model.CurrentPhase)
        if self['geo']._foundation_type == 'plate':
            g_i.deactivate(self['geo']._footing[2],  g_i.Model.CurrentPhase)
            if self['geo']._column is not None:
                g_i.deactivate(self['geo']._column[2],  g_i.Model.CurrentPhase)
        for strata_idx, poly_idxs in self['geo']._excavated.items():
            for poly_idx in poly_idxs:
                self._set_material(g_i, poly_idx + 1, 0, 'strata_{:.0f}'.format(strata_idx + 1))
        for strata_idx, poly_idxs in self['geo']._strata.items():
            for poly_idx in poly_idxs:
                self._set_material(g_i, poly_idx + 1, 0, 'strata_{:.0f}'.format(strata_idx + 1))
        if self['geo']._ratchetting is not None:
            for strata_idx, poly_idxs in self['geo']._ratchetting.items():
                for poly_idx in poly_idxs:
                    self._set_material(g_i, poly_idx + 1, 0, 'strata_{:.0f}'.format(strata_idx + 1))

        # Excavation phase
        self['iphases']['excavation'] = g_i.phase(g_i.InitialPhase)
        self['iphases']['excavation'].Identification = "excavation"
        g_i.Model.CurrentPhase = self['iphases']['excavation']

        for strata_idx, poly_idxs in self['geo']._excavated.items():
            for poly_idx in poly_idxs:
                g_i.deactivate(self['geo']._structure_polygons[poly_idx], g_i.Model.CurrentPhase)

        # construction phase
        self['iphases']['construction'] = g_i.phase(self['iphases']['excavation'])
        self['iphases']['construction'].Identification = "construction"
        g_i.Model.CurrentPhase = self['iphases']['construction']

        if self['geo']._foundation_type == 'solid':
            for poly_idx in self['geo']._foundation:
                g_i.activate(self['geo']._structure_polygons[poly_idx], g_i.Model.CurrentPhase)
                self._set_material(g_i, poly_idx + 1, 2, 'concrete')
        else:
            g_i.activate(self['geo']._footing[2],  g_i.Model.CurrentPhase)
            if self['geo']._column is not None:
                g_i.activate(self['geo']._column[2],  g_i.Model.CurrentPhase)
            
        for strata_idx, poly_idxs in self['geo']._fill.items():
            for poly_idx in poly_idxs:
                g_i.activate(self['geo']._structure_polygons[poly_idx], g_i.Model.CurrentPhase)

        for strata_idx, poly_idxs in self['geo']._fill.items():
            for poly_idx in poly_idxs:
                self._set_material(g_i, poly_idx + 1, 2, 'fill_{:.0f}'.format(strata_idx + 1))

        if self['geo']._interface is not None:
            for interface in self['geo']._interface:
                g_i.activate(interface[2], g_i.Model.CurrentPhase)

    def _initial_phases_no_excavation(self, g_i):
        """Sets initial phase.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        """
        g_i.gotostages()
        self['start phase'] = 'construction'
        self['start phase idx'] = 0
        self['nphase'] = 1
        # Initial phase
        self['iphases']['Initial Phase'] = g_i.InitialPhase
        g_i.Model.CurrentPhase = g_i.InitialPhase

        
        for poly in self['geo']._structure_polygons:
            g_i.activate(poly, g_i.Model.CurrentPhase)

        if self['geo']._foundation_type == 'solid':
            for poly_idx in self['geo']._foundation:
                self._set_material(g_i, poly_idx + 1, 0, 'concrete')
        else:
            g_i.activate(self['geo']._footing[2],  g_i.Model.CurrentPhase)
            if self['geo']._column is not None:
                g_i.activate(self['geo']._column[2],  g_i.Model.CurrentPhase)

        for strata_idx, poly_idxs in self['geo']._strata.items():
            for poly_idx in poly_idxs:
                self._set_material(g_i, poly_idx + 1, 0, 'strata_{:.0f}'.format(strata_idx + 1))
        if self['geo']._ratchetting is not None:
            for strata_idx, poly_idxs in self['geo']._ratchetting.items():
                for poly_idx in poly_idxs:
                    self._set_material(g_i, poly_idx + 1, 0, 'strata_{:.0f}'.format(strata_idx + 1))

        if self['geo']._interface is not None:
            for interface in self['geo']._interface:
                g_i.activate(interface[2], g_i.Model.CurrentPhase)

        # construction phase
        self['iphases']['construction'] = g_i.phase(self['iphases']['Initial Phase'])
        self['iphases']['construction'].Identification = "construction"

    def _set_material(self, g_i, soil_idx, phase_idx, material):
        """Assings a soil material to a polygon in a given phase.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        soil_idx : int
            Numer that identifies the soil, e.g. Soil_#.
        phase_idx : int
            Index of the phase in the g_i.phases list.
        material : str
            Material key in the soil material dictionary.
        """
        material = "self['soil material']['{}']".format(material)
        txt = "g_i.setmaterial(g_i.Soil_{:.0f}, g_i.phases[{:.0f}], {})"
        txt = txt.format(soil_idx, phase_idx, material)
        exec(txt)

    def _init_output(self, g_i, g_o, locations):
        """Selects output locations.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        g_o : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Output.
        locations : array-like
            Location of output points in the foundation bottom, measured
            as [0, 1] where 0 is the center of the foundation and 1 the
            edge.
        """
        
        self['test ids'] = {}
        # build df
        results_df = pd.DataFrame(columns=['test', 'phase', 'previous', 'plx id',
                                           'previous plx id', 'location', 'step',
                                           'load start', 'load end', 'load',
                                           'uy', 'sumMstage', 'fy', 'qy', 'uy',
                                           'ratchetting'])
        self['results'] = results_df

        g_i.gotostages()
        g_i.set(g_i.Model.CurrentPhase, self['iphases'][self['start phase']])
        g_i.selectmeshpoints()

        self['ophases'] = {}
        self['ouput location'] = locations
        self['ouput point'] = {}
        if self['geo']._foundation_type == 'plate':
            for idx in range(len(g_i.Plates)):
                if g_i.Plates[idx].Name.value == 'Plate_1_1':
                    plate_o = g_o.get_equivalent(g_i.Plates[idx])
                    self['ouput point']['top'] = g_o.addcurvepoint("node", plate_o, (0, 0))
                if g_i.Plates[idx].Name.value == 'Plate_2_1':
                    plate_o = g_o.get_equivalent(g_i.Plates[idx])
                    for loc in locations:
                        self['ouput point'][loc] = g_o.addcurvepoint("node", plate_o, (loc * self['geo']._b / 2,  -self['geo']._d))
            g_o.update()
            return
        soil_idx = int(np.max(self['geo']._foundation) + 1)
        for soil in g_i.Soils:
            if soil.Name.value == 'Soil_{:.0f}_1'.format(soil_idx):
                soil_o = g_o.get_equivalent(soil)
                break
        for loc in locations:
            self['ouput point'][loc] = g_o.addcurvepoint("node", soil_o, (loc * self['geo']._b / 2, -self['geo']._d))
        soil_o = g_o.get_equivalent(g_i.Soil_1_1)
        if self['geo']._d > self['geo']._d1:
            self['ouput point']['top'] = g_o.addcurvepoint("node", soil_o, (0, 0))
        else:
            self['ouput point']['top'] = g_o.addcurvepoint("node", soil_o, (0, self['geo']._d1 - self['geo']._d))
        g_o.update()    

    def _calculate_initial_phases(self, g_i, g_o):
        """Computs initial phases.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.

        Raises
        ------
        RuntimeError
            Phase calculation error.
        """
        
        for phase in self['iphases']:
            phaseid = phase
            status = g_i.calculate(self['iphases'][phase])
            if status != 'OK':
                raise RuntimeError(status)
        
        g_i.view(g_i.Model.CurrentPhase)
        self['ophases'][phaseid] = g_o.phases[-1]

        nstep = len(list(self['ophases'][phaseid].Steps.value))
        Uy = np.zeros((len(self['ouput point']), nstep))
        sumMstage = np.zeros(nstep)
        Fy = np.zeros(nstep)
        qy = np.zeros(nstep)
        steps = np.linspace(1, nstep, nstep)
        load_start = 0
        load_end = 0

        if self['geo']._foundation_type == 'solid':
            for sidx, step in enumerate(self['ophases'][phaseid].Steps.value):
                sumMstage[sidx] = step.Reached.SumMstage.value
                for locidx, node in enumerate(self['ouput point'].keys()):
                    Uy[locidx, sidx] = g_o.getcurveresults(self['ouput point'][node], step, g_o.ResultTypes.Soil.Uy)
        else:
            for sidx, step in enumerate(self['ophases'][phaseid].Steps.value):
                sumMstage[sidx] = step.Reached.SumMstage.value
                for locidx, node in enumerate(self['ouput point'].keys()):
                    Uy[locidx, sidx] = g_o.getcurveresults(self['ouput point'][node], step, g_o.ResultTypes.Soil.Uy)
        
        # ad results to dataframe
        for locidx, loc in enumerate(self['ouput point']):
            df = pd.DataFrame({'test':[None] * nstep,
                               'phase':[self['iphases'][phase].Identification.value] * nstep,
                               'previous':[None] * nstep,
                               'plx id':[self['iphases'][phase].Name.value] * nstep,
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
            if len(self['results']) == 0:
                self['results'] = df
            else:
                self['results'] = pd.concat([self['results'], df])
            self['results'].reset_index(inplace=True, drop=True)
               
    def _calculate_load_phase(self, g_i, testid, phaseid, prevphaseid, load, 
                              nstep, ratchetting):
        """Computes a phase in a load test.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        testid : str
            Test id.
        phaseid : str
            Phase id
        prevphaseid : str
            If of the previous phase.
        load : numeric
            Load value at the end of the phase [kN]. 
        nstep : nstep : int, optional
            Maximum number of stes in each phase, by default 1
        ratchetting : bool
            Flag indicating that ratchetting has alredy occured in any
            previous phase.

        Returns
        -------
        str
            Calculation status, 'OK' or error message.
        """
        self['test ids'][testid].append(phaseid)
        self['iphases'][phaseid] = g_i.phase(self['iphases'][prevphaseid])
        self['iphases'][phaseid].Identification = phaseid

        g_i.Model.CurrentPhase = self['iphases'][phaseid]
        g_i.set(g_i.Model.CurrentPhase.MaxStepsStored, nstep)
        self._update_ratchetting_material(g_i, ratchetting, phaseid, prevphaseid)
        
        if self['geo']._foundation_type == 'solid':
            g_i.activate(g_i.LineLoad_1_1, g_i.Model.CurrentPhase)
            g_i.set(g_i.LineLoad_1_1.qy_start, g_i.Model.CurrentPhase, load / self['geo']._b1)
        else:
            g_i.activate(g_i.PointLoad_1_1, g_i.Model.CurrentPhase)
            g_i.set(g_i.PointLoad_1_1.Fy, g_i.Model.CurrentPhase, load)
            # g_i.activate(self['load'][0], g_i.Model.CurrentPhase)
            # g_i.set(self['load'][1].Fy, g_i.Model.CurrentPhase, load)
        status = g_i.calculate(g_i.Model.CurrentPhase)
        return status
    
    def _update_ratchetting_material(self, g_i, ratchetting, phaseid, prevphaseid):
        """Sets the ratchetting material under the base if ratchetting
        occured in the previous phase.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
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
        if any(self['results'][['phase']==prevphaseid][ratchetting].to_list()):
            return
        for _, poly_idxs in self['geo']._ratchetting.items():
            for poly_idx in poly_idxs:
                self._set_material(g_i, poly_idx + 1, self['iphases'][phaseid].Number.value, 'ratchetting')

    def _check_phase_status(self, g_i, g_o, status, testid, phaseid, delete_phases):
        """Checks calculation status.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        g_io : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Output.
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
            g_i.view(g_i.Model.CurrentPhase)
            self['ophases'][phaseid] = g_o.phases[-1]
            return
        self.delete_test(g_i, g_o, testid, delete_phases=delete_phases)
        raise RuntimeError(status + ' <{}>'.format(phaseid))
    
    def _check_ratchetting(self, g_i, testid, phaseid, ratchetting):
        """Checks if ratchetting occurred in a calculation phase.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
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
        if ratchetting or self['geo']._ratchetting is None:
            return ratchetting
        idx = (self['results']['test'] == testid) \
              & (self['results']['phase'] == phaseid) \
              & (self['results']['location'] != 'top') 
        max_disp = self['results'].loc[idx, 'uy'].max()
        if max_disp >= self['ratchetting threshold']:
            ratchetting = True
        return ratchetting

    def _get_phase_results(self, g_i, g_o, testid, load_value, phaseid,
                           prevphaseid, ratchetting):
        """Adds phase results to the results dataframe.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        g_io : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Output.
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
        iphase = self['iphases'][phaseid]
        previphase = self['iphases'][prevphaseid]
        ophase = self['ophases'][phaseid]

        nstep = len(list(ophase.Steps.value))
        Uy = np.zeros((len(self['ouput point']), nstep + 1))
        sumMstage = np.zeros(nstep + 1)
        Fy = np.zeros(nstep + 1)
        qy = np.zeros(nstep + 1)
        steps = np.linspace(0, nstep, nstep + 1)
        load_start = 0
        load_end = 0

        # start with last step from previous phase
        idx1 = (self['results']['phase'] == prevphaseid)
        f0 = self['results'].loc[idx1].take([-1])['fy'].to_list()[0]
        Fy[0] = f0
        for locidx, node in enumerate(self['ouput point'].keys()):
            idx2 = idx1 & (self['results']['location'] == node)
            U0 = self['results'].loc[idx2].take([-1])['uy'].to_list()[0]
            Uy[locidx, 0] = U0

        # get current phase results
        if self['geo']._foundation_type == 'solid':
            for sidx, step in enumerate(ophase.Steps.value):
                sumMstage[sidx + 1] = step.Reached.SumMstage.value
                for locidx, node in enumerate(self['ouput point'].keys()):
                    Uy[locidx, sidx + 1] = g_o.getcurveresults(self['ouput point'][node], step, g_o.ResultTypes.Soil.Uy)
            if g_i.LineLoad_1_1.Active[previphase] is not None:
                if g_i.LineLoad_1_1.Active[previphase].value:
                    load_start = g_i.LineLoad_1_1.qy_start[previphase].value
            if g_i.LineLoad_1_1.Active[iphase] is not None:
                if g_i.LineLoad_1_1.Active[iphase].value:
                    load_end = g_i.LineLoad_1_1.qy_start[iphase].value
                    qy = load_start + (load_end - load_start) * sumMstage
                    Fy = qy * self['geo']._b1
        else:
            for sidx, step in enumerate(ophase.Steps.value):
                sumMstage[sidx + 1] = step.Reached.SumMstage.value
                for locidx, node in enumerate(self['ouput point'].keys()):
                    Uy[locidx, sidx + 1] = g_o.getcurveresults(self['ouput point'][node], step, g_o.ResultTypes.Plate.Uy)
            if g_i.PointLoad_1_1.Active[previphase] is not None:
                if g_i.PointLoad_1_1.Active[previphase].value:
                    load_start = g_i.PointLoad_1_1.Fy[previphase].value
            if g_i.PointLoad_1_1.Active[iphase] is not None:
                if g_i.PointLoad_1_1.Active[iphase].value:
                    load_end = g_i.PointLoad_1_1.Fy[iphase].value
                    Fy = load_start + (load_end - load_start) * sumMstage
        
        # ad results to dataframe
        for locidx, loc in enumerate(self['ouput point']):
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
                               'ratchetting': [ratchetting] * (nstep + 1)})
            if len(self['results']) == 0:
                self['results'] = df
            else:
                self['results'] = pd.concat([self['results'], df])
            self['results'].reset_index(inplace=True, drop=True)

    #===================================================================
    # PUBLIC METHODS
    #===================================================================
    def plot(self, figsize=2, foundation=True, fill=True, soil=True,
             excavation=False, ratchetting=True, wt=True, interface=False):
        """Foundation plot.

        Parameters
        ----------
        figsize : float, optional
            Figure width [inch], by default 4
        foundation : bool, optional
            Shows foundation structure. By default True
        fill : bool, optional
            Shows the fill material, if False shows the original
            stratigraphy. By default True
        soil : bool, optional
            Shows the local soil. By default True.
        excavation : bool, optional
            Shows the material excavated to build the foundation. By
            default False.
        ratchetting : bool, optional
            Shows the ratchetting material. By default True.
        wt : bool, optional
            Shows the global water table. By defautl True.
        interface : bool, optional
            Shows interface between the foundation and soil. By default
            False.

        Returns
        -------
        Figure
            Figure with the foundation plot.
        """
        return self['geo'].plot(figsize=figsize, foundation=foundation,
                                fill=fill, soil=soil, ratchetting=ratchetting,
                                wt=wt, interface=interface)
    
    def failure_test(self, g_i, g_o, testid, test, nstep=100, max_load=np.inf,
                     start_load=50, load_factor=2, load_increment=0):
        """Test the foundation until the model does not converge. A
        first trial is done using the start_load value. If lack of
        convergence is not achieved, the load is incremented as: 

        load = load_factor * load + load_increment.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        g_o : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Output.
        testid : str
            Test id.
        test : str
            Test type: 'compression' or 'pull out'.
        nstep : int, optional
            Maximum number of stes in each phase, by default 100.
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
        if testid in self['test ids'].keys():
            raise RuntimeError('Duplicated test id <{}>.'.format(testid))
        self['test ids'][testid] = []
        if test not in ('compression', 'pull out'):
            msg = "Test type can either be <'compression'> or <'pull out'>."
            raise RuntimeError(msg)
        if test == 'compression':
            load = -np.abs(start_load)
        else:
            load = np.abs(start_load)
        phaseid = testid
        previous_phase = self['start phase']
        status = 'OK'
        while status == 'OK' and np.abs(load) <= max_load:
            status = self._calculate_load_phase(g_i, testid, phaseid, previous_phase, load, nstep, False)
            load = load_factor * load + np.sign(load) * load_increment
            if status == 'OK':
                for phase in g_i.phases:
                    if phase.Identification.value == phaseid:
                        g_i.delete(phase)
                _ = self['iphases'].pop(phaseid)
                self['test ids'][testid] = []
        g_i.view(g_i.Model.CurrentPhase)
        self['ophases'][phaseid] = g_o.phases[-1]
        self._get_phase_results(g_i, g_o, testid, load, phaseid, previous_phase, False)

    def load_test(self, g_i, g_o, testid, load, nstep=100, delete_phases=True):
        """Conducts a load test in the model.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        g_o : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Output.
        testid : str
            Test id.
        load : numeric, array-like
            (nl,) Loads applied in each phase of the test [kN].
        nstep : int, optional
            Maximum number of stes in each phase, by default 100.
        delete_phases : bool, optional
            Deletes test phases from model if there is a calculation
            error, by default True.

        Raises
        ------
        RuntimeError
            Test id alredy in model.
        """
   
        if testid in self['test ids'].keys():
            raise RuntimeError('Duplicated test id <{}>.'.format(testid))
        self['test ids'][testid] = []
        if isinstance(load, numbers.Number):
            load = [load]
        test_phases = [testid + '_stage_{:.0f}'.format(idx) for idx in range(len(load))]
        previous_phase = [self['start phase']] + test_phases[:-1]
        ratchetting = False
        for load_value, phaseid, prevphaseid in zip(load, test_phases, previous_phase):
            status = self._calculate_load_phase(g_i, testid, phaseid, prevphaseid,
                                                load_value, nstep, ratchetting)
            self._check_phase_status(g_i, g_o, status, testid, phaseid, delete_phases)
            ratchetting = self._check_ratchetting(g_i, testid, phaseid, ratchetting)
            self._get_phase_results(g_i, g_o, testid, load_value, phaseid, prevphaseid, ratchetting)
    
    def delete_test(self, g_i, g_o, testid, delete_phases=True):
        """Deletes a test from the model.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        g_o : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Output.
        testid : str
            Test id.
        delete_phases : bool, optional
            Deletes test phases from model, by default True

        Raises
        ------
        RuntimeError
            Test not present in model.
        """
        if testid not in self['test ids']:
            msg = 'Test <{}> not in results'.format(testid)
            raise RuntimeError(msg)
        test_phases = self['test ids'][testid]
        _ = self['test ids'].pop(testid)
        if delete_phases:
            test_phases.reverse()
            for phaseid in test_phases:
                for phase in g_i.phases:
                    if phase.Identification.value == phaseid:
                        g_i.delete(phase)
                for phase in g_o.phases:
                    if phase.Identification.value == phaseid:
                        g_i.delete(phase)
            test_phases.reverse()
        for phaseid in test_phases:
            if phaseid in self['iphases']:
                _ = self['iphases'].pop(phaseid)
            if phaseid in self['ophases']:
                _ = self['ophases'].pop(phaseid)
        self['results'] = self['results'][self['results']['test']!=testid]
        self['results'].reset_index(drop=True, inplace=True)

    def plot_test(self, testid, phase=None, location=None, 
                  compression_positive=True, uplift_positive=True,
                  reset_start=False, legend=False, figsize=(6, 4)):
        if testid not in self['results']['test'].to_list():
            raise RuntimeError('Test <{}> not available in restuls.'.format(testid))
        idx = self['results']['test'] == testid
        if phase is None:
            phase = self['results'][idx]['phase'].unique()
        elif isinstance(phase, (str, numbers.Number)):
            phase = [phase]
        phase_order = []
        for pidx in range(len(phase)):
            if isinstance(phase[pidx], numbers.Number):
                phase[pidx] = '{}_stage_{:.0f}'.format(testid, phase[pidx])
            if phase[pidx] not in self['results'][idx]['phase'].to_list():
                msg = 'Phase <{}> not available in test <{}> not available in restuls'
                msg = msg.format(phase[pidx], testid)
                raise RuntimeError(msg)
            idx2 = idx & (self['results']['phase']==phase[pidx])
            phase_order.append(int(self['results'][idx2]['plx id'].unique()[0][6:]))
        phase = [x for _, x in sorted(zip(phase_order, phase))]

        if location is None:
            location = self['results'][idx]['location'].unique()
        elif isinstance(location, (str, numbers.Number)):
            location = [location]
            
        fig, ax = plt.subplots(1, 1, figsize=figsize)
        
        fsign = 1
        dsign = 1
        
        if compression_positive:
            fsign = -1
        if uplift_positive:
            dsign =- 1
        for loc in location:
            for phaseid in phase:
                idx2 = idx & (self['results']['phase']==phaseid) * (self['results']['location']==loc)
                u0 = 0
                if reset_start:
                    u0 = self['results'].loc[idx2, 'uy'].to_numpy()[0]
                ax.plot(dsign * (self['results'].loc[idx2, 'uy'] - u0)  *100,
                        fsign * self['results'].loc[idx2, 'fy'],
                        label='{} - {}'.format(loc, phaseid))
        if legend:
            ax.legend()
        ax.set_ylabel('Axial force [kN]')
        ax.set_xlabel('Vertical displacement [cm]')
        ax.grid(alpha=0.2)
        plt.close(fig)
        return fig
        
    
        
        