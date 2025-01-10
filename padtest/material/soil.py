import numpy as np
import types

class BaseSoilMaterial():
    """Base class for soil materials.
    """

    # Plaxis soil material model. E.g.: 2 for Mohr-Coulomb
    _soil_model = NotImplementedError   
    
    # Plaxis soil material name. E.g.: 2 'Mohr-Coulomb'
    _soil_name = NotImplementedError

    # Accepted acronyms for the material, lowercase, without spaces or
    # hyphens. E.g: 'mc', 'mohrcoulomb'.
    _acronyms = NotImplementedError
    
    # Dictionary with the supported parameter names, E.g.: 
    # {'PermHorizontalPrimary':['kx', 'PermHorizontalPrimary']}
    _parameter_map = {"Identification": ["MaterialName", "name", 'Identification'],
                      'SoilModel': ['SoilModel', 'model'],
                      'Colour':['colour', 'color'],
                      "DrainageType": ["DrainageType"] ,
                      'commments':['commments'],
                      "gammaSat": ['gammasat'],
                      "gammaUnsat": ['gammaunsat'],
                      'einit':['einit', 'e0'],
                      'ERef':['ERef'],
                      "E50ref": ["E50ref"],
                      'EoedRef': ['EoedRef'],
                      'EurRef': ['EurRef'],
                      'powerm': ['powerm'],
                      'G0Ref':['G0Ref'],
                      'gamma07':['gamma07'],
                      'pRef': ['pRef'],
                      "nu": ['nu', 'poisson'],
                      'cref': ['cref', 'suref'],
                      'phi':['phi'],
                      'psi': ['psi'],
                      'cInc':['cinc', 'suinc'],
                      'VerticalRef':['VerticalRef', 'gammaref'],
                      'UseDefaults':['UseDefaults'],
                      'K0nc': ['K0nc'],
                      'RF': ['RF'],
                      'PermHorizontalPrimary' : ['PermHorizontalPrimary', 'perm_primary_horizontal_axis', 'kx'],
                      'PermVertical' : ['perm_vertical_axis', 'PermVertical', 'ky'],
                      'RayleighDampingInputMethod':['RayleighDampingInputMethod', 'RayleighMethod'],
                      'RayleighAlpha': ['RayleighAlpha'],
                      'RayleighBeta': ['RayleighBeta'],
                      'TargetDamping1':['TargetDamping1', 'xi1'],
                      'TargetDamping2':['TargetDamping2', 'xi2'],
                      'TargetFrequency1':['TargetFrequency1', 'f1'],
                      'TargetFrequency2':['TargetFrequency2', 'f2'],
                      'TensionCutOff': ['TensionCutOff'],
                      'TensileStrength': ['TensileStrength'],
                      'GapClosure':['GapClosure', 'considergapclosure'],
                      'InterfaceStrengthDetermination':['InterfaceStrengthDetermination', 'strengthdetermination'],
                      'Rinter':['Rinter'],
                      'RinterResidual':['RinterResidual'],
                      'InterfaceStiffnessDetermination':['InterfaceStiffnessDetermination'],
                      'knInter':['knInter'],
                      'ksInter':['ksInter'],
                      'K0Determination':['K0Determination'],
                      'K0PrimaryIsK0Secondary':['K0PrimaryIsK0Secondary'],
                      'K0Primary':['K0Primary'],
                      'K0Secondary':['K0Secondary'],
                      'OCR': ['ocr', 'overconsolidation ratio'],
                      'POP': ['pop'],}

    # Dictionary with defualt values for material paramteres
    _default_parameters = NotImplementedError

    # List of Plaxis ids of the soil paramters only accepted under the
    # ultimate license
    _ultimate_parameters = ['RayleighDampingInputMethod', 'RayleighAlpha', 'RayleighBeta']

    # List Plaxis ids for the supported parameters for each drainage. If
    # the draiange case is not supported for the material set it to
    # False  
    _drainage = {'Drained': NotImplementedError,
                 'Undrained A': NotImplementedError,
                 'Undrained B': NotImplementedError,
                 'Undrained C': NotImplementedError,
                 'Non-porous': NotImplementedError}

    def __init__(self):
        """Initialize a new instance of `BaseSoilMaterial`.
        """
        pass
    
    #===================================================================
    # PRIVATE METHODS
    #===================================================================
    @classmethod
    def _create_material(cls, g_i, material, license):
        """Adds material to the model.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        dict
            Dictionary with soil material parameters.
        license : str
            Plaxis lincese: 'advanced' or 'ultimate'.

        Returns
        -------
        CombinedClass
            Plaxis object of the soil material.

        Raises
        ------
        RuntimeError
            Failed material creation.
        """
        material['SoilModel'] = cls._soil_model
        formated_material = cls._check_parameters(material, license)
        try:
            return g_i.soilmat(*formated_material.items())
        except:
            msg = 'Unable to create <{}> material <{}>. Check error message in Plaxis command line history for details.'
            msg = msg.format(cls._soil_name, formated_material['Identification'])
            raise RuntimeError(msg)

    @classmethod  
    def _check_parameters(cls, material, license):
        """Validates user provided soil material paramteres.

        Parameters
        ----------
        material : dict
            User provided dictionary with soil material parameters.
        license : str
            Plaxis lincese: 'advanced' or 'ultimate'.

        Returns
        -------
        dict
            Dictionary with soil material parameters with interal Plaxis
            keys.
        
        Raises
        ------
        RuntimeError
            Missing required soil material parameter.
        """
        
        formated_material = cls._set_paramters_names(material)
        formated_material = cls._set_default_values(formated_material, license)
        cls._check_parameter_license(formated_material, license)
        return formated_material

    @classmethod
    def _set_paramters_names(cls, material):
        """Sets the material dicationary keys to the internal Plaxis
        values.

        Parameters
        ----------
        material : dict
            Dictionary with soil material parameters.

        Returns
        -------
        dict
            Dictionary with soil material parameters with interal Plaxis
            keys.

        Raises
        ------
        RuntimeError
            Unsuported soil material parameter.
        RuntimeError
            Duplicated soil material parameter.
        """
        formated_material, material = cls._set_material_identification(material)
        formated_material, material = cls._set_drainage_type(formated_material, material)
        for parameter in material:
            sanitized_param = cls._sanitized_name(parameter)
            found = False
            for plx_key, supported in cls._parameter_map.items():
                supported = [cls._sanitized_name(item) for item in supported]
                if sanitized_param in supported:
                    found = True
                    break
            
            if not found:
                msg = "Soil material parameter <{}> in <{}> not supported for <{}>."
                msg = msg.format(parameter, formated_material['Identification'], cls._soil_name)
                raise RuntimeError(msg)
            
            if plx_key in formated_material:
                msg = "Duplicated soil material parameter <{}> as <{}> in <{}>.".format(plx_key, parameter, formated_material['Identification'])
                raise RuntimeError(msg)
            formated_material[plx_key] = material[parameter]

        return formated_material

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
            Dictionary with soil material parameters with interal Plaxis
            keys.
        dict
            Dictionary with the material parameters with the keys
            provided by the user.

        Raises
        ------
        RuntimeError
            Missing soil material identification.
        RuntimeError
            Multiple soil material identification.
        """
        id_keys = [id_key for id_key in cls._parameter_map['Identification'] if id_key in material]
        if len(id_keys) == 0:
            msg = 'Missing soil material idetinfication for <{}>'.format(cls._soil_name)
            raise RuntimeError(msg)
        if len(id_keys) > 1:
            msg = 'Multiple soil material idetinfications for <{}>: {}'.format(cls._soil_name, ', '.join(id_keys))
            raise RuntimeError(msg)
        formated_material = {'Identification': material[id_keys[0]]}
        _ = material.pop(id_keys[0])
        return formated_material, material

    @classmethod
    def _set_drainage_type(cls, formated_material, material):
        """Extracts the drainage type from input material dictionary.

        Parameters
        ----------
        formated_material : dict
            Dictionary with soil material parameters with interal Plaxis
            keys.
        material : dict
            User provided dictionary with soil material parameters.

        Returns
        -------
        dict
            Dictionary with soil material parameters with interal Plaxis
            keys.
        dict
            User provided dictionary with soil material parameters.

        Raises
        ------
        RuntimeError
            Missing drainage type data.
        RuntimeError
            Multiple drainage type data.
        RuntimeError
            Invalid drainage type data.
        RuntimeError
            Invalid drainage type data for the material type.
        """
    
        drainage_key = []
        for param in material:
            if cls._sanitized_name(param) == 'drainagetype':
                drainage_key.append(param)
        if len(drainage_key) == 0:
            msg = f'Missing <DrainageType> in soil material <{formated_material["Identification"]}>'
            raise RuntimeError(msg)
        elif len(drainage_key) > 1:
            msg = f'Multiple values for <DrainageType> in soil material <{formated_material["Identification"]}>'
            raise RuntimeError(msg)
        
        drainage_type = material[drainage_key[0]]
        _ = material.pop(drainage_key[0])

        valid_drainage_type = False
        for supported in cls._drainage:
            if cls._sanitized_name(drainage_type) == cls._sanitized_name(supported):
                formated_material['DrainageType'] = supported
                valid_drainage_type = True
                break
        
        if not valid_drainage_type:
            msg = 'Drainage type <{}> not supported in soil material <{}>. Supported types are: {}.'
            msg = msg.format(drainage_type, formated_material['Identification'],
                             ', '.join([drngtype for drngtype in cls._drainage if cls._drainage[drngtype]]))
            raise RuntimeError(msg)

        if not cls._drainage[formated_material['DrainageType']]:
            msg = 'Drainage type <{}> not supported in soil material <{}>. Supported types are: {}.'
            msg = msg.format(drainage_type, formated_material['Identification'],
                             ', '.join([drngtype for drngtype in cls._drainage if cls._drainage[drngtype]]))
            raise RuntimeError(msg)

        return formated_material, material

    @classmethod
    def _set_default_values(cls, formated_material, license):
        """Set default values of material paramters not provided by
        the user.

        Parameters
        ----------
        formated_material : dict
            Dictionary with soil material parameters with interal Plaxis
            keys.
        license : str
            Plaxis lincese: 'advanced' or 'ultimate'.

        Returns
        -------
        dict
            Dictionary with soil material parameters with interal Plaxis
            keys.
        """
        if license == 'advanced':
            default_parameters = [param for param in cls._default_parameters if param not in cls._ultimate_parameters]
        elif license == 'ultimate':
            default_parameters = cls._default_parameters
            
        # set constnat values
        for param in default_parameters:
            if param not in formated_material \
               and param in cls._drainage[formated_material['DrainageType']] \
               and not isinstance(cls._default_parameters[param], types.FunctionType):
                formated_material[param] = cls._default_parameters[param]

        # set values that depend on other values
        for param in default_parameters:
            if param not in formated_material \
               and param in cls._drainage[formated_material['DrainageType']] \
               and isinstance(cls._default_parameters[param], types.FunctionType):
                formated_material[param] = cls._default_parameters[param](formated_material)

        return formated_material

    @classmethod
    def _check_parameter_license(cls, formated_material, license):
        """Validates that the specified parameters are supported by
        the license.

        Parameters
        ----------
        formated_material : dict
            Dictionary with soil material parameters with interal Plaxis
            keys.
        license : str
            Plaxis lincese: 'advanced' or 'ultimate'.

        Raises
        ------
        RuntimeError
            parameter not included under the advanced license.
        """
        if license == 'ultimate':
            return
        not_supported = [param for param in formated_material if param in cls._ultimate_parameters]
        if not_supported:
            text = 'Soil parameters {} for soil model <{}> not supported under <advanced> license.'
            text = text.format(', '.join(not_supported), formated_material['Identification'])
            raise RuntimeError(text)

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
        

class Elastic(BaseSoilMaterial):
    """Linear elastic soil material."""
    _soil_model = 1
    _soil_name = 'Linear Elastic'
    _acronyms = ['linearelastic']

    # Dictionary with defualt values for material paramteres
    _default_parameters = {'RayleighDampingInputMethod':'Direct', 
                           'InterfaceStrengthDetermination':'Manual'}

    # List Plaxis ids for the supported parameters for each drainage. If
    # the draiange case is not supported for the material set it to
    # False  
    _drainage = {'Drained': ['Identification',  'DrainageType', 'commments',
                             "gammaSat", "gammaUnsat",
                             "Eref", 'nu', 
                             'RayleighDampingInputMethod', 'RayleighAlpha', 'RayleighBeta',
                             'TargetDamping1', 'TargetDamping2', 'TargetFrequency1', 'TargetFrequency2',
                             'InterfaceStrengthDetermination', 'Rinter', 'RinterResidual',
                             'InterfaceStiffnessDetermination','knInter','ksInter',
                             'K0Determination', 'K0PrimaryIsK0Secondary', 'K0Primary',
                             'K0Secondary',],
                 'Undrained A': ['Identification',  'DrainageType', 'commments',
                                 "gammaSat", "gammaUnsat",
                                 "Eref", 'nu', 
                                 'RayleighDampingInputMethod', 'RayleighAlpha', 'RayleighBeta',
                                 'TargetDamping1', 'TargetDamping2', 'TargetFrequency1', 'TargetFrequency2',
                                 'InterfaceStrengthDetermination', 'Rinter', 'RinterResidual',
                                 'InterfaceStiffnessDetermination','knInter','ksInter',
                                 'K0Determination', 'K0PrimaryIsK0Secondary', 'K0Primary',
                                 'K0Secondary',],
                 'Undrained B': False,
                 'Undrained C': ['Identification',  'DrainageType', 'commments',
                                 "gammaUnsat",
                                 "Eref", 'nu', 
                                 'RayleighDampingInputMethod', 'RayleighAlpha', 'RayleighBeta',  
                                 'TargetDamping1', 'TargetDamping2', 'TargetFrequency1', 'TargetFrequency2', 
                                 'InterfaceStrengthDetermination', 'Rinter', 'RinterResidual',
                                 'InterfaceStiffnessDetermination','knInter','ksInter',
                                 'K0Determination', 'K0PrimaryIsK0Secondary', 'K0Primary',
                                 'K0Secondary',
                                ],
                 'Non-porous': ['Identification',  'DrainageType', 'commments',
                                 "gammaUnsat",
                                 "Eref", 'nu', 
                                 'RayleighDampingInputMethod', 'RayleighAlpha', 'RayleighBeta',
                                 'TargetDamping1', 'TargetDamping2', 'TargetFrequency1', 'TargetFrequency2',
                                 'InterfaceStrengthDetermination', 'Rinter', 'RinterResidual',
                                 'InterfaceStiffnessDetermination','knInter','ksInter',
                                 'K0Determination', 'K0PrimaryIsK0Secondary', 'K0Primary',
                                 'K0Secondary',
                                 ]}


class MohrCoulomb(BaseSoilMaterial):
    """Mohr-Coulomb soil material."""
    _soil_model = 2   
    _soil_name = 'Mohr-Coulomb'
    _acronyms = ['mohrcoulomb', 'mc']

    # Dictionary with defualt values for material paramteres
    _default_parameters = {'RayleighDampingInputMethod':'Direct', 
                           'InterfaceStrengthDetermination':'Manual'}

    # List Plaxis ids for the supported parameters for each drainage. If
    # the draiange case is not supported for the material set it to
    # False  
    _drainage = {'Drained': ['Identification',  'DrainageType', 'commments',
                             'gammaSat', 'gammaUnsat', 'einit',
                             'ERef', 'nu', 'phi', 'psi', 'cref', 'cInc', 'VerticalRef',
                             'TensionCutOff', 'TensileStrength'
                             'RayleighDampingInputMethod', 'RayleighAlpha', 'RayleighBeta',
                             'TargetDamping1', 'TargetDamping2', 'TargetFrequency1', 'TargetFrequency2',
                             'PermHorizontalPrimary', 'PermVertical',
                             'InterfaceStrengthDetermination', 'Rinter', 'RinterResidual',
                             'InterfaceStiffnessDetermination','knInter','ksInter',
                             'K0Determination', 'K0PrimaryIsK0Secondary', 'K0Primary',
                             'K0Secondary'
                             ],
                'Undrained A': ['Identification',  'DrainageType', 'commments',
                                'gammaSat', 'gammaUnsat', 'einit',
                                'ERef', 'nu', 'phi', 'psi', 'cref', 'cInc', 'VerticalRef',
                                'TensionCutOff', 'TensileStrength',
                                'RayleighDampingInputMethod', 'RayleighAlpha', 'RayleighBeta',
                                'TargetDamping1', 'TargetDamping2', 'TargetFrequency1', 'TargetFrequency2',
                                'PermHorizontalPrimary', 'PermVertical',
                                'InterfaceStrengthDetermination', 'Rinter', 'RinterResidual',
                                'InterfaceStiffnessDetermination','knInter','ksInter',
                                'K0Determination', 'K0PrimaryIsK0Secondary', 'K0Primary',
                                'K0Secondary'
                                ],
                'Undrained B': ['Identification',  'DrainageType', 'commments',
                                'gammaSat', 'gammaUnsat', 'einit',
                                'ERef', 'nu', 'cref', 'cInc', 'VerticalRef',
                                'TensionCutOff', 'TensileStrength',
                                'RayleighDampingInputMethod', 'RayleighAlpha', 'RayleighBeta',
                                'TargetDamping1', 'TargetDamping2', 'TargetFrequency1', 'TargetFrequency2',
                                'PermHorizontalPrimary', 'PermVertical',
                                'InterfaceStrengthDetermination', 'Rinter', 'RinterResidual',
                                'InterfaceStiffnessDetermination','knInter','ksInter',
                                'K0Determination', 'K0PrimaryIsK0Secondary', 'K0Primary',
                                'K0Secondary'
                                ],
                'Undrained C': ['Identification',  'DrainageType', 'commments',
                                'gammaUnsat', 'einit',
                                'ERef', 'nu', 'cref', 'cInc', 'VerticalRef',
                                'TensionCutOff', 'TensileStrength',
                                'RayleighDampingInputMethod', 'RayleighAlpha', 'RayleighBeta',
                                'TargetDamping1', 'TargetDamping2', 'TargetFrequency1', 'TargetFrequency2',
                                'PermHorizontalPrimary', 'PermVertical',
                                'InterfaceStrengthDetermination', 'Rinter', 'RinterResidual',
                                'InterfaceStiffnessDetermination','knInter','ksInter',
                                'K0Determination', 'K0PrimaryIsK0Secondary', 'K0Primary',
                                'K0Secondary'
                                ],
                'Non-porous': ['Identification',  'DrainageType', 'commments',
                               'gammaUnsat', 'einit',
                               'ERef', 'nu', 'phi', 'psi', 'cref', 'cInc', 'VerticalRef',
                               'TensionCutOff', 'TensileStrength',
                               'RayleighDampingInputMethod', 'RayleighAlpha', 'RayleighBeta',
                               'TargetDamping1', 'TargetDamping2', 'TargetFrequency1', 'TargetFrequency2',
                               'PermHorizontalPrimary', 'PermVertical',
                               'InterfaceStrengthDetermination', 'Rinter', 'RinterResidual',
                               'InterfaceStiffnessDetermination','knInter','ksInter',
                               'K0Determination', 'K0PrimaryIsK0Secondary', 'K0Primary',
                               'K0Secondary'
                               ]}


class HardeningStrain(BaseSoilMaterial):
    """Hardening-Strain soil material."""
    _soil_model = 3   
    _soil_name = 'Hardening-Strain'
    _acronyms = ['hardeningstrain', 'hs']

    # Dictionary with defualt values for material paramteres
    _default_parameters = {'RayleighDampingInputMethod' : 'Direct', 
                           'InterfaceStrengthDetermination' : 'Manual',
                           'UseDefaults' : True,
                           'K0nc' : lambda material: 1 - np.sin(np.radians(material['phi']))}

    # List Plaxis ids for the supported parameters for each drainage. If
    # the draiange case is not supported for the material set it to
    # False  
    _drainage = {'Drained': ['Identification',  'DrainageType', 'commments',
                             'gammaUnsat', 'gammaSat', 'einit',
                             'E50ref', 'EoedRef', 'EurRef', 'nu', 'powerm', 'pRef', 
                             'phi', 'psi', 'cref', 'cInc', 'VerticalRef',
                             'TensionCutOff', 'TensileStrength',
                             'UseDefaults', 'K0nc', 'RF',
                             'RayleighDampingInputMethod', 'RayleighAlpha', 'RayleighBeta',
                             'TargetDamping1', 'TargetDamping2', 'TargetFrequency1', 'TargetFrequency2',
                             'PermHorizontalPrimary', 'PermVertical',
                             'InterfaceStrengthDetermination', 'Rinter', 'RinterResidual',
                             'InterfaceStiffnessDetermination','knInter','ksInter',
                             'K0Determination', 'K0PrimaryIsK0Secondary', 'K0Primary',
                             'K0Secondary', 'OCR', 'POP'
                             ],
                'Undrained A': ['Identification',  'DrainageType', 'commments',
                                'gammaUnsat', 'gammaSat', 'einit',
                                'E50ref', 'EoedRef', 'EurRef', 'nu', 'powerm', 'pRef', 
                                'phi', 'psi', 'cref', 'cInc', 'VerticalRef',
                                'TensionCutOff', 'TensileStrength',
                                'UseDefaults', 'K0nc', 'RF',
                                'RayleighDampingInputMethod', 'RayleighAlpha', 'RayleighBeta',
                                'TargetDamping1', 'TargetDamping2', 'TargetFrequency1', 'TargetFrequency2',
                                'PermHorizontalPrimary', 'PermVertical',
                                'InterfaceStrengthDetermination', 'Rinter', 'RinterResidual',
                                'InterfaceStiffnessDetermination','knInter','ksInter',
                                'K0Determination', 'K0PrimaryIsK0Secondary', 'K0Primary',
                                'K0Secondary', 'OCR', 'POP'
                                ],
                'Undrained B': ['Identification',  'DrainageType', 'commments',
                                'gammaUnsat', 'gammaSat', 'einit',
                                'E50ref', 'EoedRef', 'EurRef', 'nu', 'powerm', 'pRef', 
                                'cref', 'cInc', 'VerticalRef',
                                'TensionCutOff', 'TensileStrength',
                                'UseDefaults', 'K0nc', 'RF',
                                'RayleighDampingInputMethod', 'RayleighAlpha', 'RayleighBeta',
                                'TargetDamping1', 'TargetDamping2', 'TargetFrequency1', 'TargetFrequency2',
                                'PermHorizontalPrimary', 'PermVertical',
                                'InterfaceStrengthDetermination', 'Rinter', 'RinterResidual',
                                'InterfaceStiffnessDetermination','knInter','ksInter',
                                'K0Determination', 'K0PrimaryIsK0Secondary', 'K0Primary',
                                'K0Secondary', 'OCR', 'POP'
                                ],
                'Undrained C': False,
                'Non-porous': False}


class HSSmall(BaseSoilMaterial):
    """Hardening-Strain with small strain stiffness soil material."""
    _soil_model = 4
    _soil_name = 'Hardening-Strain samll'
    _acronyms = ['hardeningstrainsmall', 'hssmall']

    # Dictionary with defualt values for material paramteres
    _default_parameters = {'RayleighDampingInputMethod':'Direct', 
                           'InterfaceStrengthDetermination':'Manual',
                           'UseDefaults':True,
                           'K0nc' : lambda material: 1 - np.sin(np.radians(material['phi']))}
    
    # List Plaxis ids for the supported parameters for each drainage. If
    # the draiange case is not supported for the material set it to
    # False  
    _drainage = {'Drained': ['Identification',  'DrainageType', 'commments',
                             'gammaUnsat', 'gammaSat', 'einit',
                             'E50ref', 'EoedRef', 'EurRef', 'nu', 'powerm', 'pRef', 
                             'gamma07', 'pRef',
                             'phi', 'psi', 'cref', 'cInc', 'VerticalRef',
                             'TensionCutOff', 'TensileStrength',
                             'RayleighDampingInputMethod', 'RayleighAlpha', 'RayleighBeta',
                             'TargetDamping1', 'TargetDamping2', 'TargetFrequency1', 'TargetFrequency2',
                             'UseDefaults', 'K0nc', 'RF',
                             'PermHorizontalPrimary', 'PermVertical',
                             'InterfaceStrengthDetermination', 'Rinter', 'RinterResidual',
                             'InterfaceStiffnessDetermination','knInter','ksInter',
                             'K0Determination', 'K0PrimaryIsK0Secondary', 'K0Primary',
                             'K0Secondary', 'OCR', 'POP'
                             ],
                'Undrained A': ['Identification',  'DrainageType', 'commments',
                                'gammaUnsat', 'gammaSat', 'einit',
                                'E50ref', 'EoedRef', 'EurRef', 'nu', 'powerm', 'pRef', 
                                'gamma07', 'pRef',
                                'phi', 'psi', 'cref', 'cInc', 'VerticalRef',
                                'TensionCutOff', 'TensileStrength',
                                'RayleighDampingInputMethod', 'RayleighAlpha', 'RayleighBeta',
                                'TargetDamping1', 'TargetDamping2', 'TargetFrequency1', 'TargetFrequency2',
                                'UseDefaults', 'K0nc', 'RF',
                                'PermHorizontalPrimary', 'PermVertical',
                                'InterfaceStrengthDetermination', 'Rinter', 'RinterResidual',
                                'InterfaceStiffnessDetermination','knInter','ksInter',
                                'K0Determination', 'K0PrimaryIsK0Secondary', 'K0Primary',
                                'K0Secondary', 'OCR', 'POP'
                                ],
                'Undrained B': ['Identification',  'DrainageType', 'commments',
                                'gammaUnsat', 'gammaSat', 'einit',
                                'E50ref', 'EoedRef', 'EurRef', 'nu', 'powerm', 'pRef', 
                                'gamma07', 'pRef',
                                'cref', 'cInc', 'VerticalRef',
                                'TensionCutOff', 'TensileStrength',
                                'RayleighDampingInputMethod', 'RayleighAlpha', 'RayleighBeta',
                                'TargetDamping1', 'TargetDamping2', 'TargetFrequency1', 'TargetFrequency2',
                                'UseDefaults', 'K0nc', 'RF',
                                'PermHorizontalPrimary', 'PermVertical',
                                'InterfaceStrengthDetermination', 'Rinter', 'RinterResidual',
                                'InterfaceStiffnessDetermination','knInter','ksInter',
                                'K0Determination', 'K0PrimaryIsK0Secondary', 'K0Primary',
                                'K0Secondary', 'OCR', 'POP'
                                ],
                'Undrained C': False,
                'Non-porous': False}


class SoilMaterialSelector():
    """Soil materila selector"""

    _materials = [Elastic, MohrCoulomb, HardeningStrain, HSSmall]

    def __init__(self):
        """Initialize a new instance of `SoilMaterialSelector`.
        """
    
    #===================================================================
    # PUBLIC METHODS
    #===================================================================
    @classmethod
    def create_material(cls, g_i, material, license):
        """Creates a new material in the model.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        material : dict
            Dictionary with soil material properties
        license : str
            Plaxis lincese: 'advanced' or 'ultimate'.

        Returns
        -------
        CombinedClass
            Plaxis object of the soil material.


        Raises
        ------
        RuntimeError
            Missing soil model id.
        RuntimeError
            Requeste soil model not supported.
        """
        if "SoilModel" not in material:
            msg = 'Soil material model must be provided under the <SoilModel> key. Supported soil material models are: {}.'
            msg = msg.format(', '.join([mat._soil_name for mat in cls._materials]))
            raise RuntimeError(msg)
        
        for material_class in cls._materials:
            if material_class._sanitized_name(material['SoilModel']) in material_class._acronyms:
                return material_class._create_material(g_i, material, license)

        msg = 'Soil material model <{}> not supported. Supported soil material models are: {}.'
        msg = msg.format(material['SoilModel'], ', '.join([mat._soil_name for mat in cls._materials]))
        raise RuntimeError(msg)


