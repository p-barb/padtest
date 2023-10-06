from ltest.geometry import Geometry
import numpy as np

class Model(dict):

    def __init__(self, s_i, g_i, b, d, soil, model_type='axisymmetry', 
                 foundation_type='plate', b1=None, d1=None, dstrata=None,
                 wt=None, fill_angle=None, bfill=0.5,
                 nfill=None, dfill=None, dunder=None, title='', comments='',
                 fill=None, under_base_initial=None, under_base_pull_out=None,
                 concrete=None, footing=None, column=None):
        self['geo'] = Geometry(b, d, foundation_type=foundation_type,
                             b1=b1, d1=d1, dstrata=dstrata, wt=wt,
                             fill_angle=fill_angle, bfill=bfill, nfill=nfill,
                             dfill=dfill, dunder=dunder)
        self._set_model(s_i, g_i, title, comments, model_type)
        self._set_strata_materials(g_i  , soil)
        self._set_fill_materials(g_i, fill)
        self._set_under_base_material(g_i, under_base_initial, under_base_pull_out)
        self._set_foundation_materials(g_i, concrete, footing, column)
        self._set_geometry(g_i)
        self._set_wt(g_i)
        #self._build_initial_phases(g_i)

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

    def _set_under_base_material(self, g_i, initial, pull_out):
        """Creates under-base materials.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        initial : dict
            Dictionary with the material properties before pull-out.
        pull_out : dict
            Dictionary with the material properties after pull-out.

        Raises
        ------
        RuntimeError
            Under-base material missing.
        """
        if self['geo']._under is None:
            return
        if initial is None or pull_out is None:
            raise RuntimeError('Under base initial and after pull-out materials must be specified.')
        self._set_soil_material(g_i, 'under_base_initial', initial)
        self._set_soil_material(g_i, 'under_base_pull_out', pull_out)

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
        
        if column is None:
            msg = "A plate material must be speified for the foundation column."
            raise RuntimeError(msg)
        if footing is None:
            msg = "A plate material must be speified for the foundation footing."
            raise RuntimeError(msg)
        self._set_plate_material(g_i, 'column', column)
        self._set_plate_material(g_i, 'footing', footing)
        
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
        """
        g_i.gotosoil()
        if 'soil material' not in self:
            self['soil material'] = {}
        if label in self['soil material']:
            raise RuntimeError("Duplicated soil material {}".format(label))

        if material["SoilModel"] == 'elastic':
            self._set_elastic(g_i, label, material)
        elif material["SoilModel"] == 'mohr-coulomb':
            self._set_mc(g_i, label, material)
        elif material["SoilModel"] == 'hardening soil':
            self._set_hs(g_i, label, material)

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

    def _set_geometry(self, g_i):
        """Creates the model structures.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        """
        g_i.gotostructures()
        self['structures'] = {}
        self['structures']['polygon'] = {}
        self['structures']['soil'] = {}
        self['structures']['line'] = {}
        self['structures']['plate'] = {}
        self['structures']['point'] = {}
        self['structures']['interface'] = {}
        # fill & excavated material
        if self['geo']._fill is not None:
            for idx, fill in enumerate(self['geo']._fill):
                args = [list(v) for v in fill]
                out = g_i.polygon(*args)
                lbl = 'fill_{:.0f}'.format(idx+1)
                mat_lbl = 'fill_{:.0f}'.format(idx+1)
                self['structures']['polygon'][lbl] = out[0]
                self['structures']['soil'][lbl] = out[1]
                #g_i.setmaterial(self['structures'][soil_lbl],self['soil material'][mat_lbl])

            for idx, excavated in enumerate(self['geo']._excavated):
                args = [list(v) for v in excavated]
                out = g_i.polygon(*args)
                lbl = 'excavated_{:.0f}'.format(idx+1)
                mat_lbl = 'strata_{:.0f}'.format(idx+1)
                self['structures']['polygon'][lbl] = out[0]
                self['structures']['soil'][lbl] = out[1]
                #g_i.setmaterial(self['structures'][soil_lbl],self['soil material'][mat_lbl])

        # soil
        for idx, strata in enumerate(self['geo']._strata):
            args = [list(v) for v in strata]
            out = g_i.polygon(*args)
            lbl = 'strata_{:.0f}'.format(idx+1)
            mat_lbl = 'strata_{:.0f}'.format(idx+1)
            self['structures']['polygon'][lbl] = out[0]
            self['structures']['soil'][lbl] = out[1]
            #g_i.setmaterial(self['structures'][soil_lbl],self['soil material'][mat_lbl])
        
        # under footing
        if self['geo']._under is not None:
            args = [list(v) for v in self['geo']._under]
            out = g_i.polygon(*args)
            self['structures']['polygon']['under'] = out[0]
            self['structures']['soil']['under'] = out[1]
            #g_i.setmaterial(self['structures']['under_footing_soil'], self['soil material']['under_base_initial'])
        
        # plate foundation
        if self['geo']._foundation_type == 'plate':
            out_plate = g_i.plate(*[list(v) for v in self['geo']._column])
            self['structures']['point']['column_1'] = out_plate[0]
            self['structures']['point']['column_2'] = out_plate[1]
            self['structures']['line']['column'] = out_plate[2]
            self['structures']['plate']['column'] = out_plate[3]
            g_i.setmaterial(self['structures']['plate']['column'], self['plate material']['column'])
            #self['column_plate'].set_material(self['column'])
            out_int = g_i.posinterface(*[list(v) for v in self['geo']._column])
            self['structures']['point']['column_int_1'] = out_int[0]
            self['structures']['point']['column_int_2'] = out_int[1]
            self['structures']['line']['column_int'] = out_int[2]
            self['structures']['interface']['column_int'] = out_int[3]
            # footing
            out = g_i.plate(*[list(v) for v in self['geo']._footing])
            self['structures']['point']['footing_1'] = out[0]
            self['structures']['point']['footing_2'] = out[1]
            self['structures']['line']['footing'] = out[2]
            self['structures']['plate']['footing'] = out[3]
            g_i.setmaterial(self['structures']['footing_plate'], self['plate material']['footing'])
            out = g_i.posinterface(*[list(v) for v in self['geo']._footing])
            self['structures']['point']['footing_pos_int_1'] = out[0]
            self['structures']['point']['footing_pos_int_2'] = out[1]
            self['structures']['line']['footing_pos_int'] = out[2]
            self['structures']['interface']['footing_pos'] = out[3]
            out = g_i.neginterface(*[list(v) for v in self['geo']._footing])
            self['structures']['point']['footing_neg_int_1'] = out[0]
            self['structures']['point']['footing_neg_int_2'] = out[1]
            self['structures']['line']['footing_neg'] = out[2]
            self['structures']['interface']['footing_neg_int'] = out[3]
            # set load
            out = g_i.pointload(list(self['structures']['column_point_1']))
            self['structures']['point']['load'] = out[0]
            self['structures']['load'] = out[1]
            return

        args = [list(v) for v in self['geo']._foundation]
        out = g_i.polygon(*args)
        self['structures']['polygon']['foundation'] = out[0]
        self['structures']['soil']['foundation'] = out[1]
        #g_i.setmaterial(self['structures']['foundation_soil'], self['soil material']['concrete'])
        # interfaces
        out_int = g_i.posinterface([self['geo']._b1 / 2, self['geo']._model_height], 
                                    [self['geo']._b1 / 2, self['geo']._model_height - self['geo']._d + self['geo']._d1])
        self['structures']['point']['column_int_1'] = out_int[0]
        self['structures']['point']['column_int_2'] = out_int[1]
        self['structures']['line']['column_int'] = out_int[2]
        self['structures']['interface']['column'] = out_int[3]

        out = g_i.posinterface([self['geo']._b1 / 2, self['geo']._model_height - self['geo']._d + self['geo']._d1],
                                [self['geo']._b / 2, self['geo']._model_height - self['geo']._d + self['geo']._d1])
        self['structures']['point']['footing_pos_int_1'] = out[0]
        self['structures']['point']['footing_pos_int_2'] = out[1]
        self['structures']['line']['footing_pos_int'] = out[2]
        self['structures']['interface']['footing_pos'] = out[3]

        out = g_i.posinterface([self['geo']._b / 2, self['geo']._model_height - self['geo']._d + self['geo']._d1],
                                [self['geo']._b / 2, self['geo']._model_height - self['geo']._d])
        self['structures']['point']['footing_lat_int_1'] = out[0]
        self['structures']['point']['footing_lat_int_2'] = out[1]
        self['structures']['line']['footing_lat'] = out[2]
        self['structures']['interface']['footing_lat'] = out[3]

        out = g_i.neginterface([self['geo']._b1 / 2, self['geo']._model_height - self['geo']._d],
                                [self['geo']._b / 2, self['geo']._model_height - self['geo']._d])
        self['structures']['point']['footing_neg_int_1'] = out[0]
        self['structures']['point']['footing_neg_int_2'] = out[1]
        self['structures']['line']['footing_neg'] = out[2]
        self['structures']['interface']['footing_neg'] = out[3]

        # set load
        out = g_i.lineload([0, self['geo']._model_height],
                           [self['geo']._b1 / 2, self['geo']._model_height])
        self['structures']['point']['load_1'] = out[0]
        self['structures']['point']['load_2'] = out[1]
        self['structures']['line']['load'] = out[2]
        self['structures']['load'] = out[3]

    def _set_wt(self, g_i):
        """Creates the model water table.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        """
        if self['geo']._wt is None:
            return
        g_i.gotoflow()
        g_i.waterlevel([0, self['geo']._wt],
                       [self['geo']._model_width, self['geo']._wt])
    
    def _build_initial_phases(self, g_i):
        self['iphases'] = {}
        if self['geo']._fill is not None:
            self._initial_phases_with_excavation(g_i)
        else:
            self._initial_phases_no_excavation(g_i)

    def _initial_phases_with_excavation(self, g_i):
        """Sets initial, excavation and construction phases.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        """
        g_i.gotostages()
        self['start phase'] = 'construction'
        # Initial phase
        self['iphases']['Initial phase'] = g_i.InitialPhase
        g_i.Model.CurrentPhase = g_i.InitialPhase

        for idx in self['structures']['polygon']:
            g_i.deactivate(self['structures']['polygon'][idx], g_i.Model.CurrentPhase)
        for idx in self['structures']['plate']:
            g_i.deactivate(self['structures']['polygon'][idx], g_i.Model.CurrentPhase)
    
        for idx in range(self['geo']._nstrata):
            lbl = 'strata_{:.0f}'.format(idx+1)
            g_i.activate(self['structures']['polygon'][lbl] , g_i.Model.CurrentPhase)
        
        for idx in range(self['geo']._nexcavated):
            lbl = 'excavated_{:.0f}'.format(idx+1)
            g_i.activate(self['structures']['polygon'][lbl] , g_i.Model.CurrentPhase)

        if self['geo']._under is not None:
            g_i.activate(self['structures']['polygon']['under'], g_i.Model.CurrentPhase)

        
        #g_i.set(self['structures']['load'], g_i.Model.CurrentPhase, 0)
        
        # Excavation phase
        # self['iphases']['excavation'] = g_i.phase(g_i.InitialPhase)
        # self['iphases']['excavation'].Identification = "excavation"
        # g_i.Model.CurrentPhase = self['iphases']['excavation']
        # for idx in range(self['geo']._nexcavated):
        #     poly_lbl = 'excavated_polygon_{:.0f}'.format(idx+1)
        #     g_i.deactivate(self['structures'][poly_lbl] , g_i.Model.CurrentPhase)

        # # Construction phase
        # self['iphases']['construction'] = g_i.phase(self['iphases']['excavation'])
        # self['iphases']['construction'].Identification = "construction"
        # g_i.Model.CurrentPhase = self['iphases']['construction']
        # for idx in range(self['geo']._nfill):
        #     poly_lbl = 'fill_polygon_{:.0f}'.format(idx+1)
        #     g_i.activate(self['structures'][poly_lbl] , g_i.Model.CurrentPhase)
        # if self['geo']._under is not None:
        #     g_i.activate(self['structures']['under_footing_polygon'] , g_i.Model.CurrentPhase)

        # if self['geo']._foundation_type == 'plate':
        #     g_i.activate(self['structures']['column_line'], g_i.Model.CurrentPhase)
        #     g_i.activate(self['structures']['footing_line'], g_i.Model.CurrentPhase)
        # else:
        #     g_i.activate(self['structures']['foundation_polygon'], g_i.Model.CurrentPhase)

    def _initial_phases_no_excavation(self, g_i):
        """Sets initial phase.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        """
        g_i.gotostages()
        self['start phase'] = 'Initial phase'
        # Initial phase
        self['iphases']['Initial phase'] = g_i.InitialPhase
        g_i.Model.CurrentPhase = g_i.InitialPhase
        for idx, strata in enumerate(self['geo']._strata):
            poly_lbl = 'strata_polygon_{:.0f}'.format(idx+1)
            g_i.activate(self['structures'][poly_lbl] , g_i.Model.CurrentPhase)
    
        if self['geo']._under is not None:
            g_i.activate(self['structures']['under_footing_polygon'] , g_i.Model.CurrentPhase)

        if self['geo']._foundation_type == 'plate':
            g_i.activate(self['structures']['column_line'], g_i.Model.CurrentPhase)
            g_i.activate(self['structures']['footing_line'], g_i.Model.CurrentPhase)
        else:
            g_i.activate(self['structures']['foundation_polygon'], g_i.Model.CurrentPhase)
        g_i.set(self['structures']['load'], g_i.Model.CurrentPhase, 0)

    #===================================================================
    # PUBLIC METHODS
    #===================================================================
    def plot(self, figsize=4, foundation=True, fill=True):
        """Foundation plot.

        Parameters
        ----------
        figsize : float, optional
            Figure width [inch], by default 4
        foundation : bool, optional
            Shows foundation structure, by default True
        fill : bool, optional
            If True shows the fill material, if False shows the original
            stratigraphy.

        Returns
        -------
        Figure
            Figure with the foundation plot.
        """
        return self['geo'].plot(figsize=figsize, foundation=foundation,
                                fill=fill)