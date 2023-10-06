import numpy as np
 
def set_concrete_plate(fc, gamma, d, young_modulus=None, poisson=0.4):
    """Creates a dictionary with the required plate properties based on
    the concrete type.

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
    concrete['fc'] = fc * 1000 # kPa
    if young_modulus is None:
        concrete['E'] = 4700 *  np.sqrt(concrete['fc']) # kPa
    else:
        concrete['E'] = young_modulus
    concrete['nu'] = poisson 
    concrete['EA'] = concrete['E'] * d
    concrete['EI'] = concrete['E'] * d**3/12
    concrete['d'] = np.sqrt(12 * concrete['EI'] / concrete['EA'])
    concrete['Gref'] = concrete['EA'] / concrete['d']  / (2 * (1 + concrete['nu'])) # KPa
    return concrete