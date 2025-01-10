from padtest.model.plate import SymmetricPlateModel as SPlate
from padtest.model.plate import NonSymmetricPlateModel as Plate
from padtest.model.solid import SymmetricSolidModel as SSolid
from padtest.model.solid import NonSymmetricSolidModel as Solid
# load model
load = Solid.load

# concrete plates
from padtest.material.plate import PlateMaterial
concrete = PlateMaterial.concrete