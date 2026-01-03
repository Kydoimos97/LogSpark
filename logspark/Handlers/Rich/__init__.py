from ..._Internal.State import is_rich_available
from ...Types import MissingDependencyException

if not is_rich_available():
    raise MissingDependencyException(["Rich"])
