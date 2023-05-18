import os
import json

from cmlibs.zinc.context import Context
from cmlibs.zinc.status import OK as ZINC_OK

from cmlibs.utils.zinc.general import ChangeManager
from cmlibs.utils.zinc.finiteelement import create_nodes, create_triangle_elements

from cmlibs.importer.base import valid
from cmlibs.importer.errors import ImporterImportInvalidInputs, ImporterImportUnknownParameter, ImporterImportError


def _load_mesh_from_json(region, contents, coordinate_field_name):
    """
    Loads a Zinc mesh from dictionary of WebGL triangular mesh information.
    """
    field_module = region.getFieldmodule()

    # Create coordinate field.
    coordinate_field = field_module.findFieldByName(coordinate_field_name)
    if not coordinate_field.isValid():
        coordinate_field = field_module.createFieldFiniteElement(3)
        coordinate_field.setName(coordinate_field_name)
    coordinate_field.setManaged(True)
    coordinate_field.setTypeCoordinate(True)

    # Create nodes.
    node_set_size = field_module.findNodesetByName('nodes').getSize()
    node_coordinates = _group_coordinates(contents['vertices'], 3)
    create_nodes(coordinate_field, node_coordinates)

    # Create elements.
    mesh = field_module.findMeshByDimension(2)
    element_node_set = _group_element_nodes(contents['faces'], 3)
    _increment_node_identifiers(element_node_set, node_set_size + 1)
    create_triangle_elements(mesh, coordinate_field, element_node_set)


def _group_coordinates(coordinate_list, dimensions):
    if hasattr(coordinate_list[0], '__iter__'):
        return coordinate_list

    if len(coordinate_list) % dimensions != 0:
        raise ShapeError("The number of coordinate components does not match the number of dimensions.")

    node_list = []
    for i in range(0, len(coordinate_list), dimensions):
        node_list.append(coordinate_list[i:i+dimensions])

    return node_list


def _group_element_nodes(element_list, dimensions):
    if hasattr(element_list[0], '__iter__'):
        return element_list

    element_node_set = []
    for i in range(1, len(element_list), 2 * dimensions + 1):
        element_node_set.append(element_list[i:i+dimensions])
    return element_node_set


def _increment_node_identifiers(element_node_set, increment):
    for element in element_node_set:
        if 0 in element:
            break
        else:
            return

    for i in range(len(element_node_set)):
        element_node_set[i] = [x+increment for x in element_node_set[i]]


class ShapeError(Exception):
    pass


def import_data_into_region(region, inputs, coordinate_field_name='mesh_coordinates'):
    """
    This method is intended as an importer for scenes exported by the cmlibs.exporter.webgl.ArgonSceneExporter class. A Zinc mesh is
    created in the supplied region using the data from the input file. Input files should be in WebGL JSON format.
    """
    if not valid(inputs, parameters("input")):
        raise ImporterImportInvalidInputs(f"Invalid input given to importer: {identifier()}")

    with open(inputs, "r") as json_file:
        contents = json.load(json_file)

    field_module = region.getFieldmodule()
    with ChangeManager(field_module):
        _load_mesh_from_json(region, contents, coordinate_field_name)


def import_data(inputs, output_directory):
    context = Context(identifier())
    region = context.getDefaultRegion()

    import_data_into_region(region, inputs)

    # Inputs has already been validated by this point so it is safe to use.
    filename_parts = os.path.splitext(os.path.basename(inputs))
    output_exf = os.path.join(output_directory, filename_parts[0] + ".exf")
    result = region.writeFile(output_exf)

    output = None
    if result == ZINC_OK:
        output = output_exf

    return output


def identifier():
    return "WebGLJSON"


def parameters(parameter_name=None):
    importer_parameters = {
        "version": "0.1.0",
        "id": identifier(),
        "title": "WebGL JSON",
        "description":
            "WebGL JSON file format. This is a file format produced by the CMLibs WebGL ArgonSceneExporter. It contains lists of nodes "
            "and faces that can be used to create a CMLibs Zinc triangular-element mesh.",
        "input": {
            "mimetype": "application/json",
        },
        "output": {
            "mimetype": "text/x.vnd.abi.exf+plain",
        }
    }

    if parameter_name is not None:
        if parameter_name in importer_parameters:
            return importer_parameters[parameter_name]
        else:
            raise ImporterImportUnknownParameter(f"Importer '{identifier()}' does not have parameter: {parameter_name}")

    return importer_parameters
