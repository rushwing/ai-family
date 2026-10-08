# Editable Home Inventory Example

[REQ-013](../../../../harness/tasks/features/REQ-013.md) defines the contract and acceptance. [three-bedroom-apartment.example.json](three-bedroom-apartment.example.json) is a fictional specification fixture; the runtime loader/resolver will be delivered through that REQ's review and TC lifecycle. This file is not HA configuration and does not control devices.

## Customize

Copy the JSON to a private path such as `tmp/my.home-inventory.local.json` (both `tmp/` and `*.home-inventory.local.json` are Git-ignored). Change the Home's name/residence_type and the Floor's name/level to your real layout. An apartment on the sixth building floor can use `level: 6`; the example's 0 is only a suggested initial value.

Rename the three bedroom areas freely, keeping their IDs. Change `area_type` independently of `name`. To add a floor, choose a new stable ID and assign areas through `floor_id`; outdoor or unassigned areas may use null. For new areas/devices choose unique IDs; moved devices keep their IDs and change `area_id`. Add real devices locally, retaining canonical references; provider IDs and credentials belong to later private bindings, not these contracts.

Edit label registry entries and area/device label ID lists. `children` is the registered spelling. `outdoor_spaces` is the outdoor group ID; `outdoor` is a label ID. Edit group `area_types` to change the room membership rule. Changing names must never change IDs. Inventory editing guidance and validation rules are authoritative in REQ-013.

## Target Examples

The following selectors describe the future pure resolver. They do not invoke HA or perform actions:

```json
{"home_id": "home-example", "area_ids": ["area-bedroom-02"]}
```

Selects Daughter's Room and its fictional light.

```json
{"home_id": "home-example", "area_group_ids": ["resting"]}
```

Selects all three bedrooms and their fictional lights.

```json
{"home_id": "home-example", "area_group_ids": ["resting"], "label_ids": ["children"]}
```

Selects only Daughter's Room. `studio` and `storage_utility` resolve empty in this apartment; rooms in those groups can be added privately. Group selection is a union, with optional all-label filtering. Later action requirements must validate capability, identity, scope and confirmation for every selected device.

## Current Verification

`python3 -m json.tool docs/product/home-intelligence/examples/three-bedroom-apartment.example.json` checks JSON syntax only. The admission tests check the example's internal references and intended room/group membership. Runtime schema/loader/selector validation is pending REQ-013 and its required TC; no runtime validation command is claimed yet.
