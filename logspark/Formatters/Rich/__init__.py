from ..._Internal.State import is_dependency_available
from ...Types import MissingDependencyException

if not is_dependency_available("rich"):
    raise MissingDependencyException(["Rich"])
