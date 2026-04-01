# Bid Review Skills

## When to Use Bid Review

Use `analyze_bid_item` when the user asks about specific bid requirements:
- "Is there a bid bond?" -> analyze_bid_item(item="bid_bond")
- "What's the retainage?" -> analyze_bid_item(item="retainage")
- "What are the working hours?" -> analyze_bid_item(item="working_hours")

Use `run_full_bid_review` when the user wants all checklist items extracted:
- "Run a bid review"
- "Extract the bid checklist"
- "What do I need to know for bidding?"

## Item Key Reference

### Project Information
project_title, solicitation_number, owner, scope, bid_model

### Standard Contract Items
pre_bid, submission_format, bid_bond, payment_performance_bonds, contract_time, liquidated_damages, warranty, contractor_license, insurance, minority_dbe_goals, working_hours, subcontracting, funding, certified_payroll, retainage, safety, qualifications

### Site Conditions
site_access, site_restoration, bypass, traffic_control, disposal, water_hydrant_meter

### Cleaning
cleaning_method, cleaning_passes, cleaning_notifications

### CCTV
nassco, cctv_submittal_format

### CIPP Lining
curing_method, cure_water, cipp_warranty, cipp_notifications, contractor_qualifications, wet_out_facility, end_seals, mudding_the_ends, conditions_above_pipes, pre_liner, pipe_information, resin_type, testing, engineered_design_stamp, air_testing

### Manhole Rehabilitation
mh_information, mh_product_type, products, mh_testing, mh_warranty, thickness, compressive_strength, bond_strength, shrinkage, grout, measurement_payment, external_coating, mh_notifications, nace, mh_bypass, substitution_requirements, corrugations

## Interpreting Results

Each item result contains:
- **Value**: The extracted answer (e.g., "5% of bid amount")
- **Location**: Where it was found in the document
- **Confidence**: high / medium / low / not_found
- **Page**: Page number reference

Flag items with "not_found" confidence as needing manual review.
