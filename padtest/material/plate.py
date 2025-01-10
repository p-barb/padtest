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

    # List of Plaxis ids of the soil paramters only accepted under the
    # ultimate license
    _ultimate_parameters = ['RayleighDampingInputMethod', 'RayleighAlpha', 'RayleighBeta']

    #list of supported parameters depending on the Isotropic flag
    _isotropic = {True: ['Identification', 'MaterialType', 'Colour', 'commments',
                         'w', 'PreventPunching',
                         'RayleighAlpha', 'RayleighBeta',
                         'Isotropic', 'EA1', 'EI', 'StructNu'],
                  False: ['Identification', 'MaterialType', 'Colour', 'commments',
                          'w','PreventPunching',
                          'RayleighAlpha', 'RayleighBeta',
                          'Isotropic', 'EA1', 'EA2', 'EI']}

    #list of supported parameters depending on the material type
    _mat_type_param = {"Elastic":[], 
                       'Elastoplastic':['MP', 'NP1', 'NP2'],
                       "Elastoplastic (M-kappa)":['MkappaDiagram']}
    
    def __init__(self):
        """Initialize a new instance of `PlateMaterial`.
        """
        pass

    #===================================================================
    # PRIVATE METHODS
    #===================================================================
    @classmethod
    def _set_material_identification(cls, material):
        """Extracts material identification from input material
        dictionary and creates a new dictionary with identification
        under the interal plaxis key value.

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
        dict
            Dictionary with the material parameters with the keys
            provided by the user.

        Raises
        ------
        RuntimeError
            Missing material identification.
        RuntimeError
            Multiple soil material identification.
        """
        id_keys = [id_key for id_key in cls._parameter_map['Identification'] if id_key in material]
        if len(id_keys) == 0:
            msg = 'Missing plate material idetinfication.'
            raise RuntimeError(msg)
        if len(id_keys) > 1:
            msg = 'Multiple plate material idetinfication.'
            raise RuntimeError(msg)
        formated_material = {'Identification': material[id_keys[0]]}
        _ = material.pop(id_keys[0])
        return formated_material, material
    
    @classmethod
    def _set_material_type(cls, formated_material, material):
        """Sets the material type to the internal Plaxis key.

        Parameters
        ----------
        formated_material : dict
            Dictionary with material parameters with interal Plaxis
            keys.
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
            Missing plate material type.
        RuntimeError
            Multiple plate material type.
        """

        id_keys = [id_key for id_key in cls._parameter_map['MaterialType'] if id_key in material]
        if len(id_keys) == 0:
            msg = 'Missing plate material type for <{}>.'.format(formated_material['Identification'])
            raise RuntimeError(msg)
        if len(id_keys) > 1:
            msg = 'Multiple plate material types for <{}>.'.format(formated_material['Identification'])
            raise RuntimeError(msg)
        formated_material['MaterialType'] = material[id_keys[0]]
        _ = material.pop(id_keys[0])
        return formated_material, material
    
    @classmethod
    def _set_isotropic(cls, formated_material, material):
        """Sets the material isotrpoic flag to the internal Plaxis
        key.

        Parameters
        ----------
        formated_material : dict
            Dictionary with material parameters with interal Plaxis
            keys.
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
            Multiple plate material type.
        """
        user_keys = [cls._sanitized_name(key) for key in material]
        id_keys = [id_key for id_key in cls._parameter_map['Isotropic'] if cls._sanitized_name(id_key) in user_keys]
        if len(id_keys) == 0:
            formated_material['Isotropic'] = True
        elif len(id_keys) > 1:
            msg = 'Multiple plate material types for <{}>.'.format(formated_material['Identification'])
            raise RuntimeError(msg)
        else:
            formated_material['Isotropic'] = material[id_keys[0]]
            _ = material.pop(id_keys[0])
        return formated_material, material
    
    @classmethod
    def _set_paramters_names(cls, formated_material, material):
        """Sets the material dicationary keys to the internal Plaxis
        values.

        Parameters
        ----------
        formated_material : dict
            Dictionary with material parameters with interal Plaxis
            keys.
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
        supported = cls._isotropic[formated_material['Isotropic']] \
                    + cls._mat_type_param[formated_material['MaterialType']]
        
        for parameter in material:
            sanitized_param = cls._sanitized_name(parameter)
            for plx_key, user_keys in cls._parameter_map.items():
                if sanitized_param in [cls._sanitized_name(key) for key in user_keys]:
                    break
            else:
                msg = "Plate material parameter <{}> in <{}> not supported for {} <{}>."
                if formated_material['Isotropic']:
                    msg = msg.format(parameter, formated_material['Identification'], 
                                        'isotropic', formated_material['MaterialType'])
                else:
                    msg = msg.format(parameter, formated_material['Identification'], 
                                     'anisotropic', formated_material['MaterialType'])
                raise RuntimeError(msg)
                
            if plx_key not in supported:
                msg = "Plate material parameter <{}> in <{}> not supported for {} <{}>."
                if formated_material['Isotropic']:
                    msg = msg.format(parameter, formated_material['Identification'], 
                                        'isotropic', formated_material['MaterialType'])
                else:
                    msg = msg.format(parameter, formated_material['Identification'], 
                                     'anisotropic', formated_material['MaterialType'])
            
            if plx_key in formated_material:
                msg = "Duplicated plate material parameter <{}> as <{}> in <{}>.".format(plx_key, parameter, formated_material['Identification'])
                raise RuntimeError(msg)
            formated_material[plx_key] = material[parameter]
        return formated_material

    @classmethod
    def _check_parameter_license(cls, formated_material, license):
        """Validates that the specified parameters are supported by
        the license.

        Parameters
        ----------
        formated_material : dict
            Dictionary with plate material parameters with interal
            Plaxis keys.
        license : str
            Plaxis lincese: 'advanced' or 'ultimate'.

        Returns
        -------
        dict
            Dictionary with material parameters with interal Plaxis
            keys.

        Raises
        ------
        RuntimeError
            Parameter not included under the advanced license.
        """
        if license == 'ultimate':
            formated_material['RayleighDampingInputMethod'] = "Direct"
            return formated_material
        not_supported = [param for param in formated_material if param in cls._ultimate_parameters]
        if not_supported:
            text = 'Plate parameters {} for plate material model <{}> not supported under <advanced> license.'
            text = text.format(', '.join(not_supported), formated_material['Identification'])
            raise RuntimeError(text)
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
    def create_material(cls, g_i, material, license):
        """Creates an elastic plate  material in the model.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        material : dict
            Dictionary with material properties.
        license : str
            Plaxis lincese: 'advanced' or 'ultimate'.

        Returns
        -------
        CombinedClass
            Plaxis object of the plate material.
        """
        formated_material, material = cls._set_material_identification(material)
        formated_material, material = cls._set_material_type(formated_material, material)
        formated_material, material = cls._set_isotropic(formated_material, material)
        formated_material = cls._set_paramters_names(formated_material, material)
        formated_material = cls._check_parameter_license(formated_material, license)

        g_i.gotosoil()
        try:
            return g_i.platemat(*formated_material.items())
        except:
            msg = ('Unable to create plate material <{}>. Check error '
                   'message in Plaxis command line history for details.')
            raise RuntimeError(msg.format(formated_material['Identification']))
