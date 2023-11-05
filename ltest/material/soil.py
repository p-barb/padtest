import numpy as np

class SoilMaterial():
    """Interface  that creates a soil material in Plaxis from
    the contents of a dictionary.
    """
    
    def __init__(self):
        """Init method.
        """
        pass
    
    #===================================================================
    # PRIVATE METHODS
    #===================================================================
    @classmethod
    def _set_elastic(cls, g_i, label, material):
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
        CombinedClass
            Plaxis object of the soil material.
        
        Raises
        ------
        RuntimeError
            Failed to create the soil material.
        """

        if 'kx' not in material:
            material['kx'] = 0
        if 'ky' not in material:
            material['ky'] = 0
        if 'Rinter' not in material:
            material['Rinter'] = 1
        
        try:
            material = g_i.soilmat("MaterialName",label,
                                   "SoilModel", 1,
                                   "DrainageType", material["DrainageType"],
                                   "Eref", material['Eref'],
                                   "nu", material['nu'],
                                   "gammaSat", material['gammaSat'],
                                   "gammaUnsat", material['gammaUnsat'],
                                   'perm_primary_horizontal_axis', material['kx'],
                                   'perm_vertical_axis', material['ky'],
                                   'Rinter', material['Rinter'])
        except:
            msg = 'Unable to create linear elastic material <{}>.'.format(label)
            raise RuntimeError(msg)
        return material

    @classmethod
    def _set_mc(cls, g_i, label, material):
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
        CombinedClass
            Plaxis object of the soil material.
        
        Raises
        ------
        RuntimeError
            Failed to create the soil material.
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
        try:
            material = g_i.soilmat("MaterialName",label,
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
        except:
            msg = 'Unable to create Mohr-Coulomb material <{}>.'.format(label)
            raise RuntimeError(msg)
        return material
    
    @classmethod
    def _set_hs(cls, g_i, label, material):
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
        CombinedClass
            Plaxis object of the soil material.
        
        Raises
        ------
        RuntimeError
            Failed to create the soil material.
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
        try:
            material = g_i.soilmat("MaterialName",label, 
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
        except:
            msg = 'Unable to create hardening soil material <{}>.'.format(label)
            raise RuntimeError(msg)
        return material
    
    #===================================================================
    # PUBLIC METHODS
    #===================================================================
    @classmethod
    def set(cls, g_i, label, material):
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
        CombinedClass
            Plaxis object of the soil material.

        Raises
        ------
        RuntimeError
            Unsuported soil model.
        """
        g_i.gotosoil()
        if material["SoilModel"].lower() == 'elastic':
            return cls._set_elastic(g_i, label, material)
        elif material["SoilModel"].lower() in ['mohr-coulomb', 'mohr coulomb', 'mc', 'mohrcoulomb']:
            return cls._set_mc(g_i, label, material)
        elif material["SoilModel"].lower() in ['hardening-soil', 'hardening soil', 'hs', 'hardeningsoil']:
            return cls._set_hs(g_i, label, material)
        else:
            raise RuntimeError('Unsuported soil model <{}>'.format(material["SoilModel"]))