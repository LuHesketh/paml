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

print('Constructing quad calibration protocol')

protocol = paml.Protocol('Multicolor_particle_calibration', name="Multicolor fluorescence per bacterial particle calibration")
protocol.description = '''
Plate readers report fluorescence values in arbitrary units that vary widely from instrument to instrument. Therefore 
absolute fluorescence values cannot be directly compared from one instrument to another. In order to compare 
fluorescence output of biological devices, it is necessary to create a standard fluorescence 
curve. This variant of the protocol uses two replicates of three colors of dye, plus beads.

Adapted from https://dx.doi.org/10.17504/protocols.io.bht7j6rn and https://dx.doi.org/10.17504/protocols.io.6zrhf56
'''
doc.add(protocol)

# provisioning containers
bead_source = paml.Container(name='Silica beads', type=tyto.NCIT.Tube_Device)
fluorescein_source = paml.Container(name='Fluorescein', type=tyto.NCIT.Tube_Device)
sulforhodamine101_source = paml.Container(name='Sulforhodamine 101', type=tyto.NCIT.Tube_Device)
cascadeblue_source = paml.Container(name='Cascade Blue', type=tyto.NCIT.Tube_Device)
# plate for split-and-measure subroutine
plate = paml.Container(name='Calibration Plate', type=tyto.NCIT.Microplate, max_coordinate='H12')
# discard
disposal = paml.Container(name='Liquid Waste Disposal', type=tyto.NCIT.Disposal)
protocol.locations = {bead_source, fluorescein_source, sulforhodamine101_source, cascadeblue_source, plate, disposal}


# Create the substances to be used for calibration
ddh2o = sbol3.Component('ddH2O', 'https://identifiers.org/pubchem.substance:24901740')
ddh2o.name = 'Water, sterile-filtered, BioReagent, suitable for cell culture'  # TODO get from PubChem via tyto
doc.add(ddh2o)

pbs = sbol3.Component('PBS', 'https://identifiers.org/pubchem.compound:24978514')
pbs.name = 'Phosphate-Buffered Saline'  # TODO: get from PubChem with tyto
doc.add(pbs)

fluorescein = sbol3.Component('Fluorescein', 'https://identifiers.org/pubchem.substance:329753341') # Sigma 30181
fluorescein.name = 'Fluorescein sodium salt, analytical standard'   # TODO: get from PubChem with tyto
doc.add(fluorescein)
sulforhodamine101 = sbol3.Component('Sulforhodamine101', 'https://identifiers.org/pubchem.substance:24899749') # Sigma S7635
sulforhodamine101.name = 'Sulforhodamine 101'
doc.add(sulforhodamine101)
cascadeblue = sbol3.Component('CascadeBlue', 'https://identifiers.org/pubchem.substance:329760049') # Sigma 65325
cascadeblue.name = 'Cascade blue, aka 8-Methoxypyrene-1,3,6-trisulfonic acid trisodium salt'
# Alternative to consider: https://www.thermofisher.com/order/catalog/product/C687#/C687
doc.add(cascadeblue)


fluorescein_solution = sbol3.Component('FluoresceinSolution', sbol3.SBO_FUNCTIONAL_ENTITY, name = '10 uM fluorescein in PBS')
fluorescein_solution.features.append(sbol3.SubComponent(pbs))
concentration = sbol3.Measure(10,tyto.OM.micromolar,types={tyto.SBO.molar_concentration_of_an_entity})
fluorescein_solution.features.append(sbol3.SubComponent(fluorescein,measures = {concentration}))
doc.add(fluorescein_solution)

sulforhodamine101_solution = sbol3.Component('Sulforhodamine101Solution', sbol3.SBO_FUNCTIONAL_ENTITY, name = '2 uM sulforhodamine 101 in PBS')
sulforhodamine101_solution.features.append(sbol3.SubComponent(pbs))
concentration = sbol3.Measure(2,tyto.OM.micromolar,types={tyto.SBO.molar_concentration_of_an_entity})
sulforhodamine101_solution.features.append(sbol3.SubComponent(sulforhodamine101,measures = {concentration}))
doc.add(sulforhodamine101_solution)

cascadeblue_solution = sbol3.Component('CascadeBlueSolution', sbol3.SBO_FUNCTIONAL_ENTITY, name = '10 uM cascade blue in ddH2O')
cascadeblue_solution.features.append(sbol3.SubComponent(ddh2o))
concentration = sbol3.Measure(10,tyto.OM.micromolar,types={tyto.SBO.molar_concentration_of_an_entity})
cascadeblue_solution.features.append(sbol3.SubComponent(cascadeblue_solution,measures = {concentration}))
doc.add(cascadeblue_solution)

microspheres = sbol3.Component('nanoparticles_950uM', {'https://identifiers.org/pubchem.compound:24261', tyto.NCIT.Nanoparticle})
microspheres.name = 'NanoCym 950uM monodisperse silica nanoparticles'
doc.add(microspheres)

microsphere_solution = sbol3.Component('MicrosphereSolution', sbol3.SBO_FUNCTIONAL_ENTITY, name = '3e9 microspheres/mL ddH2O')
volume = sbol3.Measure(1,tyto.OM.milliliter,types={tyto.SBO.volume})
microsphere_solution.features.append(sbol3.SubComponent(ddh2o,measures={volume}))
count = sbol3.Measure(3e9,tyto.OM.number,types={tyto.SBO.number_of_entity_pool_constituents})
microsphere_solution.features.append(sbol3.SubComponent(microspheres,measures={count}))
doc.add(microsphere_solution)

protocol.material = {ddh2o, pbs, fluorescein_solution, sulforhodamine101_solution, cascadeblue_solution, microsphere_solution}

## Provision the four materials
# Particles and fluorescein start in tubes
p_fs = protocol.execute_primitive('Provision', resource=fluorescein_solution, destination=fluorescein_source,
                                   amount=sbol3.Measure(1, tyto.OM.milliliter))
protocol.add_flow(protocol.initial(), p_fs) # start with provisioning
p_rs = protocol.execute_primitive('Provision', resource=sulforhodamine101_solution, destination=sulforhodamine101_source,
                                   amount=sbol3.Measure(1, tyto.OM.milliliter))
protocol.add_flow(protocol.initial(), p_rs) # start with provisioning
p_bs = protocol.execute_primitive('Provision', resource=cascadeblue_solution, destination=cascadeblue_source,
                                   amount=sbol3.Measure(1, tyto.OM.milliliter))
protocol.add_flow(protocol.initial(), p_bs) # start with provisioning
p_ms = protocol.execute_primitive('Provision', resource=microsphere_solution, destination=bead_source,
                                   amount=sbol3.Measure(1, tyto.OM.milliliter))
protocol.add_flow(protocol.initial(), p_ms) # start with provisioning
protocol.add_flow(p_fs, p_rs) # manually add order
protocol.add_flow(p_rs, p_bs) # manually add order
protocol.add_flow(p_bs, p_ms) # manually add order

# Put the others into the plate
location = paml.ContainerCoordinates(in_container=plate, coordinates='A2:D12')
protocol.locations.append(location) # TODO: This seems like a potential anti-pattern
p_pbs = protocol.execute_primitive('Provision', resource=pbs, destination=location,
                                   amount=sbol3.Measure(100, tyto.OM.microliter))
protocol.add_flow(protocol.initial(), p_pbs) # start with provisioning for fluorescein and sulforhodamine 101
location = paml.ContainerCoordinates(in_container=plate, coordinates='E2:H12')
protocol.locations.append(location) # TODO: This seems like a potential anti-pattern
p_dd = protocol.execute_primitive('Provision', resource=ddh2o, destination=location,
                                   amount=sbol3.Measure(100, tyto.OM.microliter))
protocol.add_flow(protocol.initial(), p_dd) # start with provisioning for csacade blue and beads
protocol.add_flow(p_pbs, p_dd) # manually add order

ready_to_measure = paml.Join()
protocol.activities.append(ready_to_measure)

## Do the fluorescent dyes first, since they will settle less
sequence = [['A','B',p_fs],['C','D',p_rs],['E','F',p_bs]]
last = None
for vars in sequence:
    location = paml.ContainerCoordinates(in_container=plate, coordinates=vars[0]+'1:'+vars[1]+'1')
    protocol.locations.append(location) # TODO: This seems like a potential anti-pattern
    # Dispense initial fluorescein
    p_f1 = protocol.execute_primitive('Dispense', source=vars[2].output_pin('samples'), destination=location,
                                       amount=sbol3.Measure(200, tyto.OM.microliter))
    if last:
        protocol.add_flow(last, p_f1) # manually add order
    # Serial dilution across columns 2-11
    last = p_f1
    for c in range(2, 12):
        location = paml.ContainerCoordinates(in_container=plate, coordinates=vars[0]+str(c)+':'+vars[1]+str(c))
        protocol.locations.append(location)  # TODO: This seems like a potential anti-pattern
        p_fi = protocol.execute_primitive('TransferInto', source=last.output_pin('samples'),
                                          destination=location,
                                          amount=sbol3.Measure(100, tyto.OM.microliter),
                                          mixCycles=sbol3.Measure(3, tyto.OM.number))
        last = p_fi
    # Discard half of last well
    p_fdiscard = protocol.execute_primitive('Transfer', source=last.output_pin('samples'), destination=disposal,
                                            amount=sbol3.Measure(100, tyto.OM.microliter))
    last = p_fdiscard
    # After the last step, ready to measure
    protocol.add_flow(p_fdiscard, ready_to_measure)


## Next, do the beads
location = paml.ContainerCoordinates(in_container=plate, coordinates='G1:H1')
protocol.locations.append(location) # TODO: This seems like a potential anti-pattern
# Dispense initial fluorescein
p_p1 = protocol.execute_primitive('Dispense', source=p_ms.output_pin('samples'), destination=location,
                                   amount=sbol3.Measure(200, tyto.OM.microliter))
# Make sure beads don't start until the fluorescein is done
protocol.add_flow(p_fdiscard, p_p1)
# Serial dilution across columns 2-11
last = p_p1
for c in range(2, 12):
    location = paml.ContainerCoordinates(in_container=plate, coordinates='G'+str(c)+':H'+str(c))
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


# Finally, measure the four batches
location = paml.ContainerCoordinates(in_container=plate, coordinates='A1:B12')
protocol.locations.append(location) # TODO: This seems like a potential anti-pattern
p_f = protocol.execute_primitive('MeasureFluorescence', location=location,
                                 excitationWavelength=sbol3.Measure(488, tyto.OM.nanometer),
                                 emissionBandpassWavelength=sbol3.Measure(530, tyto.OM.nanometer))
protocol.add_flow(ready_to_measure, p_f)

location = paml.ContainerCoordinates(in_container=plate, coordinates='C1:D12')
protocol.locations.append(location) # TODO: This seems like a potential anti-pattern
p_r = protocol.execute_primitive('MeasureFluorescence', location=location,
                                 excitationWavelength=sbol3.Measure(561, tyto.OM.nanometer),
                                 emissionBandpassWavelength=sbol3.Measure(610, tyto.OM.nanometer))
protocol.add_flow(ready_to_measure, p_r)

location = paml.ContainerCoordinates(in_container=plate, coordinates='E1:F12')
protocol.locations.append(location) # TODO: This seems like a potential anti-pattern
p_b = protocol.execute_primitive('MeasureFluorescence', location=location,
                                 excitationWavelength=sbol3.Measure(405, tyto.OM.nanometer),
                                 emissionBandpassWavelength=sbol3.Measure(450, tyto.OM.nanometer))
protocol.add_flow(ready_to_measure, p_b)

location = paml.ContainerCoordinates(in_container=plate, coordinates='G1:H12')
protocol.locations.append(location) # TODO: This seems like a potential anti-pattern
p_a = protocol.execute_primitive('MeasureAbsorbance', location=location,
                                          wavelength=sbol3.Measure(600, tyto.OM.nanometer))
protocol.add_flow(ready_to_measure, p_a)

protocol.add_flow(p_f, p_r) # manually add order
protocol.add_flow(p_r, p_b) # manually add order
protocol.add_flow(p_b, p_a) # manually add order


result = protocol.add_output('absorbance', p_a.output_pin('measurements'))
protocol.add_flow(result, protocol.final())
result = protocol.add_output('green_fluorescence', p_f.output_pin('measurements'))
protocol.add_flow(result, protocol.final())
result = protocol.add_output('red_fluorescence', p_r.output_pin('measurements'))
protocol.add_flow(result, protocol.final())
result = protocol.add_output('blue_fluorescence', p_b.output_pin('measurements'))
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

doc.write('igem_quad_calibration_protocol.json',sbol3.JSONLD)
doc.write('igem_quad_calibration_protocol.ttl',sbol3.TURTLE)
doc.write('igem_quad_calibration_protocol.nt',sbol3.SORTED_NTRIPLES)

print('Complete')
