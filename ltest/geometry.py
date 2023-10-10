import copy
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as PatchPolygon
from matplotlib.collections import PatchCollection
import numbers
import numpy as np
import textwrap

from ltest.polygon import Polygon

class Geometry():

    def __init__(self, g_i, b, d, foundation_type='plate', b1=None,
                 d1=None, dstrata=None, wt=None, fill_angle=None, bfill=0.5,
                 nfill=None, dfill=None, dunder=None):
        """Init mehtod.

        Parameters
        ----------
        b : float
            foundation width [m].
        d : float
            foundation depth [m]
        foundation_type : str
            'plate' or 'solid'
        b1 : float, None
            foundation column widht [m]
        d1 : float, None
            foundation width [m]
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
        dunder : float, None
            Under base layer width [m].
        """
        self._set_foundation(b, d, b1, d1, foundation_type)
        self._set_soil(dstrata)
        self._set_fill(fill_angle, nfill, dfill, bfill)
        self._set_excavated()
        self._set_under_base(dunder)
        self._set_model_width()
        self._set_wt(wt)
        self._set_foundation_type()
        self._build_polygons(g_i)

    #===================================================================
    # PRIVATE METHODS
    #===================================================================
    def __repr__(self):
        """Repr method.

        Returns
        -------
        str
            Descrittion of the foundation.
        """
        txt = ''
        txt += self._desc + ':\n'
        txt += self._param_value_string('d', self._d, 'foundation depth', 'm')
        txt += self._param_value_string('b', self._b, 'foundation width', 'm')
        txt += self._param_value_string('b1', self._b1, 'column width', 'm')
        txt += self._param_value_string('d1', self._d1, 'foundation thickness', 'm')
        txt += self._param_value_string('dunder', self._dunder, 'foundation underbase thickness', 'm')
        txt += self._param_value_string('fill_angle', self._fill_angle, 'fill angle', 'deg')
        txt += self._param_value_string('bfill', self._bfill, 'distance between foundation edge and the start of the fill slope', 'm')
        txt += self._param_value_string('wt', self._wt, 'water table depth', 'm')
        return txt
    
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

    def _set_foundation(self, b, d, b1, d1, foundation_type):
        """Set foundation geoemtry

        Parameters
        ----------
        b : float
            Foundation width [m].
        d : float
            Foundation depth [m].
        b1 : float, None
            Foundation column widht [m]
        d1 : float, None
            Foundation width [m]
        foundation_type : str
            'plate' or 'solid'

        Raises
        ------
        RuntimeError
            Solid foundaiton without d1.
        RuntimeError
            Soild foundation without b1 or d1.
        """
        self._b = b
        self._d = d
        self._b1 = b1
        self._d1 = d1
        self._foundation_type = foundation_type
        if foundation_type == 'solid':
            if d==0 and d1 is None:
                raise RuntimeError('d1 must be specified in a solid model located at the surface.')
            elif d1 is None or b1 is None:
                raise RuntimeError('b1 and d1 must be specified in a buried solid model.')

    def _set_soil(self, dstrata):
        """Set soil layers.

        Parameters
        ----------
        dstrata : list, None
            Width of soil layers [m].
        """
        model_depth = self._d + 3 * self._b
        if dstrata is None:
            self._nstrata = 1
            self._dstrata = np.array([model_depth])
            self._zstrata = -np.cumsum(self._dstrata)
            self._model_depth = model_depth
            return
        
        if isinstance(dstrata, numbers.Number):
            dstrata = [dstrata]
        dstrata = np.array(dstrata)
        model_depth = np.max([model_depth, np.sum(dstrata)])
        if np.sum(dstrata) < model_depth:
            dstrata[-1] = model_depth - np.sum(dstrata[:-1])
        self._dstrata = dstrata
        self._nstrata = len(dstrata)
        self._model_depth = model_depth
        self._zstrata = -np.cumsum(dstrata)

    def _set_fill(self, fill_angle, nfill, dfill, bfill):
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
            self._fill = None
            self._zfill = None
            return
 
        self._fill_angle = fill_angle
        self._bfill = bfill
        if nfill is None and dfill is None:
            self._nfill = 1
            self._dfill = np.array([self._d])
            return
        if nfill is not None and dfill is not None:
            raise RuntimeError('Either define the number of uniform fill layers <nfill> or their widhts <dfill>.')
        if nfill is not None:
            self._nfill = nfill
            self._dfill = np.array([self._d / self._nfill] * self._nfill)
            return
        if isinstance(dfill, numbers.Number):
            dfill = [dfill]
        dfill = np.array(dfill)
        dfill = dfill[np.cumsum(dfill) < self._d]
        dfill = np.concatenate([dfill, [self._d - np.sum(dfill)]])
        self._dfill = dfill
        self._nfill = len(dfill)
        self._zstrata = -np.cumsum(dfill)

    def _set_excavated(self):
        if self._d == 0 or self._fill is None:
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
    
    def _set_under_base(self, dunder):
        """Set under base layer.

        Parameters
        ----------
        dunder : float, None
            Under base layer width [m].
        """
        self._dunder = dunder

    def _set_model_width(self):
        model_width = np.max([1.5 * self._d, 2 * self._b])
        if self._fill_angle is not None:
            model_width = np.max([self._b / 2 + self._bfill + self._d / np.tan(np.radians(self._fill_angle)) + 0.5,
                                  model_width])
        self._model_width = model_width
    
    def _set_wt(self, wt):
        """Sets water table.

        Parameters
        ----------
        wt : float, None
            Water tabe depth [m].
        """
        self._wt = None
        if wt is None:
            return
        self._wt = -wt
    
    def _set_foundation_type(self):
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
                                  self._dunder is not None,
                                  self._fill is not None]
        self._ftypeid = ftype[0]
        self._desc = ftype[1]

    def _build_polygons(self, g_i):
        self._polygons = []
        self._structure_polygons = []
        self._structure_soil = []
        self._phase_polygons = []
        self._foundation = []
        if self._fill is not None:
            self._fill = dict(zip(list(range(self._nfill)), [[]]*self._nfill))
            self._excavated = dict(zip(list(range(self._nexcavated)), [[]]*self._nexcavated))
        self._strata = dict(zip(list(range(self._nstrata)), [[]]*self._nstrata))
        self._underbase = []
        self._build_foundation(g_i)
        self._build_excavation(g_i)
        self._build_strata(g_i)
    
    def _build_foundation(self, g_i):
        if self._foundation_type == 'plate':
            self._build_foundation_plates(g_i)
            return
        self._foundation = None
        self._column = None
        self._footing = None
        z = np.flip(np.unique(np.hstack([[0, -self._d], self._zexcavated, self._zfill])))
        for idx in range(len(z)-1):
            self._build_foundation_polygon(g_i, z[idx], z[idx + 1])
            
    def _build_foundation_plates(self, g_i):
        if self._d == 0:
            self._foundation = np.array([[0, 0],
                                         [self._b / 2, 0]])
            self._column = None
            self._footing = np.array([[0, 0],
                                      [self._b / 2, 0]])
            return
        else:
            self._foundation = np.array([[0, 0],
                                         [0, -self._d],
                                         [self._b / 2, -self._d]])
            self._column = np.array([[0, 0],
                                     [0, -self._d]])
            self._footing = np.array([[0, -self._d],
                                      [self._b / 2, -self._d]])
    
    def _build_foundation_polygon(self, g_i, ztop, zbottom):
        vertex = [0, ztop]
        if ztop > - self._d + self._d1:
            vertex.append([self._b1 / 2, ztop])
            if zbottom >= - self._d + self._d1:
                vertex.append([self._b1 / 2, zbottom])
            else:
                vertex.append([self._b1 / 2, - self._d + self._d1])
                vertex.append([self._b / 2, - self._d + self._d1])
                vertex.append([self._b1 / 2, zbottom])
        else:
            vertex.append([self._b / 2, ztop])
            vertex.append([self._b / 2, zbottom])
        vertex.append([0, zbottom])
        poly = Polygon(vertex)
        self._polygons.append(poly)
        struct_poly, struct_soil, phase_poly = poly.add_2_model(g_i)
        self._structure_polygons.append(struct_poly)
        self._structure_soil.append(struct_soil)
        self._phase_polygons.append(phase_poly)

        poly_idx = len(self._structure_polygons)

        self._foundation.append(poly_idx)
        strata_idx = poly.in_strata(self._zstrata)
        self._strata[strata_idx].append(poly_idx)
        if self._fill is not None:
            fill_idx = poly.in_strata(self._zfill)
            self._fill[fill_idx].append(poly_idx)
            excavation_idx = poly.in_strata(self._zexcavated)
            self._excavated[excavation_idx].append(poly_idx)

    def _build_excavation(self, g_i):
        if self._dexcavated is None:
            return 
        z = np.flip(np.unique(np.hstack([[0, -self._d], self._zexcavated, self._zfill])))
        for idx in range(len(z)-1):
            self._build_excavation_polygon(g_i, z[idx], z[idx + 1])

    def _build_excavation_polygon(self, g_i, ztop, zbottom):
        vertex = []
        if self._foundation_type == 'plate':            
            vertex.apppend([0, ztop])
            vertex.apppend([self._x_fill(ztop), ztop])
            vertex.apppend([self._x_fill(zbottom), zbottom])
            vertex.apppend([0, zbottom])
        else:
            if ztop > -self._d + self._d1:
                vertex.apppend([self._b1 / 2, ztop])
            else:
                vertex.apppend([self._d1 / 2, ztop])
            vertex.apppend([self._x_fill(ztop), ztop])
            vertex.apppend([self._x_fill(zbottom), zbottom])
            if zbottom > -self._d + self._d1:
                vertex.apppend([self._b1 / 2, zbottom])
            else:
                vertex.apppend([self._d1 / 2, zbottom])
                if ztop > -self._d + self._d1:
                    vertex.apppend([self._d1 / 2, -self._d + self._d1])
                    vertex.apppend([self._b1 / 2, -self._d + self._d1])

        poly = Polygon(vertex)
        self._polygons.append(poly)
        struct_poly, struct_soil, phase_poly = poly.add_2_model(g_i)
        self._structure_polygons.append(struct_poly)
        self._structure_soil.append(struct_soil)
        self._phase_polygons.append(phase_poly)

        poly_idx = len(self._structure_polygons)
        
        strata_idx = poly.in_strata(self._zstrata)
        self._strata[strata_idx].append(poly_idx)

        fill_idx = poly.in_strata(self._zfill)
        self._fill[fill_idx].append(poly_idx)

        excavation_idx = poly.in_strata(self._zexcavated)
        self._excavated[excavation_idx].append(poly_idx)
 
    def _build_under_base(self, dunder):
        """Set under base layer.

        Parameters
        ----------
        dunder : float, None
            Under base layer width [m].
        """
        self._dunder = dunder
        self._under = None
        if dunder is None:
            return
        self._under = [[0, self._model_depth - self._d],
                       [self._b / 2 + self._bfill, self._model_depth - self._d],
                       [self._b / 2 + self._bfill, self._model_depth - self._d - self._dunder],
                       [0, self._model_depth - self._d - self._dunder]]
        self._under = np.array(self._under)

    def _build_strata(self, g_i):
        z = np.flip(np.unique(np.hstack([[0, -self._model_depth], self._zstrata])))
        for idx in range(len(z)-1):
            self._build_strata_polygon(g_i, z[idx], z[idx + 1])

    def _build_strata_polygon(self, g_i, ztop, zbottom):
        func = {1:self._strata_case_1, 2:self._strata_case_2,
                3:self._strata_case_3, 4:self._strata_case_4,
                5:self._strata_case_5, 6:self._strata_case_6,
                7:self._strata_case_7}
        
        poly = Polygon(func[self._ftypeid](ztop, zbottom)) 
        self._polygons.append(poly)
        struct_poly, struct_soil, phase_poly = poly.add_2_model(g_i)
        self._structure_polygons.append(struct_poly)
        self._structure_soil.append(struct_soil)
        self._phase_polygons.append(phase_poly)

        poly_idx = len(self._structure_polygons)

        strata_idx = poly.in_strata(self._zstrata)
        self._strata[strata_idx].append(poly_idx)

    def _x_fill(self, z):
        """X coordiante of fill slope given the depth.

        Parameters
        ----------
        z : float
            Depth [m].

        Returns
        -------
        float
            x-coordinate.
        """
        x0 = self._b / 2 + self._bfill
        return -(-z - self._d) / np.tan(np.radians(self._fill_angle)) + x0
      
    def _strata_case_1(self, ytop, ybottom):
        """Strata for surface foundations without under-base or for
        buried plate foundation without underbase and fill.

        Parameters
        ----------
        ytop : float
            depth at the top of the strata.
        ybottom : float
            Depth at the bottom of the strata. 

        Returns
        -------
        np.ndarray
            (4, 2) strata polygon coordinates.
        """
        vertex = np.array([[0, self._model_depth - ytop],
                           [self._model_width, self._model_depth - ytop],
                           [self._model_width, self._model_depth - ybottom],
                           [0, self._model_depth - ybottom]])
        return vertex
    
    def _strata_case_2(self, ytop, ybottom):
        """Strata for surface foundations without under-base or for
        buried plate foundation wit underbase and no fill.

        Parameters
        ----------
        ytop : float
            depth at the top of the strata.
        ybottom : float
            Depth at the bottom of the strata. 

        Returns
        -------
        np.ndarray
            (nvertex, 2) strata polygon coordinates.
        """
        vertex = []
        if ytop < self._dunder and ybottom <= self._dunder:
            vertex.append([self._b / 2, self._model_depth -ytop])
            vertex.append([self._model_width, self._model_depth - ytop])
            vertex.append([self._model_width, self._model_depth - ybottom])
            vertex.append([self._b / 2, self._model_depth - ybottom])
        elif ytop < self._dunder and ybottom > self._dunder:
            vertex.append([self._b / 2, self._model_depth -ytop])
            vertex.append([self._model_width, self._model_depth - ytop])
            vertex.append([self._model_width, self._model_depth - ybottom])
            vertex.append([0, self._model_depth - ybottom])
            vertex.append([0, self._model_depth - self._dunder])
            vertex.append([self._b / 2, self._model_depth - self._dunder])
        elif ytop >= self._dunder:
            vertex.append([0, self._model_depth -ytop])
            vertex.append([self._model_width, self._model_depth - ytop])
            vertex.append([self._model_width, self._model_depth - ybottom])
            vertex.append([0, self._model_depth - ybottom])
        return np.array(vertex)
    
    def _strata_case_3(self, ytop, ybottom):
        """Strata for buried solid foundations without under-base or
        fill.

        Parameters
        ----------
        ytop : float
            depth at the top of the strata.
        ybottom : float
            Depth at the bottom of the strata. 

        Returns
        -------
        np.ndarray
            (nvertex, 2) strata polygon coordinates.
        """
        vertex = []
        if ytop < self._d - self._d1:
            vertex.append([self._b1 / 2, self._model_depth -ytop])
            vertex.append([self._model_width, self._model_depth -ytop])
            vertex.append([self._model_width, self._model_depth - ybottom])
            if ybottom <= self._d - self._d1:
                vertex.append([self._b1/2, self._model_depth - ybottom])
            elif ybottom <= self._d:
                vertex.append([self._b/2, self._model_depth - ybottom])
                vertex.append([self._b/2, self._model_depth - self._d + self._d1])
                vertex.append([self._b1/2, self._model_depth - self._d + self._d1])
            else:
                vertex.append([0, self._model_depth - ybottom])
                vertex.append([0, self._model_depth - self._d])
                vertex.append([self._b/2, self._model_depth - self._d])
                vertex.append([self._b/2, self._model_depth - self._d + self._d1])
                vertex.append([self._b1/2, self._model_depth - self._d + self._d1])
        elif ytop < self._d:
            vertex.append([self._b / 2, self._model_depth -ytop])
            vertex.append([self._model_width, self._model_depth -ytop])
            vertex.append([self._model_width, self._model_depth - ybottom])
            if ybottom <= self._d:
                vertex.append([self._b/2, self._model_depth - ybottom])
            else:
                vertex.append([0, self._model_depth - ybottom])
                vertex.append([0, self._model_depth - self._d])
                vertex.append([self._b/2, self._model_depth - self._d])
        else:
            vertex.append([0, self._model_depth -ytop])
            vertex.append([self._model_width, self._model_depth - ytop])
            vertex.append([self._model_width, self._model_depth - ybottom])
            vertex.append([0, self._model_depth - ybottom])
        return np.array(vertex)
    
    def _strata_case_4(self, ytop, ybottom):
        """Strata for buried plate foundations with under-base and no
        fill.

        Parameters
        ----------
        ytop : float
            depth at the top of the strata.
        ybottom : float
            Depth at the bottom of the strata. 

        Returns
        -------
        np.ndarray
            (nvertex, 2) strata polygon coordinates.
        """
        vertex = []
        if ytop < self._d:
            vertex.append([0, self._model_depth -ytop])
            vertex.append([self._model_width, self._model_depth -ytop])
            vertex.append([self._model_width, self._model_depth - ybottom])
            if ybottom <= self._d:
                vertex.append([0, self._model_depth - ybottom])
            elif ybottom <= self._d + self._dunder:
                vertex.append([self._b/2, self._model_depth - ybottom])
                vertex.append([self._b/2, self._model_depth - self._d])
                vertex.append([0, self._model_depth - self._d])
            else:
                vertex.append([0, self._model_depth - ybottom])
                vertex.append([0, self._model_depth - self._d -  self._dunder])
                vertex.append([self._b/2, self._model_depth - self._d -  self._dunder])
                vertex.append([self._b/2, self._model_depth - self._d])
                vertex.append([0, self._model_depth - self._d])
        elif ytop < self._d + self._dunder:
            vertex.append([self._b / 2, self._model_depth -ytop])
            vertex.append([self._model_width, self._model_depth -ytop])
            vertex.append([self._model_width, self._model_depth - ybottom])
            if ybottom <= self._d + self._dunder:
                vertex.append([self._b / 2, self._model_depth - ybottom])
            else:
                vertex.append([0, self._model_depth - ybottom])
                vertex.append([0, self._model_depth - self._d - self._dunder])
                vertex.append([self._b / 2, self._model_depth - self._d - self._dunder])
        else:
            vertex.append([0, self._model_depth -ytop])
            vertex.append([self._model_width, self._model_depth - ytop])
            vertex.append([self._model_width, self._model_depth - ybottom])
            vertex.append([0, self._model_depth - ybottom])
        return np.array(vertex)
    
    def _strata_case_5(self, ytop, ybottom):
        """Strata for buried solid foundations with under-base and no
        fill.

        Parameters
        ----------
        ytop : float
            depth at the top of the strata.
        ybottom : float
            Depth at the bottom of the strata. 

        Returns
        -------
        np.ndarray
            (nvertex, 2) strata polygon coordinates.
        """
        vertex = []
        if ytop < self._d - self._d1:
            vertex.append([self._b1 / 2, self._model_depth -ytop])
            vertex.append([self._model_width, self._model_depth -ytop])
            vertex.append([self._model_width, self._model_depth - ybottom])
            if ybottom <= self._d - self._d1:
                vertex.append([self._b1/2, self._model_depth - ybottom])
            elif ybottom <= self._d + self._dunder:
                vertex.append([self._b/2, self._model_depth - ybottom])
                vertex.append([self._b/2, self._model_depth - self._d + self._d1])
                vertex.append([self._b1/2, self._model_depth - self._d + self._d1])
            else:
                vertex.append([0, self._model_depth - ybottom])
                vertex.append([0, self._model_depth - self._d - self._dunder])
                vertex.append([self._b/2, self._model_depth - self._d - self._dunder])
                vertex.append([self._b/2, self._model_depth - self._d + self._d1])
                vertex.append([self._b1/2, self._model_depth - self._d + self._d1])
        elif ytop < self._d + self._dunder:
            vertex.append([self._b / 2, self._model_depth -ytop])
            vertex.append([self._model_width, self._model_depth -ytop])
            vertex.append([self._model_width, self._model_depth - ybottom])
            if ybottom <= self._d + self._dunder:
                vertex.append([self._b/2, self._model_depth - ybottom])
            else:
                vertex.append([0, self._model_depth - ybottom])
                vertex.append([0, self._model_depth - self._d - self._dunder])
                vertex.append([self._b/2, self._model_depth - self._d - self._dunder])
        else:
            vertex.append([0, self._model_depth -ytop])
            vertex.append([self._model_width, self._model_depth - ytop])
            vertex.append([self._model_width, self._model_depth - ybottom])
            vertex.append([0, self._model_depth - ybottom])
        return np.array(vertex)
    
    def _strata_case_6(self, ytop, ybottom):
        """vertex for buried foundations with fill and no under-base.

        Parameters
        ----------
        ytop : float
            depth at the top of the strata.
        ybottom : float
            Depth at the bottom of the strata. 

        Returns
        -------
        np.ndarray
            (nvertex, 2) vertex polygon coordinates.
        """

        vertex = []
        if ytop < self._d:
            vertex.append([self._x_fill(ytop), self._model_depth - ytop])
            vertex.append([self._model_width, self._model_depth - ytop])
            vertex.append([self._model_width, self._model_depth - ybottom])
            if ybottom <= self._d:
                vertex.append([self._x_fill(ybottom), self._model_depth - ybottom])
            else:
                vertex.append([0, self._model_depth - ybottom])
                vertex.append([0, self._model_depth - self._d])
                vertex.append([self._b /2 + self._bfill, self._model_depth - self._d])
        else:
            vertex.append([0, self._model_depth -ytop])
            vertex.append([self._model_width, self._model_depth - ytop])
            vertex.append([self._model_width, self._model_depth - ybottom])
            vertex.append([0, self._model_depth - ybottom])

        return np.array(vertex)
    
    def _strata_case_7(self, ytop, ybottom):
        """vertex for buried foundations with fill and under-base.

        Parameters
        ----------
        ytop : float
            depth at the top of the strata.
        ybottom : float
            Depth at the bottom of the strata. 

        Returns
        -------
        np.ndarray
            (nvertex, 2) vertex polygon coordinates.
        """

        vertex = []
        if ytop < self._d:
            vertex.append([self._x_fill(ytop), self._model_depth - ytop])
            vertex.append([self._model_width, self._model_depth - ytop])
            vertex.append([self._model_width, self._model_depth - ybottom])
            if ybottom <= self._d:
                vertex.append([self._x_fill(ybottom), self._model_depth - ybottom])
            elif ybottom <= self._d + self._dunder:
                vertex.append([self._b / 2 + self._bfill, self._model_depth - ybottom])
                vertex.append([self._b / 2 + self._bfill, self._model_depth - self._d])
            else:
                vertex.append([0, self._model_depth - ybottom])
                vertex.append([0, self._model_depth - self._d - self._dunder])
                vertex.append([self._b /2 + self._bfill, self._model_depth - self._d - self._dunder])
                vertex.append([self._b /2 + self._bfill, self._model_depth - self._d])
        elif ytop < self._d + self._dunder:
            vertex.append([self._b / 2 + self._bfill, self._model_depth - ytop])
            vertex.append([self._model_width, self._model_depth - ytop])
            vertex.append([self._model_width, self._model_depth - ybottom])
            if ybottom <= self._d + self._dunder:
                vertex.append([self._b / 2 + self._bfill, self._model_depth - ybottom])
            else:
                vertex.append([0, self._model_depth - ybottom])
                vertex.append([0, self._model_depth - self._d - self._dunder])
                vertex.append([self._b /2 + self._bfill, self._model_depth - self._d - self._dunder])
        else:
            vertex.append([0, self._model_depth -ytop])
            vertex.append([self._model_width, self._model_depth - ytop])
            vertex.append([self._model_width, self._model_depth - ybottom])
            vertex.append([0, self._model_depth - ybottom])
        return np.array(vertex)
    
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
        fig, ax = plt.subplots(1, 1, figsize=(figsize, figsize * self._model_depth/self._model_width))

        patches = []
        colors = []
        for poly in self._polygons:
            patches.append(PatchPolygon(poly._vertex, True))
            colors += ['greenyellow']
            # colors += ['darkolivegreen']
            # colors += ['gray']
        
        p = PatchCollection(patches, alpha=.4, facecolor=colors, lw=1, edgecolor='k')
        ax.add_collection(p)
        
        # plate foundation    
        if foundation and self._foundation_type=='plate':
            if self._column is not None:
                ax.plot(self._column[:, 0], self._column[:, 1],'-', color='grey', lw=10, zorder=2)
            ax.plot(self._footing[:, 0], self._footing[:, 1],'-', color='grey', lw=10, zorder=2)
       
        # water table
        if self._wt is not None:
            ax.plot([0, self._model_width], [self._wt, self._wt], '-b', lw=3, zorder=3)

        ax.set_xlim([0, 1.1 * self._model_width])
        ax.set_ylim([-self._model_depth, 0.1 * self._model_depth])
        ax.grid(alpha=0.4)
        plt.close(fig)
        return fig