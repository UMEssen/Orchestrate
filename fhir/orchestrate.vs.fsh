// ============================================================
// Value Sets
// ============================================================

ValueSet: BodyLandmarkVS
Id: body-landmark-vs
Title: "Body Landmark Value Set"
Description: "Value set containing codes for anatomical body landmarks"
* ^status = #active
* ^experimental = false
* include codes from system BodyLandmarkCS

ValueSet: BodyRegionVS
Id: body-region-vs
Title: "Body Region Value Set"
Description: "Value set containing codes for anatomical body regions"
* ^status = #active
* ^experimental = false
* include codes from system BodyRegionCS