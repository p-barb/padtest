from abc import ABC, abstractmethod
import copy
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as PatchPolygon
from matplotlib.collections import PatchCollection
DEFAULT_CYCLE = plt.rcParams['axes.prop_cycle'].by_key()['color']
import numbers
import numpy as np
import textwrap

from padtest.geometry.polygon import Polygon

class Geometry(ABC):
    """Base class for the foundation geometry. Set inputs that are not
    dependent on whether the foundation is modelled as a solid or a
    plate.

    Parameters
    ----------
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
    model_widht : float, optional
        User specified model width [m]. By default None.
    model_depth : float, optional
        User specified model depth [m]. By default None.

    Methods
    -------
    plot(figsize=2.5, foundation=True, fill=True, soil=True, excavation=False, ratchetting=True, wt=True, interface=False, output_location=False)
        Foundation plot.
    """

    def __init__(self, dstrata=None, wt=None, fill_angle=None, bfill=0.5,
                 nfill=None, dfill=None, dratchetting=0,  model_width=None,
                 model_depth=None):
        """Initialize a new instance of `Geometry`.

        Parameters
        ----------
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
        model_widht : float, optional
            User specified model width [m]. By default None.
        model_depth : float, optional
            User specified model depth [m]. By default None.
        """

        self._set_soil_parameters(dstrata, model_depth)
        self._set_fill_parameters(fill_angle, nfill, dfill, bfill)
        self._set_excavation_parameters()
        self._set_ratchetting_parameters(dratchetting)
        self._set_model_width(model_width)
        self._set_global_wt(wt)
        
    #===================================================================
    # PRIVATE METHODS
    #===================================================================
    def _param_value_string(self, paramid, value, desc, units):
        """Creates a formated string that displays the value stored in
        a foundation parameter and it's unit.

        Parameters
        ----------
        paramid : str
            Parameter label
        value : numeric
            Value stored in the parameter.
        desc : str
            Description of the parameter
        units : str
            Units.

        Returns
        -------
        str
            Value stored in the parameter with the description of the
            parameter and its units.
        """
        fist_col_width = 35
        if value is None:
            return ''
        prefix = '  -{} = {:.2f}'.format(paramid, value)
        prefix = prefix + ' '* (fist_col_width - len(prefix))
        subsequent_indent = ' ' * fist_col_width
        wrapper = textwrap.TextWrapper(initial_indent=prefix,
                                       subsequent_indent=subsequent_indent,
                                       width=90)
        if units not in ['' , ' ']:
            desc += ' [{}]'.format(units)
        return '\n' + wrapper.fill(desc)

    def _set_soil_parameters(self, dstrata, model_depth):
        """Set soil layers.

        Parameters
        ----------
        dstrata : list, None
            Width of soil layers [m].
        """
        default_model_depth = self._d + 3 * self._b
        min_model_depth = self._d + 0.5 * self._b
        if dstrata is None:
            if model_depth is None:
                model_depth = default_model_depth
            elif model_depth < min_model_depth:
                model_depth = min_model_depth
            self._nstrata = 1
            self._dstrata = np.array([model_depth])
            self._zstrata = -np.cumsum(self._dstrata)
            self._model_depth = model_depth
            self._ylim = np.array([-model_depth, 0])
            return
        
        if isinstance(dstrata, numbers.Number):
            dstrata = [dstrata]
        dstrata = np.array(dstrata)
        default_model_depth = np.max([default_model_depth, np.sum(dstrata)])
        min_model_depth = np.max([default_model_depth, np.sum(dstrata)])

        if model_depth is None:
            model_depth = default_model_depth
            if np.sum(dstrata) < default_model_depth:
                dstrata[-1] = default_model_depth - np.sum(dstrata[:-1])
        elif model_depth < min_model_depth:
            model_depth = min_model_depth
            if np.sum(dstrata) < min_model_depth:
                dstrata[-1] = min_model_depth - np.sum(dstrata[:-1])
        elif np.sum(dstrata) < model_depth:
            dstrata[-1] = model_depth - np.sum(dstrata[:-1])
        
        self._dstrata = dstrata
        self._nstrata = len(dstrata)
        self._model_depth = model_depth
        self._ylim = np.array([-model_depth, 0])
        self._zstrata = -np.cumsum(dstrata)

    def _set_fill_parameters(self, fill_angle, nfill, dfill, bfill):
        """Set buried foundation fill.

        Parameters
        ----------
        fill_angle : float
            Fill angle [deg].
        nfill : int, None
            Number of fill layers. 
        dfill : list
            (nfill,) width of fill layers [m].
        bfill : float
            Distance between foundation edge and the start of the fill
            slope [m].

        Raises
        ------
        RuntimeError
            nfill and fill.
        """

        # surface foundaiton has no fill
        if self._d == 0 or fill_angle is None:
            self._nfill = None
            self._fill_angle = None
            self._dfill = None
            self._bfill = 0
            self._zfill = None
            return
 
        self._fill_angle = fill_angle
        self._bfill = bfill
        if nfill is not None and dfill is not None:
            raise RuntimeError('Either define the number of uniform fill layers <nfill> or their widhts <dfill>.')
        if nfill is None and dfill is None:
            nfill = 1
            dfill = np.array([self._d])
        if nfill is not None:
            nfill = nfill
            dfill = np.array([self._d / nfill] * nfill)
        if isinstance(dfill, numbers.Number):
            dfill = [dfill]
        dfill = np.array(dfill)
        dfill = dfill[np.cumsum(dfill) < self._d]
        dfill = np.concatenate([dfill, [self._d - np.sum(dfill)]])
        self._dfill = dfill
        self._nfill = len(dfill)
        self._zfill = -np.cumsum(dfill)

    def _set_excavation_parameters(self):
        if self._d == 0 or self._nfill is None:
            self._nexcavated = None
            self._dexcavated = None
            self._zexcavated = None
            return

        dexcavated = self._dstrata[np.cumsum(self._dstrata)<=self._d]
        if np.sum(dexcavated) < self._d:
            dexcavated = np.hstack([dexcavated, [self._d - np.sum(dexcavated)]])
        self._dexcavated = dexcavated
        self._nexcavated = len(dexcavated)
        self._zexcavated = -np.cumsum(dexcavated)
    
    def _set_ratchetting_parameters(self, dratchetting):
        """Set under base layer.

        Parameters
        ----------
        dratchetting : float, None
            Widht of soil under the foundation that is replaced when
            ratchetting occurs [m].
        """
        self._dratchetting = dratchetting

    def _set_model_width(self, model_width):
        """Sets the model width.

        Parameters
        ----------
        model_width : float, None
            User defiend model width [m].
        """
        default_model_width = np.max([1.5 * self._d, 2 * self._b])
        
        min_model_width = 1.1 * np.max([self._b - self._b2, self._b2]) #self._b / 2
        if self._fill_angle is not None:
            min_model_width = np.max([np.max([self._b - self._b2, self._b2])  + self._bfill + self._d / np.tan(np.radians(self._fill_angle)) + 0.5,
                                      min_model_width])
            default_model_width = np.max([min_model_width, default_model_width])
        
        if model_width is None:
            model_width = default_model_width
        else:
            model_width /= 2
        if model_width < min_model_width:
            model_width = min_model_width
        if self._symmetric:
            self._model_width = model_width
            self._xlim = np.array([0, model_width])
        else:
            self._model_width = 2 * model_width
            self._xlim = np.array([-model_width, model_width])
    
    def _set_global_wt(self, wt):
        """Sets water table.

        Parameters
        ----------
        wt : float, None
            Water tabe depth [m].
        """
        self._global_wt = None
        if wt is None:
            return
        self._global_wt = wt
    
    def _set_foundation_type(self, foundation_type):
        self._foundation_type = foundation_type
        #plate | surface | under | fill 
        foundation_types = {(True, True, False, False): [1, 'surface plate foundation with no underfill'],
                            (True, True, True, False): [2, 'surface plate foundation with underfill'],
                            (True, False, False, False): [1,'buried plate foundation with no fill or underfill'],
                            (True, False, True, False): [4 ,'buried plate foundation with underfill and no fill'],
                            (True, False, False, True): [6, 'buried plate foundation with fill and no underfill'],
                            (True, False, True, True): [7, 'buried plate foundation with fill and underfill'],
                            (False, True, False, False): [1,'surface solid foundation with not underfill'],
                            (False, True, True, False): [2, 'surface solid foundation with underfill'],
                            (False, False, False, False): [3, ' buried solid foundation with no fill or underfill'],
                            (False, False, True, False): [5, 'buried solid foundation with underfill and no fill'],
                            (False, False, False, True): [6, 'buried solid foundation with fill and no underfill'],
                            (False, False, True, True): [7, 'buried solid foundation with fill and underfill']}
        ftype =  foundation_types[self._foundation_type == 'plate', 
                                  self._d == 0,
                                  self._dratchetting != 0,
                                  self._nfill is not None]
        self._ftypeid = ftype[0]
        self._desc = ftype[1]

    def _set_polygons(self):
        self._polygons = []
        self._foundation = []
        self._strata = {new_list: [] for new_list in range(self._nstrata)}
        self._fill = None
        self._excavation = None
        self._ratchetting = None
        if self._nfill is not None:
            self._fill = {new_list: [] for new_list in range(self._nfill)}
            self._excavation = {new_list: [] for new_list in range(self._nstrata)}
        if self._dratchetting > 0:
            self._ratchetting = {new_list: [] for new_list in range(self._nstrata)}
        self._set_foundation_structures()
        self._set_fill_polygons()
        self._set_soil_polygons()
        self._set_ratchetting_polygons()

    @abstractmethod
    def _set_foundation_structures(self):
        return NotImplementedError

    def _set_fill_polygons(self):
        """Builds the model excavation and fill structures.
        """
        if self._dexcavated is None:
            return 
        z = np.flip(np.unique(np.hstack([[0, -self._d], self._zexcavated, self._zfill])))
        for idx in range(len(z)-1):
            vertex = self._get_fill_polygon_vertex(z[idx], z[idx + 1], 1)
            poly = Polygon(vertex)
            self._polygons.append(poly)
            poly_idx = len(self._polygons) -  1
            fill_idx = poly.in_strata(self._zfill)
            self._fill[fill_idx].append(poly_idx)
            excavation_idx = poly.in_strata(self._zexcavated)
            self._excavation[excavation_idx].append(poly_idx)
        if self._symmetric:
            return
        for idx in range(len(z)-1):
            vertex = self._get_fill_polygon_vertex(z[idx], z[idx + 1], -1)
            poly = Polygon(vertex)
            self._polygons.append(poly)
            poly_idx = len(self._polygons) -  1
            fill_idx = poly.in_strata(self._zfill)
            self._fill[fill_idx].append(poly_idx)
            excavation_idx = poly.in_strata(self._zexcavated)
            self._excavation[excavation_idx].append(poly_idx)
 
    @abstractmethod
    def _get_fill_polygon_vertex(self):
        return NotImplementedError
    
    def _set_soil_polygons(self):
        """Builds the model local soil structures.
        """
        z = np.flip(np.unique(np.hstack([[0, -self._model_depth], self._zstrata])))
        
        vertexfunc = {1:self._strata_case_1, 2:self._strata_case_2,
                      3:self._strata_case_3, 4:self._strata_case_4,
                      5:self._strata_case_5, 6:self._strata_case_6,
                      7:self._strata_case_7}
        for idx in range(len(z)-1):
            poly = Polygon(vertexfunc[self._ftypeid](z[idx], z[idx + 1], +1)) 
            self._polygons.append(poly)
            poly_idx = len(self._polygons) -  1
            strata_idx = poly.in_strata(self._zstrata)
            self._strata[strata_idx].append(poly_idx)
        if self._symmetric:
            return   
        for idx in range(len(z)-1):
            poly = Polygon(vertexfunc[self._ftypeid](z[idx], z[idx + 1], -1)) 
            self._polygons.append(poly)
            poly_idx = len(self._polygons) -  1
            strata_idx = poly.in_strata(self._zstrata)
            self._strata[strata_idx].append(poly_idx)
        
    def _x_fill(self, z, xsign):
        """X coordiante of fill slope given the depth.

        Parameters
        ----------
        z : float
            Depth [m].
        xsign : float
            Side of the foundation (<0) for left (>0) for right.
        
        Returns
        -------
        float
            x-coordinate.
        """
        if xsign > 0:
            x0 = self._b - self._b2 + self._bfill
            return -(-z - self._d) / np.tan(np.radians(self._fill_angle)) + x0
        x0 = - self._b2 - self._bfill
        return (-z - self._d) / np.tan(np.radians(self._fill_angle)) + x0
          
    def _strata_case_1(self, ztop, zbottom, xsign):
        """Strata for surface foundations without under-base or for
        buried plate foundation without ratchetting and fill.

        Parameters
        ----------
        ztop : float
            depth at the top of the strata [m].
        zbottom : float
            Depth at the bottom of the strata [m].
        xsign : float
            Side of the foundation (<0) for left (>0) for right.

        Returns
        -------
        np.ndarray
            (4, 2) strata polygon coordinates.
        """
        if xsign > 0:
            return np.array([[0, ztop],
                             [self._xlim[1], ztop],
                             [self._xlim[1], zbottom],
                             [0, zbottom]])
        return np.array([[0, ztop],
                         [self._xlim[0], ztop],
                         [self._xlim[0], zbottom],
                         [0, zbottom]])
         
    def _strata_case_2(self, ztop, zbottom, xsign):
        """Strata for surface foundations  with ratchetting.

        Parameters
        ----------
        ztop : float
            depth at the top of the strata [m].
        zbottom : float
            Depth at the bottom of the strata [m].
        xsign : float
            Side of the foundation (<0) for left (>0) for right. 

        Returns
        -------
        np.ndarray
            (nvertex, 2) strata polygon coordinates.
        """
        vertex = []
        if xsign > 0:
            xmin = self._b - self._b2 + self._bfill
            xmax = self._xlim[1]
        else:
            xmin = - self._b2 - self._bfill
            xmax = self._xlim[0]
        if ztop > -self._dratchetting and zbottom >= -self._dratchetting:
            vertex.append([xmin, ztop])
            vertex.append([xmax, ztop])
            vertex.append([xmax,  zbottom])
            vertex.append([xmin, zbottom])
        elif ztop > -self._dratchetting and zbottom < -self._dratchetting:
            vertex.append([xmin, ztop])
            vertex.append([xmax, ztop])
            vertex.append([xmax, zbottom])
            vertex.append([0, zbottom])
            vertex.append([0, -self._dratchetting])
            vertex.append([xmin, -self._dratchetting])
        elif ztop <= -self._dratchetting:
            vertex.append([0, ztop])
            vertex.append([xmax, ztop])
            vertex.append([xmax, zbottom])
            vertex.append([0, zbottom])
        return np.array(vertex)
    
    def _strata_case_3(self, ztop, zbottom, xsign):
        """Strata for buried solid foundations without under-base or
        fill.

        Parameters
        ----------
        ztop : float
            depth at the top of the strata [m].
        zbottom : float
            Depth at the bottom of the strata [m].
        xsign : float
            Side of the foundation (<0) for left (>0) for right. 

        Returns
        -------
        np.ndarray
            (nvertex, 2) strata polygon coordinates.
        """
        
        if xsign > 0:
            xcol = self._b1 / 2
            xfoot = self._b - self._b2
            xmodel = self._xlim[1]
        else:
            xcol = -self._b1 / 2
            xfoot = - self._b2
            xmodel = self._xlim[0]

        vertex = []
        if ztop > -self._d + self._d1:
            vertex.append([xcol, ztop])
            vertex.append([xmodel, ztop])
            vertex.append([xmodel, zbottom])
            if zbottom >= - self._d + self._d1:
                vertex.append([xcol, zbottom])
            elif zbottom > -self._d:
                vertex.append([xfoot, zbottom])
                vertex.append([xfoot, -self._d + self._d1])
                vertex.append([xcol, -self._d + self._d1])
            else:
                vertex.append([0,  zbottom])
                vertex.append([0, -self._d])
                vertex.append([xfoot, -self._d])
                vertex.append([xfoot, -self._d + self._d1])
                vertex.append([xcol, -self._d + self._d1])
        elif ztop > -self._d:
            vertex.append([xfoot, ztop])
            vertex.append([xmodel, ztop])
            vertex.append([xmodel, zbottom])
            if zbottom >= self._d:
                vertex.append([xfoot, zbottom])
            else:
                vertex.append([0, zbottom])
                vertex.append([0, -self._d])
                vertex.append([xfoot, -self._d])
        else:
            vertex.append([0, ztop])
            vertex.append([xmodel, ztop])
            vertex.append([xmodel, zbottom])
            vertex.append([0, zbottom])
        return np.array(vertex)
    
    def _strata_case_4(self, ztop, zbottom, xsign):
        """Strata for buried plate foundations with under-base and no
        fill.

        Parameters
        ----------
        ztop : float
            depth at the top of the strata [m].
        zbottom : float
            Depth at the bottom of the strata [m].
        xsign : float
            Side of the foundation (<0) for left (>0) for right.

        Returns
        -------
        np.ndarray
            (nvertex, 2) strata polygon coordinates.
        """
        
        if xsign > 0:
            xfoot = self._b - self._b2
            xmodel = self._xlim[1]
        else:
            xfoot = - self._b2
            xmodel = self._xlim[0]
        
        vertex = []
        if ztop > -self._d:
            vertex.append([0, ztop])
            vertex.append([xmodel, ztop])
            vertex.append([xmodel, zbottom])
            if zbottom >= -self._d:
                vertex.append([0,  zbottom])
            elif zbottom >= -self._d - self._dratchetting:
                vertex.append([xfoot,  zbottom])
                vertex.append([xfoot,  -self._d])
                vertex.append([0,  -self._d])
            else:
                vertex.append([0,  zbottom])
                vertex.append([0,  -self._d + self._dratchetting])
                vertex.append([xfoot,  -self._d +  self._dratchetting])
                vertex.append([xfoot,  -self._d])
                vertex.append([0,  -self._d])
        elif ztop > -self._d - self._dratchetting:
            vertex.append([xfoot, ztop])
            vertex.append([xmodel, ztop])
            vertex.append([xmodel,  zbottom])
            if zbottom > -self._d - self._dratchetting:
                vertex.append([xfoot,  zbottom])
            else:
                vertex.append([0,  zbottom])
                vertex.append([0,  -self._d - self._dratchetting])
                vertex.append([xfoot,  -self._d - self._dratchetting])
        else:
            vertex.append([0, ztop])
            vertex.append([xmodel,  ztop])
            vertex.append([xmodel,  zbottom])
            vertex.append([0,  zbottom])
        return np.array(vertex)
    
    def _strata_case_5(self, ztop, zbottom, xsign):
        """Strata for buried solid foundations with under-base and no
        fill.

        Parameters
        ----------
        ztop : float
            depth at the top of the strata [m].
        zbottom : float
            Depth at the bottom of the strata [m].
        xsign : float
            Side of the foundation (<0) for left (>0) for right. 

        Returns
        -------
        np.ndarray
            (nvertex, 2) strata polygon coordinates.
        """
        
        if xsign > 0:
            xcol = self._b1 / 2
            xfoot = self._b - self._b2
            xmodel = self._xlim[1]
        else:
            xcol = -self._b1 / 2
            xfoot = - self._b2
            xmodel = self._xlim[0]
        
        vertex = []
        if ztop > -self._d + self._d1:
            vertex.append([xcol, ztop])
            vertex.append([xmodel, ztop])
            vertex.append([xmodel,  zbottom])
            if zbottom >= -self._d + self._d1:
                vertex.append([xcol,  zbottom])
            elif zbottom >= self._d + self._dratchetting:
                vertex.append([xfoot,  zbottom])
                vertex.append([xfoot,  -self._d + self._d1])
                vertex.append([xcol,  -self._d + self._d1])
            else:
                vertex.append([0,  zbottom])
                vertex.append([0,  -self._d - self._dratchetting])
                vertex.append([xfoot,  -self._d - self._dratchetting])
                vertex.append([xfoot,  -self._d + self._d1])
                vertex.append([xcol,  -self._d + self._d1])
        elif ztop > -self._d - self._dratchetting:
            vertex.append([self._b / 2, ztop])
            vertex.append([xmodel, ztop])
            vertex.append([xmodel,  zbottom])
            if zbottom >= -self._d - self._dratchetting:
                vertex.append([xfoot,  zbottom])
            else:
                vertex.append([0,  zbottom])
                vertex.append([0,  -self._d - self._dratchetting])
                vertex.append([xfoot,  -self._d - self._dratchetting])
        else:
            vertex.append([0, ztop])
            vertex.append([xmodel,  ztop])
            vertex.append([xmodel,  zbottom])
            vertex.append([0,  zbottom])
        return np.array(vertex)
    
    def _strata_case_6(self, ztop, zbottom, xsign):
        """vertex for buried foundations with fill and no under-base.

        Parameters
        ----------
        ztop : float
            depth at the top of the strata [m].
        zbottom : float
            Depth at the bottom of the strata [m].
        xsign : float
            Side of the foundation (<0) for left (>0) for right. 

        Returns
        -------
        np.ndarray
            (nvertex, 2) vertex polygon coordinates.
        """

        if xsign > 0:
            xratch = self._b - self._b2 + self._bfill
            xmodel = self._xlim[1]
        else:
            xratch = - self._b2 - self._bfill
            xmodel = self._xlim[0]

        vertex = []
        if ztop > -self._d:
            vertex.append([self._x_fill(ztop, xsign),  ztop])
            vertex.append([xmodel,  ztop])
            vertex.append([xmodel,  zbottom])
            if zbottom >= -self._d:
                vertex.append([self._x_fill(zbottom, xsign),  zbottom])
            else:
                vertex.append([0,  zbottom])
                vertex.append([0,  -self._d])
                vertex.append([xratch,  -self._d])
        else:
            vertex.append([0, ztop])
            vertex.append([xmodel,  ztop])
            vertex.append([xmodel,  zbottom])
            vertex.append([0,  zbottom])

        return np.array(vertex)
    
    def _strata_case_7(self, ztop, zbottom, xsign):
        """vertex for buried foundations with fill and under-base.

        Parameters
        ----------
        ztop : float
            depth at the top of the strata [m].
        zbottom : float
            Depth at the bottom of the strata [m].
        xsign : float
            Side of the foundation (<0) for left (>0) for right. 

        Returns
        -------
        np.ndarray
            (nvertex, 2) vertex polygon coordinates.
        """

        if xsign > 0:
            xratch = self._b - self._b2 + self._bfill
            xmodel = self._xlim[1]
        else:
            xratch = - self._b2 - self._bfill
            xmodel = self._xlim[0]

        vertex = []
        if ztop > -self._d:
            vertex.append([self._x_fill(ztop, xsign),  ztop])
            vertex.append([xmodel,  ztop])
            vertex.append([xmodel,  zbottom])
            if zbottom >= -self._d:
                vertex.append([self._x_fill(zbottom,  xsign),  zbottom])
            elif zbottom >= -self._d - self._dratchetting:
                vertex.append([xratch,  zbottom])
                vertex.append([xratch,  -self._d])
            else:
                vertex.append([0,  zbottom])
                vertex.append([0,  -self._d - self._dratchetting])
                vertex.append([xratch,  -self._d - self._dratchetting])
                vertex.append([xratch,  -self._d])
        elif ztop > -self._d - self._dratchetting:
            vertex.append([xratch,  ztop])
            vertex.append([xmodel,  ztop])
            vertex.append([xmodel,  zbottom])
            if zbottom >= -self._d - self._dratchetting:
                vertex.append([xratch,  zbottom])
            else:
                vertex.append([0,  zbottom])
                vertex.append([0,  -self._d - self._dratchetting])
                vertex.append([xratch,  -self._d - self._dratchetting])
        else:
            vertex.append([0, ztop])
            vertex.append([xmodel,  ztop])
            vertex.append([xmodel,  zbottom])
            vertex.append([0,  zbottom])
        return np.array(vertex)

    def _set_ratchetting_polygons(self):
        """Builds the model ratchetting structures.
        """
        if self._dratchetting is None:
            return
        z = np.hstack([[-self._d, -self._d - self._dratchetting] , self._zstrata])
        z = z[z >= -self._d - self._dratchetting]
        z = z[z <= -self._d]
        z = np.flip(np.unique(z))
        xmin = 0
        xmax = self._b - self._b2 + self._bfill
        if not self._symmetric:
            xmin = - self._b2 - self._bfill
        for idx in range(len(z)-1):
            vertex = [[xmin,  z[idx]],
                      [xmax,  z[idx]],
                      [xmax,  z[idx + 1]],
                      [xmin,  z[idx + 1]]]
            poly = Polygon(vertex)
            self._polygons.append(poly)
            poly_idx = len(self._polygons) -  1
            rat_idx = poly.in_strata(self._zstrata)
            self._ratchetting[rat_idx].append(poly_idx)

    def _plot_poly(self, polyidx, others=True, figsize=4):
        """Plots polygons.

        Parameters
        ----------
        polyidx : numeric, array-like
            Polygon indexes.
        others : bool, optional
            If True the remaining polygons are plotted in grey, by
            default True.
        figsize : float, optional
            Figure width [inch], by default 4

        Returns
        -------
        Figure
            Figure with the polygons plot.
        """
        if isinstance(polyidx, numbers.Number):
            polyidx = [polyidx]
        polyidx = np.unique(polyidx)

        allpoly = list(range(len(self._polygons)))
        for idx in polyidx:
            allpoly.remove(idx)

        patches = []
        colors = []
        lw = []
        for idx in polyidx:
            patches.append(PatchPolygon(self._polygons[idx]._vertex, True))
            colors += [DEFAULT_CYCLE[idx % len(DEFAULT_CYCLE)]]
            lw += [2]
        if others:
            for idx in allpoly:
                patches.append(PatchPolygon(self._polygons[idx]._vertex, True))
                colors += ['lightgray']
                lw += [1]
        
        fig, ax = plt.subplots(1, 1, figsize=(figsize, figsize * self._model_depth/self._model_width))
        p = PatchCollection(patches, alpha=0.7, facecolor=colors, lw=lw, edgecolor='k')
        ax.add_collection(p)
        ax.set_xlim(1.1 * self._xlim)
        ax.set_ylim(1.1 * self._ylim)
        ax.grid(alpha=0.4)
        plt.close(fig)
        return fig
    
    #===================================================================
    # PUBLIC METHODS
    #===================================================================
    def plot(self, figsize=4, foundation=True, fill=True, soil=True,
             excavation=False, ratchetting=True, wt=True, interface=False,
             output_location=False):
        """Foundation plot.

        Parameters
        ----------
        figsize : float, optional
            Figure width [inch], by default 2.5
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
        output_location : bool, optional
            Show output locations. By default False.

        Returns
        -------
        Figure
            Figure with the foundation plot.
        """
        fig, ax = plt.subplots(1, 1, figsize=(figsize, figsize * self._model_depth/self._model_width))

        patches = []
        colors = []
        if foundation  and self._foundation_type=='solid':
            for polyidx in self._foundation:
                patches.append(PatchPolygon(self._polygons[polyidx]._vertex, True))
                colors += ['gray']
        if self._nfill is not None and fill:
            fill_colors = ['greenyellow', 'yellowgreen']
            for fill_idx in self._fill:
                for polyidx in self._fill[fill_idx]:
                    patches.append(PatchPolygon(self._polygons[polyidx]._vertex, True))
                    colors += [fill_colors[fill_idx % 2]]
        elif self._nfill is not None and excavation:
            exc_colors = ['goldenrod', 'darkgoldenrod']
            for exc_idx in self._excavation:
                for polyidx in self._excavation[exc_idx]:
                    patches.append(PatchPolygon(self._polygons[polyidx]._vertex, True))
                    colors += [exc_colors[exc_idx % 2]]
        if soil:
            strata_colors = ['darkolivegreen', 'olivedrab']
            for strata_idx in self._strata:
                for polyidx in self._strata[strata_idx]:
                    patches.append(PatchPolygon(self._polygons[polyidx]._vertex, True))
                    colors += [strata_colors[strata_idx % 2]]
        if ratchetting and soil and self._ratchetting is not None:
            strata_colors = ['darkolivegreen', 'olivedrab']
            for under_idx in self._ratchetting:
                for polyidx in self._ratchetting[under_idx]:
                    patches.append(PatchPolygon(self._polygons[polyidx]._vertex, True))
                    colors += [strata_colors[under_idx % 2]]

        if len(patches) > 0:
            p = PatchCollection(patches, alpha=.4, facecolor=colors, lw=1, edgecolor='k')
            ax.add_collection(p)

        # plate foundation    
        if foundation and self._foundation_type=='plate':
            ax.plot(self._foundation[:, 0], self._foundation[:, 1],'-', color='grey', lw=10, zorder=2)

        # interfaces
        if interface:
            for interface in self._interfaces.values():
                if interface._active:
                    ax.plot(interface._vertex[:, 0], interface._vertex[:, 1], '--', color='red', lw=3, zorder=3)

        # water table
        if self._global_wt is not None and wt:
            ax.plot(self._xlim, [-self._global_wt, -self._global_wt], '-b', lw=3, zorder=4)

        # output locations
        if output_location and hasattr(self, '_output_location_xcoord'):
            for xcoord in self._output_location_xcoord:
                ax.plot(xcoord, -self._d, 'ok', ms=6)
            if self._d1 is None:
                ax.plot(0, 0, 'ok', ms=6)
            elif self._d - self._d1 > 0:
                ax.plot(0, 0, 'ok', ms=6)
            else:
                ax.plot(0, self._d - self._d1, 'ok', ms=6)

        ax.set_xlim(1.1 * self._xlim)

        ylim = copy.deepcopy(1.1 * self._ylim)
        if ylim[1]==0:
            ylim[1] = 0.5
        ax.set_ylim(ylim)

        ax.grid(alpha=0.4)
        plt.close(fig)
        return fig
