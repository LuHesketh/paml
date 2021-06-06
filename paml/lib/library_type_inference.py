import sbol3
import paml
import paml.type_inference


# Pre-declare the ProtocolTyping class to avoid circularity with paml.type_inference
class ProtocolTyping:
    pass

primitive_type_inference_functions = {}  # dictionary of identity : function for typing primitives


# When there is no output, we don't need to do any inference
def no_output_primitive_infer_typing(_, __: ProtocolTyping):
    pass


#############################################
# Liquid handling primitives

LIQUID_HANDLING_PREFIX = 'https://bioprotocols.org/paml/primitives/liquid_handling/'

# TODO: add amount information into sample records


def liquid_handling_provision_infer_typing(executable, typing: ProtocolTyping):
    resource = executable.input_pin('resource').input_type(typing)
    location = executable.input_pin('destination').input_type(typing)
    samples = paml.ReplicateSamples(specification=resource)
    samples.in_location.append(location)
    typing.kludge_parent.locations.append(samples)
    executable.output_pin('samples').assert_output_type(typing, samples)
primitive_type_inference_functions[LIQUID_HANDLING_PREFIX+'Provision'] = liquid_handling_provision_infer_typing


def liquid_handling_dispense_infer_typing(executable, typing: ProtocolTyping):
    source = executable.input_pin('source').input_type(typing)  # Assumed singular replicate
    assert isinstance(source, paml.ReplicateSamples), ValueError('Dispense must come from a homogeneous source, but found '+str(source))
    location = executable.input_pin('destination').input_type(typing)
    samples = paml.ReplicateSamples(specification=source.specification) # TODO: Fix the kludge here
    samples.in_location.append(location)
    typing.kludge_parent.locations.append(samples)
    executable.output_pin('samples').assert_output_type(typing, samples)
primitive_type_inference_functions[LIQUID_HANDLING_PREFIX+'Dispense'] = liquid_handling_dispense_infer_typing


def liquid_handling_transfer_infer_typing(executable, typing: ProtocolTyping):
    source = executable.input_pin('source').input_type(typing)
    destination = executable.input_pin('destination').input_type(typing)
    if isinstance(source, paml.ReplicateSamples):
        relocated = paml.ReplicateSamples(specification=source.specification)
        relocated.in_location.append(destination)
    elif isinstance(source, paml.LocatedSamples):
        relocated = paml.HeterogeneousSamples()
        kludge = paml.ReplicateSamples() # TODO: put something real here instead
        kludge.in_location.append(destination)
        relocated.replicate_samples.append(kludge)
    else:
        raise ValueError("Don't know how to infer type for Transfer with source of type "+str(type(source)))
    typing.kludge_parent.locations.append(relocated)
    executable.output_pin('samples').assert_output_type(typing, relocated)
primitive_type_inference_functions[LIQUID_HANDLING_PREFIX + 'Transfer'] = liquid_handling_transfer_infer_typing


def liquid_handling_transferinto_infer_typing(executable, typing: ProtocolTyping):
    source = executable.input_pin('source').input_type(typing)
    destination = executable.input_pin('destination').input_type(typing) # Location
    print('Inferring on source: '+str(source.identity)+' destination: '+str(destination.identity))
    if isinstance(source, paml.ReplicateSamples):
        contents = sbol3.Component(executable.display_id+'_contents', sbol3.SBO_FUNCTIONAL_ENTITY)  # generic mixture
        mixture = paml.ReplicateSamples(specification=contents)
        mixture.in_location.append(destination)
    elif isinstance(source, paml.LocatedSamples):
        mixture = paml.HeterogeneousSamples()
        kludge = paml.ReplicateSamples() # TODO: put something real here instead
        kludge.in_location.append(destination)
        mixture.replicate_samples.append(kludge)
    else:
        raise ValueError("Don't know how to infer type for TransferInto "+executable.identity+" with source and destination types "+str(type(source))+', '+str(type(destination)))
    typing.kludge_parent.locations.append(mixture)
    executable.output_pin('samples').assert_output_type(typing, mixture)
primitive_type_inference_functions[LIQUID_HANDLING_PREFIX + 'TransferInto'] = liquid_handling_transferinto_infer_typing


primitive_type_inference_functions[LIQUID_HANDLING_PREFIX+'PipetteMix'] = no_output_primitive_infer_typing

#############################################
# Plate handling primitives

PLATE_HANDLING_PREFIX = 'https://bioprotocols.org/paml/primitives/plate_handling/'


primitive_type_inference_functions[PLATE_HANDLING_PREFIX+'Cover'] = no_output_primitive_infer_typing
primitive_type_inference_functions[PLATE_HANDLING_PREFIX+'Seal'] = no_output_primitive_infer_typing
primitive_type_inference_functions[PLATE_HANDLING_PREFIX+'AdhesiveSeal'] = no_output_primitive_infer_typing
primitive_type_inference_functions[PLATE_HANDLING_PREFIX+'ThermalSeal'] = no_output_primitive_infer_typing
primitive_type_inference_functions[PLATE_HANDLING_PREFIX+'Uncover'] = no_output_primitive_infer_typing
primitive_type_inference_functions[PLATE_HANDLING_PREFIX+'Unseal'] = no_output_primitive_infer_typing
primitive_type_inference_functions[PLATE_HANDLING_PREFIX+'Incubate'] = no_output_primitive_infer_typing


#############################################
# Spectrophotometry primitives

SPECTROPHOTOMETRY = 'https://bioprotocols.org/paml/primitives/spectrophotometry/'

def find_or_make_unknown(typing):
    exists = typing.kludge_parent.document.find('Unknown')
    if exists:
        return exists
    else:
        unknown = sbol3.Component('http://kludge.org/Unknown', sbol3.SBO_FUNCTIONAL_ENTITY)
        typing.kludge_parent.document.add(unknown)
        return unknown

def spectrophotometry_infer_typing(executable, typing: ProtocolTyping):
    location = executable.input_pin('location').input_type(typing) # KLUDGE KLUDGE
    # TODO: figure out how to add appropriate metadata onto these
    samples = paml.ReplicateSamples(specification=find_or_make_unknown(typing))
    samples.in_location.append(location)
    data = paml.LocatedData()
    data.from_samples = samples
    executable.output_pin('measurements').assert_output_type(typing, data)
primitive_type_inference_functions[SPECTROPHOTOMETRY+'MeasureAbsorbance'] = spectrophotometry_infer_typing
primitive_type_inference_functions[SPECTROPHOTOMETRY+'MeasureFluorescence'] = spectrophotometry_infer_typing
primitive_type_inference_functions[SPECTROPHOTOMETRY+'MeasureFluorescenceSpectrum'] = spectrophotometry_infer_typing
