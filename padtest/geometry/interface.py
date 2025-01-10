"""Interfaces."""
import copy
from padtest.material.soil import SoilMaterialSelector


class ModelInterfaces(dict):
    """Model interfaces.

    Parameters
    ----------
    interfaces : list
        List of str with interfaces ids.
    symmetric : bool
        Symmetric model flag.

    Methods
    -------
    apply_settings(settings) :
        Applies user settings to interfaces.
    build_material(g_i, intidx, license) :
        Builds interface mateirals.
    build_geometry(g_i, plxid) :
        Adds interfaces to the model.
    activate(g_i) :
        Activates the interfaces in the current phase.
    remove_plaxis_objects() :
        Deletes Plaxis objects stored in the interface objects.
    """

    def __init__(self, interfaces, symmetric):
        """Initialize a new instance of `ModelInterfaces`.

        Parameters
        ----------
        interfaces : list
            List of str with interfaces ids.
        symmetric : bool
            Symmetric model flag.
        """
        for inter in interfaces:
            self[inter] = Interface()
        self._symmetric = symmetric

    def apply_settings(self, settings):
        """Applies user settings to interface.

        Parameters
        ----------
        settings : bool, dict
            Bool activates/deactivates all the interfaces. Otherwise a 
            dictionary with the 'top', 'bottom', 'column' and 'lateral'
            keys can be provided. For each key either a bool is provided
            indicating whether that interface will be considered in the
            model. Also a dict can be provided for each key with the
            soil material to be assigned to it.
        """
        if not isinstance(settings, (bool, dict)):
            msg = "Interface settings must be specified by a boolean or a dictionary."
            raise RuntimeError(msg)
        
        if isinstance(settings, bool):
            for intid in self:
                self[intid].apply_settings(settings)
        elif isinstance(settings, dict):
            if 'top' in settings and not self._symmetric:
                settings['top left'] = copy.deepcopy(settings['top'])
                settings['top right'] = copy.deepcopy(settings['top'])
                settings.pop('top')
            if 'column' in settings and not self._symmetric:
                settings['column left'] = copy.deepcopy(settings['column'])
                settings['column right'] = copy.deepcopy(settings['column'])
                settings.pop('column')
            if 'lateral' in settings and not self._symmetric:
                settings['lateral left'] = copy.deepcopy(settings['lateral'])
                settings['lateral right'] = copy.deepcopy(settings['lateral'])
                settings.pop('lateral')
            
            for key in self:
                self[key].apply_settings(False)
            for key in settings:
                if key in self:
                    self[key].apply_settings(settings[key])
    
    def build_material(self, g_i, license):
        """Builds interface mateirals.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        license : str
            Plaxis lincese: 'advanced' or 'ultimate'.
        """
        for intidx, intid in enumerate(self):
            self[intid].build_material(g_i, intidx, license)

    def build_geometry(self, g_i):
        """Adds interfaces to the model.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        """
        poscount = 0
        negcount = 0
        for intid in self:
            if not self[intid]._active:
                continue
            if self[intid]._interface_type == 'positive':
                poscount +=1 
                plxid = f'PositiveInterface_{poscount:.0f}'
            else:
                negcount +=1 
                plxid = f'NegativeInterface_{negcount:.0f}'
            self[intid].build_geometry(g_i, plxid)

    def activate(self, g_i):
        """Activates the interfaces in the current phase.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        """
        for intidx, intid in enumerate(self):
            self[intid].activate(g_i)
    
    def remove_plaxis_objects(self):
        """Deletes Plaxis objects stored in the interface objects.
        """
        for intid in self:
            self[intid].remove_plaxis_objects()
 

class Interface():
    """Single interace object.

    Methods
    -------
    apply_settings(settings) :
        Applies user settings to interface.
    set_vertex(interface_type, vertex) :
        Set vertex geometry.
    build_material(g_i, intidx, license) :
        Builds interface mateiral.
    build_geometry(g_i, plxid) :
        Adds interface to the model.
    activate(g_i) :
        Activates the interface in the current phase.
    remove_plaxis_objects() :
        Deletes Plaxis objects stored in the interface object.
    """

    def __init__(self):
        """Initialize a new instance of `Interface`.

        Parameters
        ----------
        settings : bool, dict
            Bool activates/deactivates the interface. The soil material
            is assigned to it. If a dict, it is assumed that the dict
            contains the material properties that will be assigned to
            the interface.
        """
        self._active = None
        self._material = None
        self._plxid = None
        self._plxmaterialid = None
        self._interface_type = None
        self._vertex = None

    # =========================================================================
    # PUBLIC MEHTODS
    # =========================================================================
    def apply_settings(self, settings):
        """Applies user settings to interface.

        Parameters
        ----------
        settings : bool, dict
            Bool activates/deactivates the interface. The soil material
            is assigned to it. If a dict, it is assumed that the dict
            contains the material properties that will be assigned to
            the interface.
        """

        if isinstance(settings, bool):
            self._active = settings
            self._material = None
        elif isinstance(settings, dict):
            self._active = True
            self._material = settings

    def set_vertex(self, interface_type, vertex):
        """Set vertex geometry.

        Parameters
        ----------
        interface_type : str
            'negative' or 'positive' 
        vertex : array-like
            (2,nv) vertex coordiantes.
        """
        self._interface_type = interface_type
        self._vertex = vertex

    def build_material(self, g_i, intidx, license):
        """Builds interface mateiral.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        intidx : int
            Interface number.
        license : str
            Plaxis lincese: 'advanced' or 'ultimate'.
        """
        if self._material is None:
            return
        self._plxmaterialid = f'interface_{intidx}'
        self._material['Identification'] = self._plxmaterialid
        self._material_plx = SoilMaterialSelector.create_material(g_i, self._material, license)
        
    def build_geometry(self, g_i, plxid):
        """Adds interface to the model.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        plxid : int
            Interface number according to Plaxis.
        """
        self._plxid = plxid     
        if self._interface_type == 'positive':
            self._plx_object = g_i.posinterface(list(self._vertex[0]), list(self._vertex[1]))
            return
        self._plx_object = g_i.neginterface(list(self._vertex[0]), list(self._vertex[1]))

    def activate(self, g_i):
        """Activates the interface in the current phase.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        """
        if not self._active:
            return
        g_i.activate(self._plx_object[2], g_i.Model.CurrentPhase)
        if self._material is None:
            return
        txt = f"g_i.setmaterial(g_i.{self._plxid}, g_i.Model.CurrentPhase, self._material_plx)"
        exec(txt)
        
    def remove_plaxis_objects(self):
        """Deletes Plaxis objects stored in the interface object.
        """
        self._plx_object = None
        self._material_plx = None