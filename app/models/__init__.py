# import all submodules here so when i import from app.models, all table metadata would have loaded into the SQLModel class
from app.auth import models
from app.materials import models as material_models