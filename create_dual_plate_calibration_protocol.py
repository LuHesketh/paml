import sbol3
import paml
import tyto

#############################################
# Helper functions

# set up the document
doc = sbol3.Document()
sbol3.set_namespace('https://igem.org/Engineering/protocols/')

#############################################
# Import the primitive libraries
print('Importing libraries')
paml.import_library('liquid_handling')
paml.import_library('plate_handling')
paml.import_library('spectrophotometry')

# this should really get pulled into a common library somewhere
rpm = sbol3.UnitDivision('rpm',name='rpm', symbol='rpm',label='revolutions per minute',numerator=tyto.OM.revolution,denominator=tyto.OM.minute)
doc.add(rpm)


#############################################
# Create the protocols

print('Constructing dual calibration protocol')

protocol = paml.Protocol('MEFL_particle_calibration', name="Fluorescein per bacterial particle calibration")
protocol.description = '''
Plate readers report fluorescence values in arbitrary units that vary widely from instrument to instrument. Therefore 
absolute fluorescence values cannot be directly compared from one instrument to another. In order to compare 
fluorescence output of test devices between teams, it is necessary for each team to create a standard fluorescence 
curve. Although distribution of a known concentration of GFP protein would be an ideal way to standardize the amount of 
GFP fluorescence in our ​E. coli​ cells, the stability of the protein and the high cost of its purification are 
problematic. We therefore use the small molecule fluorescein, which has similar excitation and emission properties to 
GFP, but is cost-effective and easy to prepare. (The version of GFP used in the devices, GFP mut3b, has an excitation 
maximum at 501 nm and an emission maximum at 511 nm; fluorescein has an excitation maximum at 494 nm and an emission 
maximum at 525nm).

You will prepare a dilution series of fluorescein in four replicates and measure the fluorescence in a 96 well plate in 
your plate reader. By measuring these in your plate reader, you will generate a standard curve of fluorescence for 
fluorescein concentration. You will be able to use this to convert your cell based readings to an equivalent 
fluorescein concentration. Before beginning this protocol, ensure that you are familiar with the GFP settings and 
measurement modes of your instrument. You will need to know what filters your instrument has for measuring GFP, 
including information about the bandpass width (530 nm / 30 nm bandpass, 25-30 nm width is recommended), excitation 
(485 nm is recommended) and emission (520-530 nm is recommended) of this filter.

To convert OD measurements to particle measurements, you will prepare a dilution series of ​monodisperse silica 
microspheres and measure the ​Abs​600 in your plate reader. The size and optical characteristics of these microspheres 
are similar to cells, and there is a known amount of particles per volume. This measurement will allow you to construct 
a standard curve of particle concentration which can be used to convert 600 nm absorbance measurements into an 
estimated equivalent number of cells.

Adapted from https://dx.doi.org/10.17504/protocols.io.bht7j6rn and https://dx.doi.org/10.17504/protocols.io.6zrhf56
'''
doc.add(protocol)

# provisioning containers
bead_source = paml.Container(name='Silica beads', type=tyto.NCIT.Tube_Device)
fluorescein_source = paml.Container(name='Fluorescein', type=tyto.NCIT.Tube_Device)
# plate for split-and-measure subroutine
plate = paml.Container(name='Calibration Plate', type=tyto.NCIT.Microplate, max_coordinate='H12')
# discard
disposal = paml.Container(name='Liquid Waste Disposal', type=tyto.NCIT.Disposal)
protocol.locations = {bead_source, fluorescein_source, plate, disposal}


# Create the substances to be used for calibration
ddh2o = sbol3.Component('ddH2O', 'https://identifiers.org/pubchem.substance:24901740')
ddh2o.name = 'Water, sterile-filtered, BioReagent, suitable for cell culture'  # TODO get from PubChem via tyto
doc.add(ddh2o)

pbs = sbol3.Component('PBS', 'https://identifiers.org/pubchem.compound:24978514')
pbs.name = 'Phosphate-Buffered Saline'  # TODO: get from PubChem with tyto
doc.add(pbs)

fluorescein = sbol3.Component('Fluorescein', 'https://identifiers.org/pubchem.substance:329757279')
fluorescein.name = 'Fluorescein sodium salt, p.a., for source staining'   # TODO: get from PubChem with tyto
doc.add(fluorescein)

fluorescein_solution = sbol3.Component('FluoresceinSolution', sbol3.SBO_FUNCTIONAL_ENTITY, name = '10 uM fluorescein')
fluorescein_solution.features.append(sbol3.SubComponent(pbs))
concentration = sbol3.Measure(10,tyto.OM.micromolar,types={tyto.SBO.molar_concentration_of_an_entity})
fluorescein_solution.features.append(sbol3.SubComponent(fluorescein,measures = {concentration}))
doc.add(fluorescein_solution)

microspheres = sbol3.Component('nanoparticles_950uM', {'https://identifiers.org/pubchem.compound:24261', tyto.NCIT.Nanoparticle})
microspheres.name = 'NanoCym 950uM monodisperse silica nanoparticles'
doc.add(microspheres)

microsphere_solution = sbol3.Component('MicrosphereSolution', sbol3.SBO_FUNCTIONAL_ENTITY, name = '3e9 microspheres/mL')
volume = sbol3.Measure(1,tyto.OM.milliliter,types={tyto.SBO.volume})
microsphere_solution.features.append(sbol3.SubComponent(ddh2o,measures={volume}))
count = sbol3.Measure(3e9,tyto.OM.number,types={tyto.SBO.number_of_entity_pool_constituents})
microsphere_solution.features.append(sbol3.SubComponent(microspheres,measures={count}))
doc.add(microsphere_solution)

protocol.material = {ddh2o, pbs, fluorescein_solution, microsphere_solution}

## Provision the four materials
# Particles and fluorescein start in tubes
p_ms = protocol.execute_primitive('Provision', resource=microsphere_solution, destination=bead_source,
                                   amount=sbol3.Measure(1, tyto.OM.milliliter))
protocol.add_flow(protocol.initial(), p_ms) # start with provisioning
p_fs = protocol.execute_primitive('Provision', resource=fluorescein_solution, destination=fluorescein_source,
                                   amount=sbol3.Measure(1, tyto.OM.milliliter))
protocol.add_flow(protocol.initial(), p_fs) # start with provisioning

# Put the others into the plate
location = paml.ContainerCoordinates(in_container=plate, coordinates='A2:D12')
protocol.locations.append(location) # TODO: This seems like a potential anti-pattern
p_pbs = protocol.execute_primitive('Provision', resource=pbs, destination=location,
                                   amount=sbol3.Measure(100, tyto.OM.microliter))
protocol.add_flow(protocol.initial(), p_pbs) # start with provisioning
location = paml.ContainerCoordinates(in_container=plate, coordinates='E2:H12')
protocol.locations.append(location) # TODO: This seems like a potential anti-pattern
p_dd = protocol.execute_primitive('Provision', resource=ddh2o, destination=location,
                                   amount=sbol3.Measure(100, tyto.OM.microliter))
protocol.add_flow(protocol.initial(), p_dd) # start with provisioning

ready_to_measure = paml.Join()
protocol.activities.append(ready_to_measure)

## Do the fluorescein first, since it will settle less
location = paml.ContainerCoordinates(in_container=plate, coordinates='A1:D1')
protocol.locations.append(location) # TODO: This seems like a potential anti-pattern
# Dispense initial fluorescein
p_f1 = protocol.execute_primitive('Dispense', source=p_fs.output_pin('samples'), destination=location,
                                   amount=sbol3.Measure(200, tyto.OM.microliter))
# Serial dilution across columns 2-11
last = p_f1
for c in range(2, 12):
    location = paml.ContainerCoordinates(in_container=plate, coordinates='A'+str(c)+':D'+str(c))
    protocol.locations.append(location)  # TODO: This seems like a potential anti-pattern
    p_fi = protocol.execute_primitive('TransferInto', source=last.output_pin('samples'),
                                      destination=location,
                                      amount=sbol3.Measure(100, tyto.OM.microliter),
                                      mixCycles=sbol3.Measure(3, tyto.OM.number))
    last = p_fi
# Discard half of last well
p_fdiscard = protocol.execute_primitive('Transfer', source=last.output_pin('samples'), destination=disposal,
                                        amount=sbol3.Measure(100, tyto.OM.microliter))
# After the last step, ready to measure
protocol.add_flow(p_fdiscard, ready_to_measure)


## Next, do the beads
location = paml.ContainerCoordinates(in_container=plate, coordinates='E1:H1')
protocol.locations.append(location) # TODO: This seems like a potential anti-pattern
# Dispense initial fluorescein
p_p1 = protocol.execute_primitive('Dispense', source=p_ms.output_pin('samples'), destination=location,
                                   amount=sbol3.Measure(200, tyto.OM.microliter))
# Make sure beads don't start until the fluorescein is done
protocol.add_flow(p_fdiscard, p_p1)
# Serial dilution across columns 2-11
last = p_p1
for c in range(2, 12):
    location = paml.ContainerCoordinates(in_container=plate, coordinates='E'+str(c)+':H'+str(c))
    protocol.locations.append(location)  # TODO: This seems like a potential anti-pattern
    p_pi = protocol.execute_primitive('TransferInto', source=last.output_pin('samples'),
                                      destination=location,
                                      amount=sbol3.Measure(100, tyto.OM.microliter),
                                      mixCycles=sbol3.Measure(3, tyto.OM.number))
    last = p_pi
# Discard half of last well
p_pdiscard = protocol.execute_primitive('Transfer', source=last.output_pin('samples'), destination=disposal,
                                          amount=sbol3.Measure(100, tyto.OM.microliter))
# After the last step, ready to measure
protocol.add_flow(p_pdiscard, ready_to_measure)


# Finally, measure the two batches
location = paml.ContainerCoordinates(in_container=plate, coordinates='A1:D12')
protocol.locations.append(location) # TODO: This seems like a potential anti-pattern
p_f = protocol.execute_primitive('MeasureFluorescence', location=location,
                                 excitationWavelength=sbol3.Measure(488, tyto.OM.nanometer),
                                 emissionBandpassWavelength=sbol3.Measure(530, tyto.OM.nanometer))
protocol.add_flow(ready_to_measure, p_f)
location = paml.ContainerCoordinates(in_container=plate, coordinates='E1:H12')
protocol.locations.append(location) # TODO: This seems like a potential anti-pattern
p_a = protocol.execute_primitive('MeasureAbsorbance', location=location,
                                          wavelength=sbol3.Measure(600, tyto.OM.nanometer))
protocol.add_flow(ready_to_measure, p_a)
result = protocol.add_output('absorbance', p_a.output_pin('measurements'))
protocol.add_flow(result, protocol.final())
result = protocol.add_output('fluorescence', p_f.output_pin('measurements'))
protocol.add_flow(result, protocol.final())

print('Protocol construction complete')


######################
# Invocation of protocol on a plate:;

# plate for invoking the protocol
#input_plate = paml.Container(name='497943_4_UWBF_to_stratoes', type=tyto.NCIT.Microplate, max_coordinate='H12')


print('Validating document')
for e in doc.validate().errors: print(e);
for w in doc.validate().warnings: print(w);

print('Writing document')

doc.write('igem_dual_calibration_protocol.json',sbol3.JSONLD)
doc.write('igem_dual_calibration_protocol.ttl',sbol3.TURTLE)
doc.write('igem_dual_calibration_protocol.nt',sbol3.SORTED_NTRIPLES)

print('Complete')
