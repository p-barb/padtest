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

    def __init__(self):
        """Initialize a new instance of `BaseSoilMaterial`.
        """
        pass
    
    #===================================================================
    # PRIVATE METHODS
    #===================================================================
    @classmethod
    def _create_material(cls, g_i, material):
        """Adds material to the model.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        dict
            Dictionary with soil material parameters.

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
        formated_material = cls._check_parameters(material)
        try:
            return g_i.soilmat(*formated_material.items())
        except:
            msg = 'Unable to create <{}> material <{}>. Check error message in Plaxis command line history for details.'
            msg = msg.format(cls._soil_name, formated_material['Identification'])
            raise RuntimeError(msg)

    @classmethod  
    def _check_parameters(cls, material):
        """Validates user provided soil material paramteres.

        Parameters
        ----------
        material : dict
            User provided dictionary with soil material parameters.

        Returns
        -------
        dict
            Dictionary with soil material parameters with interal Plaxis
            keys.
        
        Raises
        ------
        RuntimeError
            Unknown material parameter.
        RuntimeError
            Duplicated material parameter
        """
        
        formated_material = {}
        for parameter in material:
            sanitized_param = cls._sanitized_name(parameter)
            found = False
            for plx_key, supported in cls._parameter_map.items():
                supported = [cls._sanitized_name(item) for item in supported]
                if sanitized_param in supported:
                    found = True
                    break
            
            if not found:
                msg = "Unknown material parameter <{}> in <{}>  for <{}>."
                msg = msg.format(parameter, formated_material['Identification'], cls._soil_name)
                raise RuntimeError(msg)
            
            if plx_key in formated_material:
                msg = "Duplicated soil material parameter <{}> as <{}> in <{}>.".format(plx_key, parameter, formated_material['Identification'])
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
        

class Elastic(BaseSoilMaterial):
    """Linear elastic soil material."""
    _soil_model = 1
    _soil_name = 'Linear Elastic'
    _acronyms = ['linearelastic']

class MohrCoulomb(BaseSoilMaterial):
    """Mohr-Coulomb soil material."""
    _soil_model = 2   
    _soil_name = 'Mohr-Coulomb'
    _acronyms = ['mohrcoulomb', 'mc']


class HardeningStrain(BaseSoilMaterial):
    """Hardening-Strain soil material."""
    _soil_model = 3   
    _soil_name = 'Hardening-Strain'
    _acronyms = ['hardeningstrain', 'hs']


class HSSmall(BaseSoilMaterial):
    """Hardening-Strain with small strain stiffness soil material."""
    _soil_model = 4
    _soil_name = 'Hardening-Strain samll'
    _acronyms = ['hardeningstrainsmall', 'hssmall']


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
    def create_material(cls, g_i, material):
        """Creates a new material in the model.

        Parameters
        ----------
        g_i : PlxProxyGlobalObject
            Global object of the current open Plaxis model in Input.
        material : dict
            Dictionary with soil material properties.

        Returns
        -------
        CombinedClass
            Plaxis object of the soil material.


        Raises
        ------
        RuntimeError
            Missing soil model id.
        RuntimeError
            Soil model not supported.
        """
        if "SoilModel" not in material:
            msg = 'Soil material model must be provided under the <SoilModel> key. Supported soil material models are: {}.'
            msg = msg.format(', '.join([mat._soil_name for mat in cls._materials]))
            raise RuntimeError(msg)
        
        for material_class in cls._materials:
            if material_class._sanitized_name(material['SoilModel']) in material_class._acronyms:
                return material_class._create_material(g_i, material)

        msg = 'Soil material model <{}> not supported. Supported soil material models are: {}.'
        msg = msg.format(material['SoilModel'], ', '.join([mat._soil_name for mat in cls._materials]))
        raise RuntimeError(msg)


