import numpy as np
import matplotlib.pyplot as plt

class Polygon():
    """2D clsoed polygon.
    """
    
    def __init__(self, vertex):
        """Init method.

        Parameters
        ----------
        vertex : array-llike
            (nv, 2) vertex cooodrinates.
        """
        vertex = np.array(vertex)
        if np.array_equal(vertex[-1], vertex[0]):
            vertex = vertex[:-1]
        self._vertex = vertex
        self._nvertex = len(self._vertex)
        self._set_area()
        self._set_bounding_box()
    
    #===================================================================
    # PRIVATE METHODS
    #===================================================================
    def _closed_vertex(self):
        """Returns the closed polygon vertex coordinates.

        Returns
        -------
        np.ndarray
            (nv+1, 2) vertex coordiantes.
        """
        return np.vstack([self._vertex, self._vertex[0]])
        
    def _set_area(self):
        """Computes polygon area and centroid.

        Raises
        ------
        RuntimeError
            0 area polygon.
        """
        vertex = self._closed_vertex()
        area = 0
        cx = 0
        cy = 0
        for idx in range(self._nvertex):
            x = vertex[idx, 0] * vertex[idx + 1, 1] - vertex[idx + 1, 0] * vertex[idx, 1]
            cx += (vertex[idx, 0] + vertex[idx + 1, 0]) * x
            cy += (vertex[idx, 1] + vertex[idx + 1, 1]) * x
            area += x
        area /= 2
        if area == 0:
            raise RuntimeError('Polygon has no area.')            
        self._centroid = np.array([cx, cy]) / (6 * area)
        self._area = np.abs(area)

    def _set_bounding_box(self):
        """Computes polygo bounding box.
        """
        xmin = np.min(self._vertex[:, 0])
        xmax = np.max(self._vertex[:, 0])
        ymin = np.min(self._vertex[:, 1])
        ymax = np.max(self._vertex[:, 1])
        self._bounding_box = np.array([[xmin, ymin], [xmin, ymax], [xmax, ymax], [xmax, ymin]])
        self._width = xmax - xmin
        self._height = ymax - ymin
    
    def _vertex_list(self):
        """Returns the polygon vertex as a list.

        Returns
        -------
        list
            List with vertex coordinates.
        """
        return [list(v) for v in self._vertex]
    
    #===================================================================
    # PUBLIC METHODS
    #===================================================================
    def in_strata(self, zstrata):
        """Identifies the strata where the polygon is located.

        Parameters
        ----------
        zstrata : array-like
            (nstrata,) depth of the bottom of each strata, in descending
            order.

        Returns
        -------
        int
            Index of the strata in the zstrata array.
        """
        # beyond max straa depth
        if self._centroid[1] < zstrata[-1]:
            return None
        return list(self._centroid[1]> zstrata).index(True)

    def add_2_model(self, g_i):
        """Adds the polygon as a Plaxis model structure.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.

        Returns
        -------
        _type_
            _description_
        """
        g_i.gotostructures()
        struct_poly, struct_soil = g_i.polygon(*self._vertex_list())
        g_i.gotostages()
        phase_poly = g_i.polygons[-1]
    
        return struct_poly, struct_soil, phase_poly

    def plot(self, figsize=3):
        """Creates a figure showing the polygon and its centroid.

        Parameters
        ----------
        figsize : float, optional
            Figure size, by default 3

        Returns
        -------
        Figure
            Figure with the polygon and its centroid.
        """
        fig, ax = plt.subplots(1, 1, figsize=(figsize, figsize * self._height / self._width))
        vertex = self._closed_vertex()
        ax.plot(vertex[:,0], vertex[:,1], '-ok')
        ax.plot(self._centroid[0], self._centroid[1], 'xk', ms=8)
        ax.grid(alpha=0.2)
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        plt.close()
        return fig
        