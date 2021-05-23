import sbol3
import paml
import paml_md
import paml.type_inference
from paml.lib.library_type_inference import primitive_type_inference_functions
from paml_md.markdown_primitives import primitive_to_markdown_functions
import time
import filecmp
from importlib import reload # for reloading modules
# reload('paml')

## Add inference and markdown for experimental primitive
def subset_infer_typing(executable, typing: paml.type_inference.ProtocolTyping):
    samples = executable.input_pin('samples').input_type(typing)
    location = executable.input_pin('location').input_type(typing)
    # TODO: this is an evil kludge and should be replaced with actual subsetting
    subset = paml.ReplicateSamples(specification=samples.specification)
    subset.in_location.append(location)
    typing.kludge_parent.locations.append(subset)
    executable.output_pin('subset').assert_output_type(typing, subset)
primitive_type_inference_functions['https://igem.org/Engineering/protocols/SampleSubset'] = subset_infer_typing


def subset_markdown(executable, mdc: paml_md.MarkdownConverter):
    return '' # Nothing needs to be explicitly written for a subset operation; it's just there for inference
primitive_to_markdown_functions['https://igem.org/Engineering/protocols/SampleSubset'] = subset_markdown


doc = sbol3.Document()
sbol3.set_namespace('https://igem.org/Engineering/protocols/') # TODO: kludge: shouldn't need this, but markdown conversion does during its type inference

#doc.read('test/testfiles/igem_ludox_draft.nt', 'nt')
#paml_md.MarkdownConverter(doc).convert('iGEM_LUDOX_OD_calibration_2018')
#filecmp.cmp('iGEM_LUDOX_OD_calibration_2018.md', 'test/testfiles/iGEM_LUDOX_OD_calibration_2018.md')

print('Loading file')
start = time.time()
doc.read('igem_dual_calibration_protocol.nt', sbol3.SORTED_NTRIPLES)
end = time.time()
print('Loading took '+str(round(end - start))+' seconds')

mdc = paml_md.MarkdownConverter(doc)

mdc.convert('MEFL_particle_calibration')
