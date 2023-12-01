import numpy as np

class PlateMaterial():
    """Interface  that creates a plate material in Plaxis from
    the contents of a dictionary.
    """

    def __init__(self):
        """Init method.
        """
        pass

    #===================================================================
    # PUBLIC METHODS
    #===================================================================
    @classmethod
    def concrete(cls, fc, gamma, d, young_modulus=None, poisson=0.4):
        """Creates a dictionary with the required plate properties based
        on the concrete type.

        Parameters
        ----------
        fc : float
            Design compressive strenght of concrete [MPa].
        gamma : float
            Unit weight [kN/m3].
        d : float
            Thickness of the slab [m].
        young_modulus : float, optional
            Young modulus [kPa], by default None.
        poisson : float, optional
            Poisson coeffcient, by default 0.4.

        Returns
        -------
        dict
            Dictionary with the properties required to create a plate
            material.
        """
        concrete = {}
        concrete['fc'] = fc # kPa
        if young_modulus is None:
            concrete['E'] = 4700 *  np.sqrt(concrete['fc']) *1000 # kPa
        else:
            concrete['E'] = young_modulus
        concrete['nu'] = poisson 
        concrete['EA'] = concrete['E'] * d
        concrete['EI'] = concrete['E'] * d**3/12
        concrete['d'] = np.sqrt(12 * concrete['EI'] / concrete['EA'])
        concrete['Gref'] = concrete['EA'] / concrete['d']  / (2 * (1 + concrete['nu'])) # KPa
        concrete['gamma'] = gamma
        concrete['w'] = concrete['gamma'] * concrete['d']
        return concrete
    
    @classmethod
    def set(cls, g_i, label, material):
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
        CombinedClass
            Plaxis object of the plate material.
        """
        g_i.gotosoil()
        if "RayleighAlpha" not in material:
            material['RayleighAlpha'] = 0
        if "RayleighBeta"not in material:
            material['RayleighBeta'] = 0
        try:
            material = g_i.platemat("MaterialName", label,
                                    "MaterialNumber", 0,
                                    "Elasticity", 0,
                                    "IsIsotropic", True,
                                    "EA", material['EA'],
                                    "EA2", material['EA'],
                                    "EI", material['EI'],
                                    "nu", material['nu'],
                                    "d", material['d'],
                                    "Gref", material['Gref'],
                                    'RayleighAlpha', material['RayleighAlpha'],
                                    'RayleighBeta', material['RayleighBeta'])
        except:
            msg = 'Unable to create plate material <{}>.'.format(label)
            raise RuntimeError(msg)
        return material
