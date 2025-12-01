Profile: OrchestrateObservation
Parent: Observation
Id: orchestrate-observation
Title: "Orchestrate Outputs"
Description: """This is the Profile to standardize the Orchestrate Outputs"""
* ^version = "0.0.1"

* status MS
* status.value = #final

* code MS
* code 1..1

* subject 1..1
* subject only Reference(Patient)
* derivedFrom only Reference(ImagingStudy)
* partOf only Reference(Procedure)


* component ^slicing.discriminator.type = #value
* component ^slicing.discriminator.path = "code"
* component ^slicing.rules = #open
* component 1..*
* component contains
    studyUID 1..1 and
    seriesUID 1..1 and
    instanceUID 0..1 and
    sliceThickness 1..1 and
    reconstructionKernel 0..1 and
    bodycontrastPhase 0..1 and
    braincontrastPhase 0..1 and
    bodyLandmark 1..* and
    bodyRegion 1..*


* component[studyUID].code.text = "Study Instance UID"
* component[studyUID].value[x] only string

* component[seriesUID].code.text = "Series Instance UID"
* component[seriesUID].value[x] only string

* component[sliceThickness].code.text = "Slice Thickness"
* component[sliceThickness].value[x] only Quantity
* component[sliceThickness].valueQuantity.unit = "mm"

* component[reconstructionKernel].code.text = "Reconstruction Kernel"
* component[reconstructionKernel].value[x] only string


* component[bodycontrastPhase].code.text = "Body Contrast Phase"
* component[bodycontrastPhase].value[x] only string

* component[braincontrastPhase].code.text = "Brain Contrast Phase"
* component[braincontrastPhase].value[x] only string

* component[bodyLandmark].code from BodyLandmarkVS (required)
* component[bodyLandmark].value[x] only Quantity
* component[bodyLandmark].valueQuantity.unit = "%"

* component[bodyRegion].code from BodyRegionVS (required)
* component[bodyRegion].value[x] only Quantity
* component[bodyRegion].valueQuantity.unit = "%"
