import numpy as np

class PlateMaterial():
    """Interface  that creates a plate material in Plaxis from
    the contents of a dictionary.
    """
    _parameter_map = {"Identification": ["MaterialName", "name", 'Identification'],
                      'MaterialType': ['MaterialType'],
                      'Colour':['colour', 'color'],
                      'commments':['commments'],
                      'w':['w'],
                      'PreventPunching':['PreventPunching'],
                      'RayleighAlpha': ['RayleighAlpha'],
                      'RayleighBeta': ['RayleighBeta'],
                      'Isotropic':['Isotropic'],
                      'EA1':['EA1', 'EA'],
                      'EA2':['EA2'],
                      'EI':['EI'],
                      'StructNu':['StructNu', 'nu', 'poisson'],
                      'MP':['MP'],
                      'Np1':['Np1'],
                      'Np2':['Np2'],
                      'MkappaDiagram':['MkappaDiagram']}
    
    def __init__(self):
        """Initialize a new instance of `PlateMaterial`.
        """
        pass

    #===================================================================
    # PRIVATE METHODS
    #===================================================================
    @classmethod
    def _set_paramters_names(cls, material):
        """Sets the material dicationary keys to the internal Plaxis
        values.

        Parameters
        ----------
        material : dict
            Dictionary with the material parameters with the keys
            provided by the user.

        Returns
        -------
        dict
            Dictionary with material parameters with interal Plaxis
            keys.

        Raises
        ------
        RuntimeError
            Unsuported material parameter.
        RuntimeError
            Duplicated material parameter.
        """
        formated_material = {}
        for parameter in material:
            sanitized_param = cls._sanitized_name(parameter)
            for plx_key, user_keys in cls._parameter_map.items():
                if sanitized_param in [cls._sanitized_name(key) for key in user_keys]:
                    break
            else:
                msg = "Plate material parameter <{}> in <{}> not supported."
                msg = msg.format(parameter, formated_material['Identification'])
                raise RuntimeError(msg)
                
            if plx_key in formated_material:
                msg = "Duplicated plate material parameter <{}> as <{}> in <{}>.".format(plx_key, parameter, formated_material['Identification'])
                raise RuntimeError(msg)
            formated_material[plx_key] = material[parameter]
        return formated_material


    @staticmethod
    def _sanitized_name(name):
        """Returns a sanitized version (lower case, no spaces or
        hyphens) of a parameter name.

        Parameters
        ----------
        name : str
            Parameter name.

        Returns
        -------
        str
            Sanitized parameter name.
        """
        sanitized = name.lower()
        for char in [' ', '_', '-']:
             sanitized = sanitized.replace(char, '')
        return sanitized

    #===================================================================
    # PUBLIC METHODS
    #===================================================================
    @classmethod
    def concrete(cls, gamma, d, young_modulus=None, fc=None, poisson=0.4):
        """Creates a dictionary with the required plate properties based
        on the concrete type.

        Parameters
        ----------
        gamma : float
            Unit weight [kN/m3].
        d : float
            Thickness of the slab [m].
        young_modulus : float, optional
            Young modulus [kPa], by default None.
        fc : float, optional
            Compressive strenght of concrete [MPa]. Used to estimate the
            Young modulus when not provided as
            E[kPa] = 4700 sqrt(fc[MPa]) 10^3.
        poisson : float, optional
            Poisson coeffcient, by default 0.4.

        Returns
        -------
        dict
            Dictionary with the properties required to create a plate
            material.

        Raises
        ------
        RuntimeError
            Neither E or fc specified.
        """
        if young_modulus is None and fc is None:
            msg = 'Either the Young modulus or the concrece compressive strength must be specified.'
            raise RuntimeError(msg)
        elif young_modulus is None:
            young_modulus = 4700 *  np.sqrt(fc) *1000 # kPa

        concrete = {}
        concrete['MaterialType'] = 'Elastic'
        concrete['Isotropic'] = True
        concrete['nu'] = poisson 
        concrete['EA1'] = young_modulus * d
        concrete['EI'] = young_modulus * d**3 / 12
        concrete['w'] = gamma * d
        return concrete
    
    @classmethod
    def create_material(cls, g_i, material):
        """Creates an elastic plate  material in the model.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        material : dict
            Dictionary with material properties.

        Returns
        -------
        CombinedClass
            Plaxis object of the plate material.
        """
        formated_material = cls._set_paramters_names(material)

        g_i.gotosoil()
        try:
            return g_i.platemat(*formated_material.items())
        except:
            msg = ('Unable to create plate material <{}>. Check error '
                   'message in Plaxis command line history for details.')
            raise RuntimeError(msg.format(formated_material['Identification']))
