# Editable Home Inventory Example

[REQ-013](../../../../harness/tasks/archive/done/features/REQ-013.md) defines the contract and acceptance. [three-bedroom-apartment.example.json](three-bedroom-apartment.example.json) is a fictional editable inventory. The offline loader/resolver is implemented; the supplied independent review passed. The JSON is not HA configuration and does not control devices.

## Customize

Copy the JSON to a private path such as `tmp/my.home-inventory.local.json` (both `tmp/` and `*.home-inventory.local.json` are Git-ignored). Change the Home's name/residence_type and the Floor's name/level to your real layout. An apartment on the sixth building floor can use `level: 6`; the example's 0 is only a suggested initial value.

Rename the three bedroom areas freely, keeping their IDs. Change `area_type` independently of `name`. To add a floor, choose a new stable ID and assign areas through `floor_id`; outdoor or unassigned areas may use null. For new areas/devices choose unique IDs; moved devices keep their IDs and change `area_id`. Add real devices locally, retaining canonical references; provider IDs and credentials belong to later private bindings, not these contracts.

Edit label registry entries and area/device label ID lists. `children` is the registered spelling. `outdoor_spaces` is the outdoor group ID; `outdoor` is a label ID. Edit group `area_types` to change the room membership rule. Changing names must never change IDs. Inventory editing guidance and validation rules are authoritative in REQ-013.

## Target Examples

Use the following selectors with the pure resolver and `home_id="home-example"`. They select canonical targets without invoking HA or performing actions:

```json
{"area_ids": ["area-bedroom-02"]}
```

Selects Daughter's Room and its fictional light.

```json
{"area_group_ids": ["resting"]}
```

Selects all three bedrooms and their fictional lights.

```json
{"area_group_ids": ["resting"], "label_ids": ["children"]}
```

Selects only Daughter's Room. `studio` and `storage_utility` resolve empty in this apartment; rooms in those groups can be added privately. Group selection is a union, with optional all-label filtering. Later action requirements must validate capability, identity, scope and confirmation for every selected device.

## Offline Validation

Install from the repository root using Python 3.12+ and validate an explicit path:

```bash
python -m pip install -e libs/state-schema
python -m state_schema.home_inventory docs/product/home-intelligence/examples/three-bedroom-apartment.example.json
```

After copying the file and editing the private inventory, validate that copy:

```bash
python -m state_schema.home_inventory tmp/my.home-inventory.local.json
```

The command reads UTF-8 JSON, prints a normalized inventory on success and leaves the file unchanged. Invalid JSON/UTF-8, unsupported versions, unknown fields, duplicate IDs/JSON fields, invalid types and dangling/cross-home references fail with the file and actionable error on stderr. It makes no network or provider calls. See [package instructions](../../../../libs/state-schema/README.md) for typed contracts and diagnostics.

Resolve the copied inventory in Python:

```python
from state_schema.home_inventory import load_inventory, resolve_targets

inventory = load_inventory("tmp/my.home-inventory.local.json")
result = resolve_targets(
    inventory,
    home_id=inventory["home"]["id"],
    selector={"area_group_ids": ["resting"], "label_ids": ["children"]},
)
print(result)
```

The resolver returns sorted, unique `area_ids` and `device_ids`. Invalid selectors fail explicitly; valid empty selections stay empty. Loading or resolving targets never executes device actions. The completed independent TC-code/feature review is recorded in Harness.

## Offline provider replacement fixture

[provider-binding-replacement.example.json](provider-binding-replacement.example.json)
contains separate fictional `before` and `after` binding collections for the
existing apartment inventory. One bedroom light changes from HA mapping data to
mock mapping data; the second binding remains equal. It contains no credentials,
live endpoints or actual household identifiers. The `before`/`after` wrapper is
a verification fixture, not the version-1 collection envelope.

Validate each collection against an unchanged inventory snapshot using the
[shared package API](../../../../libs/state-schema/README.md#providerbinding-req-014).
Do not insert bindings into the canonical inventory JSON. This compares data;
it neither switches a live provider nor implements a mock device or action.
Keep private copies in Git-ignored `*.provider-bindings.local.json` files.
REQ-014 implementation is awaiting independent combined review in PR #29.

## Canonical State timeline

[canonical-state-timeline.example.json](canonical-state-timeline.example.json)
is a fictional REQ-015 acceptance bundle: `initial_state` is a canonical State
record, `provider_ack` is separate task evidence, and `observations` contains
partial helper updates. Intent targets power false and level zero; ACK alone
leaves observations unknown. The first actual report mismatches, and the second
provides current-generation post-baseline agreement. The bundle is not itself
a State collection; wrap records in `{schema_version: 1, states: [...]}` when
validating references. No device write or provider connection is performed.

## Capability Base Review Fixture

[capability-base.example.json](capability-base.example.json) is a fictional `demo.power` descriptor catalogue for REQ-016 offline tests and installed-wheel smoke. It is not one of HI-S012's six production capability definitions and attaches to no Device/provider. It declares typed power input, accepted output and a state-converged target; output acceptance cannot create State evidence.
