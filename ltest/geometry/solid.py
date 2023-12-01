from abc import abstractmethod
import numpy as np

from ltest.geometry.polygon import Polygon
from ltest.geometry.geometry import Geometry

class SolidGeometry(Geometry):
    """Geometry of a symmetric solid foundation

    Parameters
    ----------
    b : float
        Foundation width [m].
    d : float
        Foundation depth [m].
    b1 : float
        foundation column widht [m].
    d1 : float
        foundation width [m].
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
    interface : bool, dict, None, optional
        If True includes all interfaces between the footing and
        soil. A dictionary with fields 'column', 'top', 'bottom'
        and 'lateral' can be provided. If a field is True then the
        interface is activated. Missing fields are assumed to be
        False. If None, only the column interface is activated.
        By default None.
    model_widht : float, optional
        User specified model width [m]. By default None.
    model_depth : float, optional
        User specified model depth [m]. By default None.
    
    Methods
    -------
    plot(figsize=2.5, foundation=True, fill=True, soil=True, excavation=False, ratchetting=True, wt=True, interface=False, output_location=False)
        Foundation plot.
    """

    def __init__(self, b, d, b1, d1, b2=None, dstrata=None, wt=None,
                 fill_angle=None, bfill=0.5, nfill=None, dfill=None,
                 dratchetting=0, interface=None, model_width=None,
                 model_depth=None):
        """Init mehtod.

        Parameters
        ----------
        b : float
            Foundation width [m].
        d : float
            Foundation depth [m].
        b1 : float
            Foundation column widht [m].
        d1 : float
            Foundation width [m].
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
        interface : bool, dict, None, optional
            If True includes all interfaces between the footing and
            soil. A dictionary with fields 'column', 'top', 'bottom'
            and 'lateral' can be provided. If a field is True then the
            interface is activated. Missing fields are assumed to be
            False. If None, only the column interface is activated.
            By default None.
        model_widht : float, optional
            User specified model width [m]. By default None.
        model_depth : float, optional
            User specified model depth [m]. By default None.
        """
        self._set_foundation(b, d, b1, d1, b2)
        Geometry.__init__(self, dstrata=dstrata, wt=wt, fill_angle=fill_angle,
                          bfill=bfill, nfill=nfill, dfill=dfill,
                          dratchetting=dratchetting,  model_width=model_width,
                          model_depth=model_depth)
        self._set_foundation_type('solid')
        self._set_interfaces(interface)
        self._set_polygons()
                
    #===================================================================
    # PRIVATE METHODS
    #===================================================================
    def _set_foundation(self, b, d, b1, d1, b2):
        """Set foundation geometry

        Parameters
        ----------
        b : float
            Foundation width [m].
        d : float
            Foundation depth [m].
        b1 : float
            Foundation column widht [m]
        d1 : float
            Foundation width [m]
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
        self._b1 = b1
        self._d1 = d1
        if b2 is None:
            b2 = b / 2
        if b2 > b - b1 / 2 or b2 < b1 / 2:
            msg = ("The distance from the left edge to the center of the "
                   "column <b2> must be between b1/2  and b - b1/2.")
            raise RecursionError(msg)
        self._b2 = b2

    @abstractmethod
    def _set_interfaces(self, interface):
        """Set interfaces between the foundatio and soil.

        Parameters
        ----------
        interface : bool, dict, None
            If True includes all interfaces between the footing and
            soil. A dictionary with fields 'column', 'top', 'bottom'
            and 'lateral' can be provided. If a field is True then the
            interface is activated. Missing fields are assumed to be
            False. If None, only the column interface is activated.
        """
        return NotImplementedError
    
    def _validate_interface_dict(self, interface):
        """Validates interface input.

        Parameters
        ----------
        interface : bool, dict, None
            If True includes all interfaces between the footing and
            soil. A dictionary with fields 'column', 'top', 'bottom'
            and 'lateral' can be provided. If a field is True then the
            interface is activated. Missing fields are assumed to be
            False. If None, only the column interface is activated.
        
        Returns
        -------
        dict
            Interface dictionary.

        Raises
        ------
        RuntimeError
            Wrong variable type.
        """
        if interface is None:
            interface_dict = {'column':True,  'top':False,
                              'bottom':False, 'lateral':False}
        elif not isinstance(interface, (bool, dict)):
            msg = "Interface settings must be specified by a boolean or a dictionary."
            raise RuntimeError(msg)
        elif isinstance(interface, bool):
            interface_dict = {'column':interface,  'top':interface,
                              'bottom':interface, 'lateral':interface}

        elif isinstance(interface, dict):
            interface_dict = {'column':False,  'top':False,
                              'bottom':False, 'lateral':False}
            for key in interface:
                if key in interface_dict:
                    interface_dict[key] = interface[key]
        
        return interface_dict

    def _set_foundation_structures(self):
        """Sets the polygons used for the foundation.
        """
        self._column = None
        self._footing = None
        self._column_plx = None
        self._footing_plx = None
        z = np.array([0, -self._d])
        if self._d  > self._d1:
            if self._nfill is not None:
                z = np.hstack([z, self._zexcavated, self._zfill])
        else:
            z = np.hstack([z, [-self._d + self._d1]])
        z = np.flip(np.unique(z))
        for idx in range(len(z)-1):
            vertex = self._get_foundation_polygon_vertex(z[idx], z[idx + 1])
            poly = Polygon(vertex)
            self._polygons.append(poly)
            poly_idx = len(self._polygons) -  1
            self._foundation.append(poly_idx)
            if self._nfill is not None:
                excavation_idx = poly.in_strata(self._zexcavated)
                self._excavation[excavation_idx].append(poly_idx)
    
    @abstractmethod
    def _get_foundation_polygon_vertex(self, ztop, zbottom):
        """Builds a single soil polygon for the foundation.

        Parameters
        ----------
        ztop : float
            Top depth (<=0) [m].
        zbottom : float
            Bottom depth (<ztop) [m]
        
        Returns
        -------
        list
            Vertex of the foundation polygon.
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
        
        Returns
        -------
        list
            List with vertex coordinates.
        """
        
        if xsign > 0:
            xcol = self._b1 / 2
            xfoot = self._b - self._b2
        else:
            xcol = -self._b1 / 2
            xfoot = -self._b2
        vertex = []
        if ztop > -self._d + self._d1:
            vertex.append([xcol, ztop])
        else:
            vertex.append([xfoot, ztop])
        vertex.append([self._x_fill(ztop, xsign), ztop])
        vertex.append([self._x_fill(zbottom, xsign), zbottom])
        if zbottom > -self._d + self._d1:
            vertex.append([xcol, zbottom])
        else:
            vertex.append([xfoot, zbottom])
            if ztop > -self._d + self._d1:
                vertex.append([xfoot, -self._d + self._d1])
                vertex.append([xcol, -self._d + self._d1])
        return vertex


class SymmetricSolidGeometry(SolidGeometry):
    """Geometry of a symmetric solid foundation

    Parameters
    ----------
    b : float
        Foundation width [m].
    d : float
        Foundation depth [m].
    b1 : float
        Foundation column widht [m].
    d1 : float
        Foundation width [m].
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
        soil. A dictionary with fields 'column', 'top', 'bottom'
        and 'lateral' can be provided. If a field is True then the
        interface is activated. Missing fields are assumed to be
        False. If None, only the column interface is activated.
        By default None.
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

    def __init__(self, b, d, b1, d1, dstrata=None, wt=None,
                 fill_angle=None, bfill=0.5, nfill=None, dfill=None,
                 dratchetting=0, interface=None, model_width=None,
                 model_depth=None):
        """Init mehtod.

        Parameters
        ----------
        b : float
            Foundation width [m].
        d : float
            Foundation depth [m].
        b1 : float
            Foundation column widht [m].
        d1 : float
            Foundation width [m].
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
            soil. A dictionary with fields 'column', 'top', 'bottom'
            and 'lateral' can be provided. If a field is True then the
            interface is activated. Missing fields are assumed to be
            False. If None, only the column interface is activated.
            By default None.
        model_widht : float, optional
            User specified model width [m]. By default None.
        model_depth : float, optional
            User specified model depth [m]. By default None.
        """
        SolidGeometry.__init__(self, b, d, b1, d1, b2=None, dstrata=dstrata, wt=wt,
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
        interface : bool, dict, None
            If True includes all interfaces between the footing and
            soil. A dictionary with fields 'column', 'top', 'bottom'
            and 'lateral' can be provided. If a field is True then the
            interface is activated. Missing fields are assumed to be
            False. If None, only the column interface is activated.
        """

        interface_dict = self._validate_interface_dict(interface)
    
        self._interface_vertex = []
        if interface_dict['bottom']:
            vertex = [[0, -self._d], [self._b / 2, -self._d]]
            self._interface_vertex.append(('negative', np.array(vertex)))
        if interface_dict['lateral'] and self._d > 0:
            vertex = [[self._b / 2, -self._d], [self._b / 2, np.min([-self._d + self._d1, 0])]]
            self._interface_vertex.append(('negative', np.array(vertex)))
        if interface_dict['top'] and self._d > self._d1:
            vertex = [[self._b / 2, -self._d + self._d1], [self._b1 / 2, -self._d + self._d1]]
            self._interface_vertex.append(('negative', np.array(vertex)))
        if interface_dict['column'] and self._d > self._d1:
            vertex = [[self._b1 / 2, -self._d + self._d1], [self._b1 / 2, 0]]
            self._interface_vertex.append(('negative', np.array(vertex)))
    
    def _get_foundation_polygon_vertex(self, ztop, zbottom):
        """Builds a single soil polygon for the foundation.

        Parameters
        ----------
        ztop : float
            Top depth (<=0) [m].
        zbottom : float
            Bottom depth (<ztop) [m]
        
        Returns
        -------
        list
            Vertex of the foundation polygon.
        """
        vertex = [[0, ztop]]
        if ztop > - self._d + self._d1:
            vertex.append([self._b1 / 2, ztop])
            if zbottom >= - self._d + self._d1:
                vertex.append([self._b1 / 2, zbottom])
            else:
                vertex.append([self._b1 / 2, - self._d + self._d1])
                vertex.append([self._b / 2, - self._d + self._d1])
                vertex.append([self._b / 2, zbottom])
        else:
            vertex.append([self._b / 2, ztop])
            vertex.append([self._b / 2, zbottom])
        vertex.append([0, zbottom])
        return vertex


class NonSymmetricSolidGeometry(SolidGeometry):
    """Geometry of a non symmetric solid foundation

    Parameters
    ----------
    b : float
        Foundation width [m].
    d : float
        Foundation depth [m].
    b1 : float
        Foundation column widht [m].
    d1 : float
        Foundation width [m].
    b2 : float, None, optional.
        Distance from the left edge of the footing to the center of
        the column [m] (b1/2<=b2<=b-b1/2). If None then b/2. By
        default None.
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
        soil. A dictionary with fields 'column', 'top', 'bottom'
        and 'lateral' can be provided. If a field is True then the
        interface is activated. Missing fields are assumed to be
        False. If None, only the column interface is activated.
        By default None.
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

    def __init__(self, b, d, b1, d1, b2=None, dstrata=None, wt=None,
                 fill_angle=None, bfill=0.5, nfill=None, dfill=None,
                 dratchetting=0, interface=None, model_width=None,
                 model_depth=None):
        """Init mehtod.

        Parameters
        ----------
        b : float
            Foundation width [m].
        d : float
            Foundation depth [m].
        b1 : float
            Foundation column widht [m].
        d1 : float
            Foundation width [m].
        b2 : float, None, optional.
            Distance from the left edge of the footing to the center of
            the column [m] (b1/2<=b2<=b-b1/2). If None then b/2. By
            default None.
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
            soil. A dictionary with fields 'column', 'top', 'bottom'
            and 'lateral' can be provided. If a field is True then the
            interface is activated. Missing fields are assumed to be
            False. If None, only the column interface is activated.
            By default None.
        model_widht : float, optional
            User specified model width [m]. By default None.
        model_depth : float, optional
            User specified model depth [m]. By default None.
        """
        SolidGeometry.__init__(self, b, d, b1, d1, b2=b2, dstrata=dstrata, wt=wt,
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
        interface : bool, dict, None
            If True includes all interfaces between the footing and
            soil. A dictionary with fields 'column', 'top', 'bottom'
            and 'lateral' can be provided. If a field is True then the
            interface is activated. Missing fields are assumed to be
            False. If None, only the column interface is activated.
        """

        interface_dict = self._validate_interface_dict(interface)
    
        self._interface_vertex = []
        if interface_dict['bottom']:
            vertex = [[- self._b2, -self._d], [self._b - self._b2, -self._d]]
            self._interface_vertex.append(('negative', np.array(vertex)))
        
        if interface_dict['lateral'] and self._d > 0:
            vertex = [[-self._b2, np.min([-self._d + self._d1, 0])], [-self._b2, -self._d]]
            self._interface_vertex.append(('negative', np.array(vertex)))
            
            vertex = [[self._b - self._b2, -self._d], [self._b - self._b2, np.min([-self._d + self._d1, 0])]]
            self._interface_vertex.append(('negative', np.array(vertex)))
        
        if interface_dict['top'] and self._d > self._d1 and self._b2 > 0:
            vertex = [[-self._b1 / 2, -self._d + self._d1], [-self._b2, -self._d + self._d1]]
            self._interface_vertex.append(('negative', np.array(vertex)))

        if interface_dict['top'] and self._d > self._d1 and self._b2 < self._b:
            vertex = [[self._b - self._b2, -self._d + self._d1], [self._b1 / 2, -self._d + self._d1]]
            self._interface_vertex.append(('negative', np.array(vertex)))
        
        if interface_dict['column'] and self._d > self._d1:
            vertex = [[self._b1 / 2, -self._d + self._d1], [self._b1 / 2, 0]]
            self._interface_vertex.append(('negative', np.array(vertex)))

            vertex = [[-self._b1 / 2, 0], [-self._b1 / 2, -self._d + self._d1]]
            self._interface_vertex.append(('negative', np.array(vertex)))

    def _get_foundation_polygon_vertex(self, ztop, zbottom):
        """Builds a single soil polygon for the foundation.

        Parameters
        ----------
        ztop : float
            Top depth (<=0) [m].
        zbottom : float
            Bottom depth (<ztop) [m]
        
        Returns
        -------
        list
            Vertex of the foundation polygon.
        """

        xmin_col = -self._b1 / 2
        xmin_foot = -self._b2
        xmax_foot = self._b - self._b2
        
        if ztop > - self._d + self._d1:
            vertex = [[xmin_col, ztop]]
            vertex.append([self._b1 / 2, ztop])
            if zbottom >= - self._d + self._d1:
                vertex.append([self._b1 / 2, zbottom])
                vertex.append([xmin_col, zbottom])
            else:
                vertex.append([self._b1 / 2, - self._d + self._d1])
                vertex.append([xmax_foot, - self._d + self._d1])
                vertex.append([xmax_foot, zbottom])
                vertex.append([xmin_foot, zbottom])
                vertex.append([xmin_foot, - self._d + self._d1])
                vertex.append([xmin_col, - self._d + self._d1])
        else:
            vertex = [[xmin_foot, ztop]]
            vertex.append([xmax_foot, ztop])
            vertex.append([xmax_foot, zbottom])
            vertex.append([xmin_foot, zbottom])
        return vertex
    

