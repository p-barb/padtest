import copy
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection
import numbers
import numpy as np
import textwrap

class Geometry():

    def __init__(self, b, d, foundation_type='plate', b1=None, d1=None,
                 dstrata=None, wt=None, fill_angle=None, bfill=0.5,
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
        self._set_fill(fill_angle, nfill, dfill, bfill)
        self._set_under_base(dunder)
        self._set_foundation_type()
        self._set_soil(dstrata)
        self._build_excavated()
        self._set_wt(wt)

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
        txt += self._param_value_string('wt', self._wt_depth, 'water table depth', 'm')
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
            foundation width [m].
        d : float
            foundation depth [m]
        b1 : float, None
            foundation column widht [m]
        d1 : float, None
            foundation width [m]
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
        self._surface_foundation = False
        if d == 0:
            self._surface_foundation = True
        ymax = self._d + 3 * self._b
        self._model_height = ymax
        self._b1 = b1
        self._d1 = d1
        self._foundation_type = foundation_type
        if foundation_type == 'solid':
            if d==0 and d1 is None:
                raise RuntimeError('d1 must be specified in a solid model located at the surface.')
            elif d1 is None or b1 is None:
                raise RuntimeError('b1 and d1 must be specified in a buried solid model.')
        if foundation_type == 'plate' and self._d == 0:
            self._foundation = np.array([[0, ymax],
                                         [b/2, ymax]])
            self._column = None
            self._footing = np.array([[0, ymax],
                                      [b/2, ymax]])
            return
        elif foundation_type == 'plate':
            self._foundation = np.array([[0, ymax],
                                         [0, ymax - d],
                                         [b/2, ymax  - d]])
            self._column = np.array([[0, ymax],
                                      [0, ymax - d]])
            self._footing = np.array([[0, ymax - d],
                                      [b/2, ymax  - d]])
            return
        self._column = None
        self._footing = None
        if self._d == 0:
            self._foundation = np.array([[0, ymax + d1],
                                        [b/2, ymax + d1],
                                        [b/2, ymax],
                                        [0, ymax]])
        else:
            self._foundation = np.array([[0, ymax],
                                        [b1/2, ymax],
                                        [b1/2, ymax - d + d1],
                                        [b/2, ymax - d + d1],
                                        [b/2, ymax - d],
                                        [0, ymax - d]])

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
            return
 
        self._fill_angle = fill_angle
        self._bfill = bfill
        if nfill is None and dfill is None:
            self._nfill = 1
            self._dfill = np.array([self._d])
            self._build_fill()
            return
        if nfill is not None and dfill is not None:
            raise RuntimeError('Either define the number of uniform fill layers <nfill> or their widhts <dfill>.')
        if nfill is not None:
            self._nfill = nfill
            self._dfill = [self._d / self._nfill] * self._nfill
            self._build_fill()
            return
        if isinstance(dfill, numbers.Number):
            dfill = [dfill]
        dfill = np.array(dfill)
        dfill = dfill[np.cumsum(dfill) < self._d]
        dfill = np.concatenate([dfill, [self._d - np.sum(dfill)]])
        self._dfill = dfill
        self._nfill = len(dfill)
        self._build_fill()
    
    def _build_fill(self):
        """Builds polygons with the fill coordinates.
        """
        self._fill_top = np.concatenate([[0], np.cumsum(self._dfill)[:-1]])
        self._fill_bottom = np.cumsum(self._dfill)
        self._fill = []
        for ytop, ybottom in zip(self._fill_top, self._fill_bottom):
            self._fill.append(self._build_fill_layer(ytop, ybottom))

    def _build_fill_layer(self, ytop, ybottom):
        """Build polygon coordinates for a single fill layer.

        Parameters
        ----------
        ytop : float
            Depth top of fill layer [m].
        ybottom : _type_
            Depth bottom of fill layer [m].

        Returns
        -------
        np.ndarray
            (4, 2) coordiantes of fill polygon.
        """
        if self._foundation_type == 'plate':
            fill = np.array([[0, self._model_height -  ytop],
                             [self._x_fill(ytop), self._model_height - ytop],
                             [self._x_fill(ybottom), self._model_height - ybottom],
                             [0, self._model_height - ybottom]])            
            return fill
        if self._bfill == 0:
            fill = np.array([[self._b1 / 2, self._model_height -  ytop],
                             [self._x_fill(ytop), self._model_height - ytop],
                             [self._x_fill(ybottom), self._model_height - ybottom],
                             [self._b1 / 2, self._model_height - ybottom]])            
            return fill

        fill = []
        if ytop < self._d - self._d1:
            fill.append([self._b1 / 2, self._model_height -  ytop])
            fill.append([self._x_fill(ytop), self._model_height - ytop])
            fill.append([self._x_fill(ybottom), self._model_height - ybottom])
            if ybottom <= self._d - self._d1:
                fill.append([self._b1 / 2, self._model_height - ybottom])
            else:
                fill.append([self._b / 2, self._model_height - ybottom])
                fill.append([self._b / 2, self._model_height - self._d + self._d1])
                fill.append([self._b1 / 2, self._model_height - self._d + self._d1])
        else:
            fill.append([self._b / 2 + self._b1 / 2, self._model_height -  ytop])
            fill.append([self._x_fill(ytop), self._model_height - ytop])
            fill.append([self._x_fill(ybottom), self._model_height - ybottom])
            fill.append([self._b / 2 + self._b1 / 2, self._model_height - ybottom])
        return np.array(fill)
    
    def _build_excavated(self):
        """Builds polygons with the excavated material coordinates.
        """
        if self._fill is None:
            self._excavated = None
            self._dexcavated = None
            self._nexcavated = None
            return
        dexcavated = copy.deepcopy(self._dstrata)
        dexcavated = dexcavated[np.cumsum(dexcavated) < self._d]
        dexcavated = np.concatenate([dexcavated, [self._d - np.sum(dexcavated)]])
        self._dexcavated = dexcavated
        self._nexcavated = len(dexcavated)

        # Build polygon coordinates for the stratigrpahy within the fill
        # area
        strata_top = np.concatenate([[0], np.cumsum(dexcavated)[:-1]])
        srtata_bottom = np.cumsum(dexcavated)
        self._excavated = []
        for ytop, ybottom in zip(strata_top, srtata_bottom):
            self._excavated.append(self._build_excavated_layer(ytop, ybottom))

    def _build_excavated_layer(self, ytop, ybottom):
        """Build polygon coordinates for a single excavated layer.

        Parameters
        ----------
        ytop : float
            Depth top of excavated layer [m].
        ybottom : _type_
            Depth bottom of excavated layer [m].

        Returns
        -------
        np.ndarray
            (4, 2) coordiantes of fill polygon.
        """
        
        fill = np.array([[0, self._model_height -  ytop],
                            [self._x_fill(ytop), self._model_height - ytop],
                            [self._x_fill(ybottom), self._model_height - ybottom],
                            [0, self._model_height - ybottom]])            
        return fill

    def _x_fill(self, y):
        """X coordiante of fill slope given the depth.

        Parameters
        ----------
        y : float
            Depth [m].

        Returns
        -------
        float
            x-coordinate.
        """
        x0 = self._b / 2 + self._bfill
        return -(y - self._d) / np.tan(np.radians(self._fill_angle)) + x0
        
    def _set_under_base(self, dunder):
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
        self._under = [[0, self._model_height - self._d],
                       [self._b / 2 + self._bfill, self._model_height - self._d],
                       [self._b / 2 + self._bfill, self._model_height - self._d - self._dunder],
                       [0, self._model_height - self._d - self._dunder]]
        self._under = np.array(self._under)

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

    def _set_soil(self, dstrata):
        """Set soil layers.

        Parameters
        ----------
        dstrata : list, None
            Width of soil layers [m].
        """
        model_width = np.max([1.5 * self._d, 2 * self._b])
        if self._fill_angle is not None:
            model_width = np.max([self._b/2 + self._bfill + self._d / np.tan(np.radians(self._fill_angle)) + 0.5,
                                  model_width])
        self._model_width = model_width
        if dstrata is None:
            dstrata = self._model_height * 2
        
        if isinstance(dstrata, numbers.Number):
            dstrata = [dstrata]
        dstrata = np.array(dstrata)
        dstrata = dstrata[np.cumsum(dstrata) < self._model_height]
        dstrata = np.concatenate([dstrata, [self._model_height - np.sum(dstrata)]])
        self._dstrata = dstrata
        self._nstrata = len(dstrata)

        #Build polygon coordinates for the stratigrpahy.
        self._strata_top = np.concatenate([[0], np.cumsum(self._dstrata)[:-1]])
        self._strata_bottom = np.cumsum(self._dstrata)
        self._strata = []
        func = {1:self._strata_case_1, 2:self._strata_case_2,
                3:self._strata_case_3, 4:self._strata_case_4,
                5:self._strata_case_5, 6:self._strata_case_6,
                7:self._strata_case_7}
        for ytop, ybottom in zip(self._strata_top, self._strata_bottom):
            self._strata.append(func[self._ftypeid](ytop, ybottom))        
          
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
        strata = np.array([[0, self._model_height - ytop],
                           [self._model_width, self._model_height - ytop],
                           [self._model_width, self._model_height - ybottom],
                           [0, self._model_height - ybottom]])
        return strata
    
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
        strata = []
        if ytop < self._dunder and ybottom <= self._dunder:
            strata.append([self._b / 2, self._model_height -ytop])
            strata.append([self._model_width, self._model_height - ytop])
            strata.append([self._model_width, self._model_height - ybottom])
            strata.append([self._b / 2, self._model_height - ybottom])
        elif ytop < self._dunder and ybottom > self._dunder:
            strata.append([self._b / 2, self._model_height -ytop])
            strata.append([self._model_width, self._model_height - ytop])
            strata.append([self._model_width, self._model_height - ybottom])
            strata.append([0, self._model_height - ybottom])
            strata.append([0, self._model_height - self._dunder])
            strata.append([self._b / 2, self._model_height - self._dunder])
        elif ytop >= self._dunder:
            strata.append([0, self._model_height -ytop])
            strata.append([self._model_width, self._model_height - ytop])
            strata.append([self._model_width, self._model_height - ybottom])
            strata.append([0, self._model_height - ybottom])
        return np.array(strata)
    
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
        strata = []
        if ytop < self._d - self._d1:
            strata.append([self._b1 / 2, self._model_height -ytop])
            strata.append([self._model_width, self._model_height -ytop])
            strata.append([self._model_width, self._model_height - ybottom])
            if ybottom <= self._d - self._d1:
                strata.append([self._b1/2, self._model_height - ybottom])
            elif ybottom <= self._d:
                strata.append([self._b/2, self._model_height - ybottom])
                strata.append([self._b/2, self._model_height - self._d + self._d1])
                strata.append([self._b1/2, self._model_height - self._d + self._d1])
            else:
                strata.append([0, self._model_height - ybottom])
                strata.append([0, self._model_height - self._d])
                strata.append([self._b/2, self._model_height - self._d])
                strata.append([self._b/2, self._model_height - self._d + self._d1])
                strata.append([self._b1/2, self._model_height - self._d + self._d1])
        elif ytop < self._d:
            strata.append([self._b / 2, self._model_height -ytop])
            strata.append([self._model_width, self._model_height -ytop])
            strata.append([self._model_width, self._model_height - ybottom])
            if ybottom <= self._d:
                strata.append([self._b/2, self._model_height - ybottom])
            else:
                strata.append([0, self._model_height - ybottom])
                strata.append([0, self._model_height - self._d])
                strata.append([self._b/2, self._model_height - self._d])
        else:
            strata.append([0, self._model_height -ytop])
            strata.append([self._model_width, self._model_height - ytop])
            strata.append([self._model_width, self._model_height - ybottom])
            strata.append([0, self._model_height - ybottom])
        return np.array(strata)
    
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
        strata = []
        if ytop < self._d:
            strata.append([0, self._model_height -ytop])
            strata.append([self._model_width, self._model_height -ytop])
            strata.append([self._model_width, self._model_height - ybottom])
            if ybottom <= self._d:
                strata.append([0, self._model_height - ybottom])
            elif ybottom <= self._d + self._dunder:
                strata.append([self._b/2, self._model_height - ybottom])
                strata.append([self._b/2, self._model_height - self._d])
                strata.append([0, self._model_height - self._d])
            else:
                strata.append([0, self._model_height - ybottom])
                strata.append([0, self._model_height - self._d -  self._dunder])
                strata.append([self._b/2, self._model_height - self._d -  self._dunder])
                strata.append([self._b/2, self._model_height - self._d])
                strata.append([0, self._model_height - self._d])
        elif ytop < self._d + self._dunder:
            strata.append([self._b / 2, self._model_height -ytop])
            strata.append([self._model_width, self._model_height -ytop])
            strata.append([self._model_width, self._model_height - ybottom])
            if ybottom <= self._d + self._dunder:
                strata.append([self._b / 2, self._model_height - ybottom])
            else:
                strata.append([0, self._model_height - ybottom])
                strata.append([0, self._model_height - self._d - self._dunder])
                strata.append([self._b / 2, self._model_height - self._d - self._dunder])
        else:
            strata.append([0, self._model_height -ytop])
            strata.append([self._model_width, self._model_height - ytop])
            strata.append([self._model_width, self._model_height - ybottom])
            strata.append([0, self._model_height - ybottom])
        return np.array(strata)
    
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
        strata = []
        if ytop < self._d - self._d1:
            strata.append([self._b1 / 2, self._model_height -ytop])
            strata.append([self._model_width, self._model_height -ytop])
            strata.append([self._model_width, self._model_height - ybottom])
            if ybottom <= self._d - self._d1:
                strata.append([self._b1/2, self._model_height - ybottom])
            elif ybottom <= self._d + self._dunder:
                strata.append([self._b/2, self._model_height - ybottom])
                strata.append([self._b/2, self._model_height - self._d + self._d1])
                strata.append([self._b1/2, self._model_height - self._d + self._d1])
            else:
                strata.append([0, self._model_height - ybottom])
                strata.append([0, self._model_height - self._d - self._dunder])
                strata.append([self._b/2, self._model_height - self._d - self._dunder])
                strata.append([self._b/2, self._model_height - self._d + self._d1])
                strata.append([self._b1/2, self._model_height - self._d + self._d1])
        elif ytop < self._d + self._dunder:
            strata.append([self._b / 2, self._model_height -ytop])
            strata.append([self._model_width, self._model_height -ytop])
            strata.append([self._model_width, self._model_height - ybottom])
            if ybottom <= self._d + self._dunder:
                strata.append([self._b/2, self._model_height - ybottom])
            else:
                strata.append([0, self._model_height - ybottom])
                strata.append([0, self._model_height - self._d - self._dunder])
                strata.append([self._b/2, self._model_height - self._d - self._dunder])
        else:
            strata.append([0, self._model_height -ytop])
            strata.append([self._model_width, self._model_height - ytop])
            strata.append([self._model_width, self._model_height - ybottom])
            strata.append([0, self._model_height - ybottom])
        return np.array(strata)
    
    def _strata_case_6(self, ytop, ybottom):
        """Strata for buried foundations with fill and no under-base.

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

        strata = []
        if ytop < self._d:
            strata.append([self._x_fill(ytop), self._model_height - ytop])
            strata.append([self._model_width, self._model_height - ytop])
            strata.append([self._model_width, self._model_height - ybottom])
            if ybottom <= self._d:
                strata.append([self._x_fill(ybottom), self._model_height - ybottom])
            else:
                strata.append([0, self._model_height - ybottom])
                strata.append([0, self._model_height - self._d])
                strata.append([self._b /2 + self._bfill, self._model_height - self._d])
        else:
            strata.append([0, self._model_height -ytop])
            strata.append([self._model_width, self._model_height - ytop])
            strata.append([self._model_width, self._model_height - ybottom])
            strata.append([0, self._model_height - ybottom])

        return np.array(strata)
    
    def _strata_case_7(self, ytop, ybottom):
        """Strata for buried foundations with fill and under-base.

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

        strata = []
        if ytop < self._d:
            strata.append([self._x_fill(ytop), self._model_height - ytop])
            strata.append([self._model_width, self._model_height - ytop])
            strata.append([self._model_width, self._model_height - ybottom])
            if ybottom <= self._d:
                strata.append([self._x_fill(ybottom), self._model_height - ybottom])
            elif ybottom <= self._d + self._dunder:
                strata.append([self._b / 2 + self._bfill, self._model_height - ybottom])
                strata.append([self._b / 2 + self._bfill, self._model_height - self._d])
            else:
                strata.append([0, self._model_height - ybottom])
                strata.append([0, self._model_height - self._d - self._dunder])
                strata.append([self._b /2 + self._bfill, self._model_height - self._d - self._dunder])
                strata.append([self._b /2 + self._bfill, self._model_height - self._d])
        elif ytop < self._d + self._dunder:
            strata.append([self._b / 2 + self._bfill, self._model_height - ytop])
            strata.append([self._model_width, self._model_height - ytop])
            strata.append([self._model_width, self._model_height - ybottom])
            if ybottom <= self._d + self._dunder:
                strata.append([self._b / 2 + self._bfill, self._model_height - ybottom])
            else:
                strata.append([0, self._model_height - ybottom])
                strata.append([0, self._model_height - self._d - self._dunder])
                strata.append([self._b /2 + self._bfill, self._model_height - self._d - self._dunder])
        else:
            strata.append([0, self._model_height -ytop])
            strata.append([self._model_width, self._model_height - ytop])
            strata.append([self._model_width, self._model_height - ybottom])
            strata.append([0, self._model_height - ybottom])
        return np.array(strata)

    def _strata_xmin(self, y):
        """Left coordinate of a strata at depth y.

        Parameters
        ----------
        y : float
            Depth [m].

        Returns
        -------
        float
            x-coordinate.
        """
        # surface foundaiton - no fill
        if self._d == 0:
            if self._dunder is None:        
                return 0
            if y > self._dunder:
                return 0
            return self._b / 2
        # buried foundation
        if y > self._d:
            if self._dunder is None:        
                return 0
            if y > self._d + self._dunder:
                return 0
            return self._b/2 + self._bfill
        # plate foundation
        if self._foundation_type == 'plate':
            if self._fill is None:
                return 0
            return self._x_fill(y)
        # solid foundation
        if self._fill is None:
            if y <= self._d - self._d1:
                return self._b1 / 2
            return self._b/2
        return self._x_fill(y)

    def _set_wt(self, wt):
        """Sets water table.

        Parameters
        ----------
        wt : float, None
            Water tabe depth [m].
        """
        self._wt_depth = wt
        self._wt = None
        if wt is not None:
            self._wt = self._model_height - wt 
    
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
        fig, ax = plt.subplots(1, 1, figsize=(figsize, figsize * self._model_height/self._model_width))

        patches = []
        colors = []
        if self._fill is not None and fill:
            colors += ['greenyellow'] * self._nfill
            for fill in self._fill:
                patches.append(Polygon(fill, True))
        elif self._fill is not None:
            colors += ['tan'] * self._nexcavated
            for excavated in self._excavated:
                patches.append(Polygon(excavated, True))

        colors += ['tan'] * self._nstrata 
        for strata in self._strata:
            patches.append(Polygon(strata, True))
        if self._under is not None:
            patches.append(Polygon(self._under, True))
            colors += ['darkolivegreen']

        if foundation and self._foundation_type=='plate':
            if self._column is not None:
                ax.plot(self._column[:, 0], self._column[:, 1],'-', color='grey', lw=10, zorder=2)
            ax.plot(self._footing[:, 0], self._footing[:, 1],'-', color='grey', lw=10, zorder=2)
        elif foundation and self._foundation_type == 'solid':
            patches.append(Polygon(self._foundation, True))
            colors += ['gray']
        p = PatchCollection(patches, alpha=.4, facecolor=colors, lw=1, edgecolor='k')
        ax.add_collection(p)
        # water table
        if self._wt is not None:
            ax.plot([0, self._model_width], [self._wt, self._wt], '-b', lw=3, zorder=3)

        ax.set_xlim([0, 1.2 * self._model_width])
        ax.set_ylim([0, 1.2 * self._model_height])
        ax.grid(alpha=0.4)
        plt.close(fig)
        return fig