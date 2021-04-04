
from aiida.orm import Node, load_node, Bool
from aiida.plugins import DataFactory, CalculationFactory

def is_code(code):
    """
    Test if the given input is a Code node, by object, id, uuid, or pk
    if yes returns a Code node in all cases
    if no returns None
    """
    from aiida.orm import Code
    from aiida.common.exceptions import NotExistent, MultipleObjectsError, InputValidationError

    if isinstance(code, Code):
        return code

    try:
        pk = int(code)
    except ValueError:
        codestring = str(code)
        try:
            code = Code.get_from_string(codestring)
        except NotExistent:
            try:
                code = load_node(codestring)
            except NotExistent:
                code = None
        except (InputValidationError, MultipleObjectsError):
            code = None
    else:
        try:
            code = load_node(pk)
        except NotExistent:
            code = None

    if isinstance(code, Code):
        return code
    else:
        return None


def get_inputs_spex(inp_layout, remote, spexcode, options, label='', description='', settings=None, params=None, **kwargs):
    '''
    Assembles the input dictionary for Spex Calculation.

    :param inp_layout: layout of the spex.inp file
    :param remote: remote_folder from the previous calculation of RemoteData type
    :param spexcode: spex code of Code type
    :param options: calculation options that will be stored in metadata
    :param label: a string setting a label of the CalcJob in the DB
    :param description: a string setting a description of the CalcJob in the DB
    :param params: input parameters for spex code of Dict type

    Example of use::

        inputs_build = get_inputs_spex(inp_layout, spexcode, options, label,
                                         description, params=params)
        future = self.submit(inputs_build)

    '''

    SpexProcess = CalculationFactory('spex.spex')
    inputs = SpexProcess.get_builder()

    if inp_layout:
        inputs['inp_layout'] = inp_layout
    if remote:
        inputs['parent_folder'] = remote
    if spexcode:
        inputs['code'] = spexcode
    if params:
        inputs['parameters'] = params
    if settings:
        inputs['settings'] = settings
    if description:
        inputs['metadata']['description'] = description
    else:
        inputs['metadata']['description'] = ''

    if label:
        inputs['metadata']['label'] = label
    else:
        inputs['metadata']['label'] = ''

    if not options:
        options = {}

    if options:
        inputs['metadata']['options'] = options

    return inputs


def test_and_get_codenode(codenode, expected_code_type, use_exceptions=False):
    """
    Pass a code node and an expected code (plugin) type. Check that the
    code exists, is unique, and return the Code object.

    :param codenode: the name of the code to load (in the form label@machine)
    :param expected_code_type: a string with the plugin that is expected to
      be loaded. In case no plugins exist with the given name, show all existing
      plugins of that type
    :param use_exceptions: if True, raise a ValueError exception instead of
      calling sys.exit(1)
    :return: a Code object
    """
    import sys
    from aiida.common.exceptions import NotExistent
    from aiida.orm import Code

    try:
        if codenode is None or not isinstance(codenode, Code):
            raise ValueError
        code = codenode
        if code.get_input_plugin_name() != expected_code_type:
            raise ValueError
    except ValueError as exc:
        from aiida.orm.querybuilder import QueryBuilder
        qb = QueryBuilder()
        qb.append(Code, filters={'attributes.input_plugin': {'==': expected_code_type}}, project='*')

        valid_code_labels = ['{}@{}'.format(c.label, c.computer.name) for [c] in qb.all()]

        if valid_code_labels:
            msg = ('Given Code node is not of expected code type.\n'
                   'Valid labels for a {} executable are:\n'.format(expected_code_type))
            msg += '\n'.join('* {}'.format(l) for l in valid_code_labels)

            if use_exceptions:
                raise ValueError(msg) from exc
            else:
                print(msg)  # , file=sys.stderr)
                sys.exit(1)
        else:
            msg = ('Code not valid, and no valid codes for {}.\n'
                   'Configure at least one first using\n'
                   '    verdi code setup'.format(expected_code_type))
            if use_exceptions:
                raise ValueError(msg) from exc
            else:
                print(msg)  # , file=sys.stderr)
                sys.exit(1)

    return code

def find_last_submitted_calcjob(restart_wc):
    """
    Finds the last CalcJob submitted in a higher-level workchain
    and returns it's uuid
    """
    from aiida.common.exceptions import NotExistent
    from aiida.orm import CalcJobNode
    links = restart_wc.get_outgoing().all()
    calls = list([x for x in links if isinstance(x.node, CalcJobNode)])
    if calls:
        calls = sorted(calls, key=lambda x: x.node.pk)
        return calls[-1].node.uuid
    else:
        raise NotExistent