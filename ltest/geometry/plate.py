import numpy as np

from ltest.geometry.geometry import Geometry

class Plategeometry(Geometry):
    """Geometry of a plate foudation.

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
    
    Methods
    -------
    plot(figsize=2.5, foundation=True, fill=True, soil=True, excavation=False, ratchetting=True, wt=True, interface=False)
        Foundation plot.
    """

    def __init__(self, b, d, dstrata=None, wt=None, fill_angle=None,
                 bfill=0.5, nfill=None, dfill=None, dratchetting=0,
                 interface=None, model_width=None, model_depth=None):
        """Init mehtod.

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
        """
        
        self._set_foundation(b, d)
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
    def _set_foundation(self, b, d):
        """Set foundation geometry

        Parameters
        ----------
        b : float
            Foundation width [m].
        d : float
            Foundation depth [m].
        """
        self._b = b
        self._d = d
        self._b1 = None
        self._d1 = None

    def _set_interfaces(self, interface):
        """Set interfaces between the foundatio and soil.

        Parameters
        ----------
        interface : bool, dict, None, optional
            If True includes all interfaces between the footing and
            soil. A dictionary with fields 'column', 'top' and 'bottom'
            can be provided. If a field is True then the interface is
            activated. Missing fields are assumed to be False.
            If None, only the column interface is activated. By default None.
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
        
        self._interface_vertex = []
        if interface_dict['bottom']:
            vertex = [[0, -self._d], [self._b / 2, -self._d]]
            self._interface_vertex.append(np.array(vertex))
        if interface_dict['top'] and self._d > 0:
            vertex = [[0, -self._d], [self._b / 2, -self._d]]
            self._interface_vertex.append(np.array(vertex))
        if interface_dict['column'] and self._d > 0:
            vertex = [[0, -self._d], [0, 0]]
            self._interface_vertex.append(np.array(vertex))

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

    def _get_fill_polygon_vertex(self, ztop, zbottom):
        """Verteces for a polygon in the fill area.

        Parameters
        ----------
        ztop : float
            Top depth (<=0) [m].
        zbottom : float
            Bottom depth (<ztop) [m]

        Returns
        -------
        list
            List with vertex coordinates.
        """
        vertex = []
        vertex.append([0, ztop])
        vertex.append([self._x_fill(ztop), ztop])
        vertex.append([self._x_fill(zbottom), zbottom])
        vertex.append([0, zbottom]) 
        return vertex
            