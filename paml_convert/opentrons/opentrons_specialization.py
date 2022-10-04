import os
import json
import logging
from typing import Dict
from paml_convert.plate_coordinates import get_aliquot_list

import sbol3
import tyto
import paml
import uml

from paml_convert.behavior_specialization import BehaviorSpecialization


l = logging.getLogger(__file__)
l.setLevel(logging.ERROR)


container_ontology_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../container-ontology/owl/container-ontology.ttl')
ContO = tyto.Ontology(path=container_ontology_path, uri='https://sift.net/container-ontology/container-ontology')

# Map OT2 pipette names to compatible tipracks
COMPATIBLE_TIPS = {
    'p20_single_gen2': ['opentrons_96_tiprack_10ul',
                        'opentrons_96_filtertiprack_10ul'],
    'p300_single_gen2': ['opentrons_96_tiprack_300ul'],
    'p1000_single_gen2': ['opentrons_96_tiprack_1000ul',
                          'opentrons_96_filtertiprack_1000ul'],
    'p300_multi_gen2': [],
    'p20_multi_gen2': [],
    'p10_single': ['opentrons_96_tiprack_10ul',
                   'opentrons_96_filtertiprack_10ul'],
    'p10_multi': ['opentrons_96_tiprack_10ul',
                  'opentrons_96_filtertiprack_10ul'],
    'p50_single': [],
    'p50_multi': [],
    'p300_single': ['opentrons_96_tiprack_300ul'],
    'p300_multi': [],
    'p1000_single': ['opentrons_96_tiprack_1000ul',
                     'opentrons_96_filtertiprack_1000ul'],
}


# Map terms in the Container ontology to OT2 API names
LABWARE_MAP = {
    'cont:Opentrons96TipRack10uL': 'opentrons_96_tiprack_10ul',
    'cont:Opentrons96TipRack300uL': 'opentrons_96_tiprack_300ul',
    'cont:Opentrons96TipRack1000uL': 'opentrons_96_tiprack_1000ul',
    'cont:Opentrons96FilterTipRack10uL': 'opentrons_96_filtertiprack_10ul',
    'cont:Opentrons96FilterTipRack200uL': 'opentrons_96_filtertiprack_200ul',
    'cont:Opentrons96FilterTipRack1000uL': 'opentrons_96_filtertiprack_1000ul',
    'cont:Opentrons24TubeRackwithEppendorf1.5mLSafe-LockSnapcap': 'opentrons_24_tuberack_eppendorf_1.5ml_safelock_snapcap',
    'cont:Corning96WellPlate360uLFlat': 'corning_96_wellplate_360ul_flat',
}


class OT2Specialization(BehaviorSpecialization):

    EQUIPMENT = {
        'p20_single_gen2': sbol3.Agent('p20_single_gen2', name='P20 Single GEN2'),
        'p300_single_gen2': sbol3.Agent('p300_single_gen2', name='P300 Single GEN2'),
        'p1000_single_gen2': sbol3.Agent('p1000_single_gen2', name='P1000 Single GEN2'),
        'p300_multi_gen2': sbol3.Agent('p300_multi_gen2', name='P300 Multi GEN2'),
        'p20_multi_gen2': sbol3.Agent('p20_multi_gen2', name='P20 Multi GEN2'),
        'p10_single': sbol3.Agent('p10_single', name='P10 Single'),
        'p10_multi': sbol3.Agent('p10_multi', name='P10 Multi'),
        'p50_single': sbol3.Agent('p50_single', name='P50 Single'),
        'p50_multi': sbol3.Agent('p50_multi', name='P50 Multi'),
        'p300_single': sbol3.Agent('p300_single', name='P300 Single'),
        'p300_multi': sbol3.Agent('p300_multi', name='P300 Multi'),
        'p1000_single': sbol3.Agent('p1000_single', name='P1000 Single'),
        'temperature_module': sbol3.Agent('temperature_module', name='Temperature Module GEN1'),
        'tempdeck': sbol3.Agent('temperature_module', name='Temperature Module GEN1'),
        'temperature_module_gen2': sbol3.Agent('temperature_module_gen2', name='Temperature Module GEN2'),
        'magnetic_module': sbol3.Agent('magdeck', name='Magnetic Module GEN1'),
        'magnetic_module_gen2': sbol3.Agent('magnetic_module_gen2', name='Magnetic Module GEN2'),
        'thermocycler_module': sbol3.Agent('thermocycler_module', name='Thermocycler Module'),
        'thermocycler': sbol3.Agent('thermocycler_module', name='Thermocycler Module')
    }

    def __init__(self, filename, resolutions: Dict[sbol3.Identified,str] = None) -> None:
        super().__init__()
        self.resolutions = resolutions
        self.var_to_entity = {}
        self.script = ''
        self.script_steps = []
        self.markdown = ''
        self.markdown_steps = []
        self.apilevel = '2.11'
        self.configuration = {}
        self.filename = filename

        # Needed for using container ontology
        self.container_api_addl_conditions = "(cont:availableAt value <https://sift.net/container-ontology/strateos-catalog#Strateos>)"


    def _init_behavior_func_map(self) -> dict:
        """
        This function redirects processing of each primitive to the functions
        defined below.  Adding additional mappings here is most likely required.
        """
        return {
            "https://bioprotocols.org/paml/primitives/sample_arrays/EmptyContainer" : self.define_container,
            "https://bioprotocols.org/paml/primitives/liquid_handling/Provision" : self.provision,
            "https://bioprotocols.org/paml/primitives/liquid_handling/Transfer" : self.transfer_to,
            "https://bioprotocols.org/paml/primitives/liquid_handling/TransferByMap" : self.transfer_by_map,
            "https://bioprotocols.org/paml/primitives/sample_arrays/PlateCoordinates" : self.plate_coordinates,
            "https://bioprotocols.org/paml/primitives/spectrophotometry/MeasureAbsorbance" : self.measure_absorbance,
            "https://bioprotocols.org/paml/primitives/sample_arrays/EmptyRack" : self.define_rack,
            "https://bioprotocols.org/paml/primitives/sample_arrays/LoadContainerInRack" : self.load_containers,
            "https://bioprotocols.org/paml/primitives/sample_arrays/LoadRackOnInstrument" : self.load_racks,
            "https://bioprotocols.org/paml/primitives/sample_arrays/ConfigureInstrument" : self.configure_instrument,
        }

    def handle_process_failure(self, record):
        super().handle_process_failure(record)
        self.script_steps.append(f"# Failure processing record: {record.identity}")

    def on_begin(self, ex: paml.ProtocolExecution):

        protocol = self.execution.protocol.lookup()
        apilevel = self.apilevel
        self.markdown += f"# {protocol.name}\n"
        self.script += "from opentrons import protocol_api\n\n" \
                       f"metadata = {{'apiLevel': '{apilevel}',\n" \
                       f"            'description': '{protocol.description}'\n" \
                       f"            'protocolName': '{protocol.name}'}} \n\n" \
                       "def run(protocol: protocol_api.ProtocolContext):\n"

    def on_end(self, ex):
        self.script += self._compile_script()
        self.markdown += self._compile_markdown()
        if self.filename:
            with open(self.filename + '.py', 'w') as f:
                f.write(self.script)
            with open(self.filename + '.md', 'w') as f:
                f.write(self.markdown)
            print(f"Successful execution. Script dumped to {self.filename}.")
        else:
            l.warn("Writing output of specialization to self.data because no filename specified.")
            self.data = f"# OT2 Script\n ```python\n{self.script}```\n # Operator Script\n {self.markdown}"

    def _compile_script(self):
        script = ''
        for step in self.script_steps:
           script += f'    {step}\n'
        return script

    def _compile_markdown(self):
        markdown = self._materials()
        markdown += '\n## Steps\n'
        for i, step in enumerate(self.markdown_steps):
           markdown += str(i + 1) + '. ' + step + '\n'
        return markdown

    def _tipracks(self, left,right):
        leftTipID = left["pipette"]
        rightTipID = right["pipette"]
        tipCount=0
        tipList=""
        markdown=""
        for tiprack in left["tipracks"]:
            tiprackID = tiprack["id"]
            tiprackDeck = tiprack["deck"]
            tipList += f"leftTiprack{tipCount},"
            markdown += f"leftTiprack{tipCount} = protocol.load_labware('{tiprackID}', {tiprackDeck})\n"
            tipCount+=1
        markdown += f"left = protocol.load_instrument('{leftTipID}', 'left', tip_rack={tipList[:-1]})\n"
        tipCount=0
        tipList=""
        for tiprack in right["tipracks"]:
            tiprackID = tiprack["id"]
            tiprackDeck = tiprack["deck"]
            tipList += f"rightTiprack{tipCount},"
            markdown += f"rightTiprack{tipCount} = protocol.load_labware('{tiprackID}', {tiprackDeck})\n"
            tipCount+=1
        markdown += f"right = protocol.load_instrument('{rightTipID}', 'right', tip_rack={tipList[:-1]})\n"
        #return markdown

    def _materials(self):
        protocol = self.execution.protocol.lookup()

        materials = {obj.name: obj for obj in protocol.document.objects
                     if type(obj) is sbol3.Component }
        markdown = '\n\n## Protocol Materials:\n'
        for name, material  in materials.items():
            markdown += f"* [{name}]({material.types[0]})\n"

        # Compute container types and quantities
        document_objects = []
        protocol.document.traverse(lambda obj: document_objects.append(obj))
        call_behavior_actions = [obj for obj in document_objects if type(obj) is uml.CallBehaviorAction]
        containers = {}
        for cba in call_behavior_actions:
            input_names = [input.name for input in cba.inputs]
            if 'specification' in input_names:
                container = cba.input_pin('specification').value.value.lookup()
            elif 'rack' in input_names:
                container = cba.input_pin('rack').value.value.lookup()
            elif 'container' in input_names:
                container = cba.input_pin('container').value.value.lookup()
            else:
                continue
            container_type = container.queryString
            container_name = container.name if container.name else 'unnamed'
            qty = cba.input_pin('quantity') if 'quantity' in input_names else 1

            if container_type not in containers:
                containers[container_type] = {}
            containers[container_type][container_name] = qty

        for container_type, container_name_map in containers.items():
            for container_name, qty in container_name_map.items():
                container_class = ContO.uri + '#' + container_type.split(':')[-1]
                container_str = ContO.get_term_by_uri(container_class)
                if 'TipRack' in container_type:
                    text = f'* {container_str}'
                elif container_name == 'unnamed':
                    text = f'* unnamed {container_str}'
                else:
                    text = f'* `{container_name}` ({container_str})'
                if qty > 1:
                    text += f' (x {qty})'
                text += '\n'
                markdown += text

        return markdown

    def _parameter_value_markdown(self, pv : paml.ParameterValue, is_output=False):
        parameter = pv.parameter.lookup().property_value
        value = pv.value.lookup().value if isinstance(pv.value, uml.LiteralReference) else pv.value.value
        units = tyto.OM.get_term_by_uri(value.unit) if isinstance(value, sbol3.om_unit.Measure) else None
        value = str(f"{value.value} {units}")  if units else str(value)
        if is_output:
            return f"* `{parameter.name}`"
        else:
            return f"* `{parameter.name}` = {value}"

    def define_container(self, record: paml.ActivityNodeExecution, ex: paml.ProtocolExecution):
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()

        spec = parameter_value_map["specification"]['value']
        samples = parameter_value_map["samples"]['value']

        #TODO: initialize sample contents

    def time_wait(self, record: paml.ActivityNodeExecution, ex: paml.ProtocolExecution):
        results = {}
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()
        value = parameter_value_map["amount"]["value"].value
        units = parameter_value_map["amount"]["value"].unit
        self.script_steps += [f"time.sleep(value)"]


    def provision(self, record: paml.ActivityNodeExecution, ex: paml.ProtocolExecution):
        results = {}
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()
        destination = parameter_value_map["destination"]["value"]
        value = parameter_value_map["amount"]["value"].value
        units = parameter_value_map["amount"]["value"].unit
        units = tyto.OM.get_term_by_uri(units)
        resource = parameter_value_map["resource"]["value"]
        amount = parameter_value_map["amount"]["value"]
        amount = measurement_to_text(amount)

        coords = ''
        coords = destination.get_parent().get_parent().token_source.lookup().node.lookup().input_pin('coordinates').value.value
        upstream_execution = get_token_source('destination', record)
        behavior_type = get_behavior_type(upstream_execution)
        if behavior_type == 'LoadContainerInRack':
            coords = upstream_execution.call.lookup().parameter_value_map()['coordinates']['value']
            upstream_execution = get_token_source('slots', upstream_execution)
            container = upstream_execution.call.lookup().parameter_value_map()['specification']['value']
        else:
            raise NotImplementedError(f'A "Provision" call cannot follow a "{behavior_type}" call')
        container_str = f'`{container.name}`' if container.name else container.queryString

        text = f'Load {amount} of {resource.name} in {coords} of {container_str}'
        self.markdown_steps += [text]


    def transfer_to(self, record: paml.ActivityNodeExecution, ex: paml.ProtocolExecution):

        results = {}
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()
        destination = parameter_value_map["destination"]["value"]
        source = parameter_value_map["source"]["value"]
        value = parameter_value_map["amount"]["value"].value
        units = parameter_value_map["amount"]["value"].unit
        units = tyto.OM.get_term_by_uri(units)
        OT2Pipette="left"

        # Trace the "source" pin back to the EmptyContainer to retrieve the
        # ContainerSpec for the destination container
        upstream_execution = get_token_source('source', record)
        behavior_type = get_behavior_type(upstream_execution)
        if behavior_type == 'LoadContainerInRack':
            upstream_execution = get_token_source('slots', upstream_execution)  # EmptyRack
            parameter_value_map = upstream_execution.call.lookup().parameter_value_map()
            source_container = parameter_value_map['specification']['value']
        else:
            raise Exception(f'Invalid input pin "source" for Transfer.')

        # Map the source container to a variable name in the OT2 api script
        source_name = None
        for deck, labware in self.configuration.items():
            if labware == source_container:
                source_name = f'labware{deck}'
                break
        if not source_name:
            raise Exception(f'{source_container} is not loaded.')

        # Trace the "destination" pin back to the EmptyContainer execution
        # to retrieve the ContainerSpec for the destination container
        upstream_execution = get_token_source('destination', record)
        behavior_type = get_behavior_type(upstream_execution)
        if behavior_type == 'PlateCoordinates':
            upstream_execution = get_token_source('source', upstream_execution)  # EmptyContainer
            parameter_value_map = upstream_execution.call.lookup().parameter_value_map()
            destination_container = parameter_value_map['specification']['value']
        else:
            raise Exception(f'Invalid input pin "destination" for Transfer.')
        destination_name = None
        for deck, labware in self.configuration.items():
            if labware == destination_container:
                destination_name = f'labware{deck}'
                break
        if not destination_name:
            raise Exception(f'{destination_container} is not loaded.')

        # TODO: automatically choose pipette based on transferred volume
        if not self.configuration:
            raise Exception('Transfer call failed. Use ConfigureInstrument to configure a pipette')
        pipette = self.configuration['left']

        source_str = source.mask
        destination_str = destination.mask
        for c_source in get_aliquot_list(source.mask):
            for c_destination in get_aliquot_list(destination.mask):
                self.script_steps += [f"{pipette.display_id}.transfer({value}, {source_name}['{c_source}'], {destination_name}['{c_destination}'])"]


    def transfer_by_map(self, record: paml.ActivityNodeExecution, ex: paml.ProtocolExecution):

        results = {}
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()
        destination = parameter_value_map["destination"]["value"]
        source = parameter_value_map["source"]["value"]
        plan = parameter_value_map["plan"]["value"]
        temperature = parameter_value_map["temperature"]["value"]
        value = parameter_value_map["amount"]["value"].value
        units = parameter_value_map["amount"]["value"].unit
        units = tyto.OM.get_term_by_uri(units)
        OT2Pipette="left"

        # Trace the "source" pin back to the EmptyContainer to retrieve the
        # ContainerSpec for the destination container
        upstream_execution = record.get_token_source('source')
        behavior_type = get_behavior_type(upstream_execution)
        if behavior_type == 'LoadContainerInRack':
            upstream_execution = upstream_execution.get_token_source('slots')  # EmptyRack
            parameter_value_map = upstream_execution.call.lookup().parameter_value_map()
            source_container = parameter_value_map['specification']['value']
        else:
            raise Exception(f'Invalid input pin "source" for Transfer.')

        # Map the source container to a variable name in the OT2 api script
        source_name = None
        for deck, labware in self.configuration.items():
            if labware == source_container:
                source_name = f'labware{deck}'
                break
        if not source_name:
            raise Exception(f'{source_container} is not loaded.')

        # Trace the "destination" pin back to the EmptyContainer execution
        # to retrieve the ContainerSpec for the destination container
        upstream_execution = record.get_token_source('destination')
        behavior_type = get_behavior_type(upstream_execution)
        if behavior_type == 'PlateCoordinates':
            upstream_execution = get_token_source('source', upstream_execution)  # EmptyContainer
            parameter_value_map = upstream_execution.call.lookup().parameter_value_map()
            destination_container = parameter_value_map['specification']['value']
        else:
            raise Exception(f'Invalid input pin "destination" for Transfer.')
        destination_name = None
        for deck, labware in self.configuration.items():
            if labware == destination_container:
                destination_name = f'labware{deck}'
                break
        if not destination_name:
            raise Exception(f'{destination_container} is not loaded.')

        # TODO: automatically choose pipette based on transferred volume
        if not self.configuration:
            raise Exception('Transfer call failed. Use ConfigureInstrument to configure a pipette')
        pipette = self.configuration['left']

        source_str = source.mask
        destination_str = destination.mask
        for c_source in get_aliquot_list(source.mask):
            for c_destination in get_aliquot_list(destination.mask):
                self.script_steps += [f"{pipette.display_id}.transfer({value}, {source_name}['{c_source}'], {destination_name}['{c_destination}'])"]

    def plate_coordinates(self, record: paml.ActivityNodeExecution, ex: paml.ProtocolExecution):
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()
        source = parameter_value_map["source"]["value"]
        coords = parameter_value_map["coordinates"]["value"]
        samples = parameter_value_map['samples']['value']
        samples.mask = coords

    def measure_absorbance(self, record: paml.ActivityNodeExecution, ex: paml.ProtocolExecution):
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()

        wl = parameter_value_map["wavelength"]["value"]
        wl_units = tyto.OM.get_term_by_uri(wl.unit)
        samples = parameter_value_map["samples"]["value"]

        samples_str = f"`{samples.source.lookup().value.lookup().value.name}({samples.mask})`"
        self.script_steps +=[f'protocol.comment(\'Make absorbance measurements (named `{measurements}`) of {samples_str} at {wl.value} {wl_units}.\')']


    def define_rack(self, record: paml.ActivityNodeExecution, ex: paml.ProtocolExecution):
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()

        spec = parameter_value_map['specification']['value']
        slots = parameter_value_map['slots']['value']

        # FIXME the protocol var_to_entity mapping links variables created in
        # the execution trace with real values assigned here, such as
        # container below.  This mapping can be used in later processing to
        # reuse bindings.
        #
        # self.var_to_entity[samples_var] = container

        #OT2Props = json.loads(spec.OT2SpecificProps)
        #OT2Deck = OT2Props["deck"]

    def load_containers(self, record: paml.ActivityNodeExecution, ex: paml.ProtocolExecution):
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()
        container: paml.ContainerSpec = parameter_value_map['container']['value']
        coords: str = parameter_value_map['coordinates']['value'] if 'coordinates' in parameter_value_map else 'A1'
        slots: paml.SampleCollection = parameter_value_map['slots']['value']
        samples: paml.SampleMask = parameter_value_map['samples']['value']

        # TODO: validate coordinates for the given container spec
        samples.source = slots
        samples.mask = coords
        container_str = get_container_name(container)

        rack_str = ''
        try:
            # TODO: replace this lookup with a call to get_token_source()
            rack = slots.get_parent().get_parent().token_source.lookup().node.lookup().input_pin('specification').value.value.lookup()
            rack_str = get_container_name(rack)
        except Exception as e:
            print(e)

        aliquots = get_aliquot_list(coords)
        if len(aliquots) == 1:
            self.markdown_steps += [f'Load {container_str} in slot {coords} in {rack_str}']
        elif len(aliquots) > 1:
            self.markdown_steps += [f'Load {container_str}s in slots {coords} in {rack_str}']



    def load_racks(self, record: paml.ActivityNodeExecution, ex: paml.ProtocolExecution):
        call = record.call.lookup()
        node = record.node.lookup()
        parameter_value_map = call.parameter_value_map()
        coords: str = parameter_value_map['coordinates']['value'] if 'coordinates' in parameter_value_map else '1'
        rack: paml.ContainerSpec = parameter_value_map['rack']['value']

        if rack.queryString not in LABWARE_MAP:
            raise Exception(f'Load failed. {rack.queryString} not a recognized rack type.')

        if coords in self.configuration:
            raise Exception(f'Failed to load {rack_str} in Deck {coords}. The Deck is already occupied by {self.configuration[coords]}')
        self.configuration[coords] = rack

        api_name = LABWARE_MAP[rack.queryString]
        self.script_steps += [f"labware{coords} = protocol.load_labware('{api_name}', '{coords}')"]
        rack_str = get_container_name(rack)
        self.markdown_steps += [f'Load {rack_str} in Deck {coords} of OT2 instrument']

        # If the loaded labware is a tiprack, check if any compatible pipettes
        # are currently loaded
        if 'TipRack' in rack.queryString:
            select_pipette = None
            for pipette in self.configuration.values():
                if pipette.display_id in COMPATIBLE_TIPS and api_name in COMPATIBLE_TIPS[pipette.display_id]:
                    select_pipette = pipette.display_id
                    break
            if select_pipette:
                self.script_steps += [f'{select_pipette}.tip_racks.append(labware{coords})']



    def configure_instrument(self, record: paml.ActivityNodeExecution, ex: paml.ProtocolExecution):
        call = record.call.lookup()
        parameter_value_map = call.parameter_value_map()
        instrument = parameter_value_map['instrument']['value']
        mount = parameter_value_map['mount']['value']

        allowed_mounts = ['left', 'right']
        allowed_decks = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']
        if mount not in allowed_mounts and mount not in allowed_decks:
            raise Exception("ConfigureInstrument call failed: mount must be either 'left' or 'right' or a deck number from 1-12")

        self.configuration[mount] = instrument

        if mount in allowed_mounts:
            self.markdown_steps += [f"Mount `{instrument.name}` in {mount} mount of the OT2 machine"]
            self.script_steps += [f"{instrument.display_id} = protocol.load_instrument('{instrument.display_id}', '{mount}')"]
            if instrument.display_id not in COMPATIBLE_TIPS:
                raise Exception(f"ConfigureInstrument call failed: instrument must be one of {list(COMPATIBLE_TIPS.keys())}")

        else:
            self.markdown_steps += [f"Load `{instrument.name}` in Deck {mount} of the OT2 machine"]
            instrument_id = instrument.display_id.replace('_', ' ')  # OT2 api name uses spaces instead of underscores
            self.script_steps += [f"{instrument_id} = protocol.load_module('{instrument.display_id}', '{mount}')"]


        # Check if a compatible tiprack has been loaded and configure the pipette
        # to use it
        tiprack_selection = None
        for deck, rack in self.configuration.items():
            if type(rack) is not paml.ContainerSpec:
                continue
            api_name = LABWARE_MAP[rack.queryString]
            if api_name in COMPATIBLE_TIPS[instrument.display_id]:
                tiprack_selection = rack
                break
        if tiprack_selection:
            self.script_steps += [f'{instrument.display_id}.tip_racks.append(labware{deck})']


def get_container_name(container: paml.ContainerSpec):
    if container.name:
        return f'`{container.name}`'
    try:
        prefix, local = container.queryString.split(':')
    except:
        raise Exception(f'Container specification {qname} is invalid.')
    return ContO.get_term_by_uri(f'{ContO.uri}#{local}')


def measurement_to_text(measure: sbol3.Measure):
    measurement_scalar = measure.value
    measurement_units = tyto.OM.get_term_by_uri(measure.unit)
    return f'{measurement_scalar} {measurement_units}'


def get_token_source(input_name: str, record: paml.CallBehaviorExecution) -> paml.CallBehaviorExecution:
     # Find the target flow carrying the token for the specified input pin
     input_flows = [flow.lookup() for flow in record.incoming_flows if type(flow.lookup().token_source.lookup()) is paml.ActivityNodeExecution]  # Input tokens flow between ActivityNodeExecutions and CallBehaviorExecutions
     input_flows2 = [flow.lookup() for flow in record.incoming_flows if type(flow.lookup()) is paml.ActivityEdgeFlow]
     assert input_flows != input_flows2
     upstream_execution_nodes = [flow.token_source.lookup() for flow in input_flows]
     target_node = None
     for node in upstream_execution_nodes:
         pin = node.node.lookup()
         assert type(pin) is uml.InputPin
         if pin.name == input_name:
             target_node = node
             break
     if not target_node:
         raise Exception(f'{input_name} not found')
     assert len(target_node.incoming_flows) == 1
     token_source = target_node.incoming_flows[0].lookup().token_source.lookup()
     if type(token_source.node.lookup()) is uml.ForkNode:
         # Go one more step upstream to get the source CallBehaviorExecution
         return token_source.incoming_flows[0].lookup().token_source.lookup()
     assert type(token_source) is paml.CallBehaviorExecution, f"Handler for token source of {type(token_source)} is not implemented yet"
     return token_source


def get_behavior_type(ex: paml.CallBehaviorExecution) -> str:
    # Look up the type of Primitive that a CallBehaviorExecution
    # represents.  Strips the namespace out of the Primitive's URI
    # and returns just the local name, e.g., "PlateCoordinates"
    return ex.node.lookup().behavior.split('/')[-1]
