from abc import abstractmethod
import numpy as np

from padtest.geometry.geometry import Geometry
from padtest.geometry.interface import ModelInterfaces

class PlateGeometry(Geometry):
    """Geometry of a plate foudation.

    Parameters
    ----------
    b : float
        Foundation width [m].
    d : float
        Foundation depth [m].
    b2 : float, None, optional.
        Distance from the left edge to the center of the column [m]. If
        None then b/2. By default None.
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
    dratchetting : float, None
        Widht of soil under the foundation that is replaced when
        ratchetting occurs [m].
    interface : bool, dict, optional
        Bool activates/deactivates all the interfaces. Otherwise a 
        dictionary with the 'top', 'bottom', 'column' and 'lateral'
        keys can be provided. For each key either a bool is provided
        indicating whether that interface will be considered in the
        model. Also a dict can be provided for each key with the
        soil material to be assigned to it. By default False.
    model_widht : float, optional
        User specified model width [m]. By default None.
    model_depth : float, optional
        User specified model depth [m]. By default None.
    
    Methods
    -------
    plot(figsize=2.5, foundation=True, fill=True, soil=True, excavation=False, ratchetting=True, wt=True, interface=False, output_location=False)
        Foundation plot.
    """

    def __init__(self, b, d, b2=None, dstrata=None, wt=None, fill_angle=None,
                 bfill=0.5, nfill=None, dfill=None, dratchetting=0,
                 interface=False, model_width=None, model_depth=None):
        """Initialize a new instance of `PlateGeometry`.

        Parameters
        ----------
        b : float
            Foundation width [m].
        d : float
            Foundation depth [m].
        b2 : float, None, optional.
            Distance from the left edge to the center of the column [m].
            If None then b/2. By default None.
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
        dratchetting : float, None
            Widht of soil under the foundation that is replaced when
            ratchetting occurs [m].
        interface : bool, dict, optional
            Bool activates/deactivates all the interfaces. Otherwise a 
            dictionary with the 'top', 'bottom', 'column' and 'lateral'
            keys can be provided. For each key either a bool is provided
            indicating whether that interface will be considered in the
            model. Also a dict can be provided for each key with the
            soil material to be assigned to it. By default False.
        model_widht : float, optional
            User specified model width [m]. By default None.
        model_depth : float, optional
            User specified model depth [m]. By default None.
        """
        
        self._set_foundation(b, d, b2)
        Geometry.__init__(self, dstrata=dstrata, wt=wt, fill_angle=fill_angle,
                          bfill=bfill, nfill=nfill, dfill=dfill,
                          dratchetting=dratchetting,  model_width=model_width,
                          model_depth=model_depth)
        self._set_foundation_type('plate')
        self._set_interfaces(interface)
        self._set_polygons()

    #===================================================================
    # PRIVATE METHODS
    #===================================================================
    def _set_foundation(self, b, d, b2):
        """Set foundation geometry

        Parameters
        ----------
        b : float
            Foundation width [m].
        d : float
            Foundation depth [m].
        b2 : float, None, optional.
            Distance from the left edge to the center of the column [m].
            If None then b/2. By default None.
        
        Raises
        ------
        RuntimeError
            Invalid b2.
        """
        self._b = b
        self._d = d
        self._b1 = None
        self._d1 = None
        if b2 is None:
            b2 = b / 2
        if b2 > b or b2 < 0:
            msg = ("The distance from the left edge to the center of the "
                   "column <b2> must be between 0 and b.")
            raise RecursionError(msg)
        self._b2 = b2

    @abstractmethod
    def _set_interfaces(self, interface):
        """Set interfaces between the foundatio and soil.

        Parameters
        ----------
        interface : bool, dict, optional
            Bool activates/deactivates all the interfaces. Otherwise a 
            dictionary with the 'top', 'bottom', 'column' and 'lateral'
            keys can be provided. For each key either a bool is provided
            indicating whether that interface will be considered in the
            model. Also a dict can be provided for each key with the
            soil material to be assigned to it. By default False.
        """
        return NotImplementedError

    def _validate_interface_dict(self, interface):
        """Validates interface input.

        Parameters
        ----------
        interface : bool, dict, None, optional
            If True includes all interfaces between the footing and
            soil. A dictionary with fields 'column', 'top' and 'bottom'
            can be provided. If a field is True then the interface is
            activated. Missing fields are assumed to be False.
            If None, only the column interface is activated. By default
            None.

        Returns
        -------
        dict
            Interface dictionary.

        Raises
        ------
        RuntimeError
            Wrong variable type.
        """
        if interface is None :
            interface_dict = {'column':True,  'top':False,
                              'bottom':False}
        elif not isinstance(interface, (bool, dict)):
            msg = "Interface settings must be specified by a boolean or a dictionary."
            raise RuntimeError(msg)
        elif isinstance(interface, bool):
            interface_dict = {'column':interface,  'top':interface,
                              'bottom':interface}
        elif isinstance(interface, dict):
            interface_dict = {'column':False,  'top':False,
                              'bottom':False}
            for key in interface:
                if key in interface_dict:
                    interface_dict[key] = interface[key]
        return interface_dict

    @abstractmethod
    def _set_foundation_structures(self):
        """Sets the plates used for the foundation.
        """
        return NotImplementedError

    def _get_fill_polygon_vertex(self, ztop, zbottom, xsign):
        """Verteces for a polygon in the fill area.

        Parameters
        ----------
        ztop : float
            Top depth (<=0) [m].
        zbottom : float
            Bottom depth (<ztop) [m]
        xsign : float
            Side of the foundation (<0) for left (>0) for right.

        Returns
        -------
        list
            List with vertex coordinates.
        """
        vertex = []
        vertex.append([0, ztop])
        vertex.append([self._x_fill(ztop, xsign), ztop])
        vertex.append([self._x_fill(zbottom, xsign), zbottom])
        vertex.append([0, zbottom]) 
        return vertex


class SymmetricPlateGeometry(PlateGeometry):
    """Geometry of a symmetric plate foudation.

    Parameters
    ----------
    b : float
        foundation width [m].
    d : float
        foundation depth [m]
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
    dratchetting : float, None
        Widht of soil under the foundation that is replaced when
        ratchetting occurs [m].
    interface : bool, dict, optional
        Bool activates/deactivates all the interfaces. Otherwise a 
        dictionary with the 'top', 'bottom', 'column' and 'lateral'
        keys can be provided. For each key either a bool is provided
        indicating whether that interface will be considered in the
        model. Also a dict can be provided for each key with the
        soil material to be assigned to it. By default False.
    model_widht : float, optional
        User specified model width [m]. By default None.
    model_depth : float, optional
        User specified model depth [m]. By default None.
    
    Methods
    -------
    plot(figsize=2.5, foundation=True, fill=True, soil=True, excavation=False, ratchetting=True, wt=True, interface=False, output_location=False)
        Foundation plot.
    """
    
    _symmetric = True
    
    def __init__(self, b, d, dstrata=None, wt=None, fill_angle=None,
                 bfill=0.5, nfill=None, dfill=None, dratchetting=0,
                 interface=False, model_width=None, model_depth=None):
        """Initialize a new instance of `SymmetricPlateGeometry`.

        Parameters
        ----------
        b : float
            foundation width [m].
        d : float
            foundation depth [m]
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
        dratchetting : float, None
            Widht of soil under the foundation that is replaced when
            ratchetting occurs [m].
        interface : bool, dict, optional
            Bool activates/deactivates all the interfaces. Otherwise a 
            dictionary with the 'top', 'bottom', 'column' and 'lateral'
            keys can be provided. For each key either a bool is provided
            indicating whether that interface will be considered in the
            model. Also a dict can be provided for each key with the
            soil material to be assigned to it. By default False.
        model_widht : float, optional
            User specified model width [m]. By default None.
        model_depth : float, optional
            User specified model depth [m]. By default None.
        """
        
        PlateGeometry.__init__(self, b, d, b2=None, dstrata=dstrata, wt=wt,
                               fill_angle=fill_angle, bfill=bfill, nfill=nfill,
                               dfill=dfill, dratchetting=dratchetting,
                               interface=interface, model_width=model_width,
                               model_depth=model_depth)

    #===================================================================
    # PRIVATE METHODS
    #===================================================================
    def _set_interfaces(self, interface):
        """Set interfaces between the foundatio and soil.

        Parameters
        ----------
        interface : bool, dict, optional
            Bool activates/deactivates all the interfaces. Otherwise a 
            dictionary with the 'top', 'bottom', 'column' and 'lateral'
            keys can be provided. For each key either a bool is provided
            indicating whether that interface will be considered in the
            model. Also a dict can be provided for each key with the
            soil material to be assigned to it. By default False.
        """

        self._interfaces = ModelInterfaces(['column','top', 'bottom'], True)

        vertex = [[0, -self._d], [self._b / 2, -self._d]]
        self._interfaces['bottom'].set_vertex('negative', np.array(vertex))

        if self._d > 0:
            vertex = [[0, -self._d], [self._b / 2, -self._d]]
            self._interfaces['top'].set_vertex('positive', np.array(vertex))
        else:
            self._interfaces.pop('top')

        if self._d > 0:
            vertex = [[0, -self._d], [0, 0]]
            self._interfaces['column'].set_vertex('negative', np.array(vertex))
        else:
            self._interfaces.pop('column')

        self._interfaces.apply_settings(interface)

    def _set_foundation_structures(self):
        """Sets the plates used for the foundation.
        """
        if self._d == 0:
            self._foundation = np.array([[0, 0], [self._b / 2, 0]])
            self._footing = np.array([[0, 0], [self._b / 2, 0]])
            self._column = None
        else:
            self._foundation = np.array([[0, 0],
                                         [0, -self._d],
                                         [self._b / 2, -self._d]])
            self._footing = np.array([[0, -self._d], [self._b / 2, -self._d]])
            self._column = np.array([[0, 0], [0, -self._d]])


class NonSymmetricPlateGeometry(PlateGeometry):
    """Geometry of a non-symmetric plate foudation.
    
    Parameters
    ----------
    b : float
        Foundation width [m].
    d : float
        Foundation depth [m].
    b2 : float, None, optional.
        Distance from the left edge of the footing to the center of
        the column [m] (0<=b2<=b). If None then b/2. By default
        None.
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
    dratchetting : float, None
        Widht of soil under the foundation that is replaced when
        ratchetting occurs [m].
    interface : bool, dict, optional
        Bool activates/deactivates all the interfaces. Otherwise a 
        dictionary with the 'top', 'bottom', 'column' and 'lateral'
        keys can be provided. For each key either a bool is provided
        indicating whether that interface will be considered in the
        model. Also a dict can be provided for each key with the
        soil material to be assigned to it. By default False.
    model_widht : float, optional
        User specified model width [m]. By default None.
    model_depth : float, optional
        User specified model depth [m]. By default None.
    
    Methods
    -------
    plot(figsize=2.5, foundation=True, fill=True, soil=True, excavation=False, ratchetting=True, wt=True, interface=False, output_location=False)
        Foundation plot.
    """

    _symmetric = False
    
    def __init__(self, b, d, b2=None, dstrata=None, wt=None, fill_angle=None,
                 bfill=0.5, nfill=None, dfill=None, dratchetting=0,
                 interface=False, model_width=None, model_depth=None):
        """Initialize a new instance of `NonSymmetricPlateGeometry`.

        Parameters
        ----------
        b : float
            Foundation width [m].
        d : float
            Foundation depth [m].
        b2 : float, None, optional.
            Distance from the left edge of the footing to the center of
            the column [m] (0<=b2<=b). If None then b/2. By default
            None.
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
        dratchetting : float, None
            Widht of soil under the foundation that is replaced when
            ratchetting occurs [m].
        interface : bool, dict, optional
            Bool activates/deactivates all the interfaces. Otherwise a 
            dictionary with the 'top', 'bottom', 'column' and 'lateral'
            keys can be provided. For each key either a bool is provided
            indicating whether that interface will be considered in the
            model. Also a dict can be provided for each key with the
            soil material to be assigned to it. By default False.
        model_widht : float, optional
            User specified model width [m]. By default None.
        model_depth : float, optional
            User specified model depth [m]. By default None.
        """
        
        PlateGeometry.__init__(self, b, d, b2=b2, dstrata=dstrata, wt=wt,
                               fill_angle=fill_angle, bfill=bfill, nfill=nfill,
                               dfill=dfill, dratchetting=dratchetting,
                               interface=interface, model_width=model_width,
                               model_depth=model_depth)


    #===================================================================
    # PRIVATE METHODS
    #===================================================================
    def _set_interfaces(self, interface):
        """Set interfaces between the foundatio and soil.

        Parameters
        ----------
        interface : bool, dict, optional
            Bool activates/deactivates all the interfaces. Otherwise a 
            dictionary with the 'top', 'bottom', 'column' and 'lateral'
            keys can be provided. For each key either a bool is provided
            indicating whether that interface will be considered in the
            model. Also a dict can be provided for each key with the
            soil material to be assigned to it. By default False.
        """

        self._interfaces = ModelInterfaces(['column left', 'column right',
                                            'top left', 'top right',
                                            'bottom'], False)
        
        vertex = [[-self._b2 , -self._d], [self._b - self._b2, -self._d]]
        self._interfaces['bottom'].set_vertex('negative', np.array(vertex))

        if self._d > 0:
            vertex = [[-self._b2 , -self._d], [0 , -self._d]]
            self._interfaces['top left'].set_vertex('positive', np.array(vertex))
            vertex = [[0, -self._d], [self._b - self._b2, -self._d]]
            self._interfaces['top right'].set_vertex('positive', np.array(vertex))
        else:
            self._interfaces.pop('top left')
            self._interfaces.pop('top right')
        
        if self._d > 0:
            vertex = [[0, -self._d], [0, 0]]
            self._interfaces['column right'].set_vertex('negative', np.array(vertex))
            self._interfaces['column left'].set_vertex('positive', np.array(vertex))
        else:
            self._interfaces.pop('column left')
            self._interfaces.pop('column right')

        self._interfaces.apply_settings(interface)

    def _set_foundation_structures(self):
        """Sets the plates used for the foundation.
        """
        if self._d == 0:
            self._foundation = np.array([[-self._b2, 0], [self._b - self._b2, 0]])
            self._footing = np.array([[-self._b2, 0], [self._b - self._b2, 0]])
            self._column = None
        else:
            self._foundation = np.array([[0, 0],
                                         [0, -self._d],
                                         [-self._b2, -self._d],
                                         [self._b - self._b2, -self._d]])
            self._footing = np.array([[-self._b2, -self._d], [self._b - self._b2, -self._d]])
            self._column = np.array([[0, 0], [0, -self._d]])




