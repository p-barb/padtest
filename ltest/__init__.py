from ltest.model.plate import SymmetricPlateModel as SPlate
from ltest.model.plate import NonSymmetricPlateModel as Plate
from ltest.model.solid import SymmetricSolidModel as SSolid
from ltest.model.solid import NonSymmetricSolidModel as Solid
# load model
load = Solid.load

# concrete plates
from ltest.material.plate import PlateMaterial
concrete = PlateMaterial.concrete