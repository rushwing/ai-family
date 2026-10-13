"""Frozen exact revision-1 expectation snapshot; changes require review (REQ-021)."""

CATALOGUE_JSON = (
    '[{"actions":{"set_on":{"completion_policy":{"kind":"state_converged","'
    'targets":{"is_on":{"field":"is_on","source":"input"}}},"description":"'
    "Declare an absolute target; completion requires eligible observed Stat"
    "e agreement, not provider ACK. No execution is implemented by this des"
    'criptor.","idempotency":"safe_repeat","input_schema":{"additionalPrope'
    'rties":false,"properties":{"is_on":{"type":"boolean"}},"required":["is'
    '_on"],"type":"object"},"output_schema":{"type":"null"},"risk":"medium"'
    ',"timeout_ms":30000,"title":"Set on state"}},"capability_id":"home.swi'
    'tchable","capability_version":1,"description":"Boolean control state: '
    "true means on and false means off; this is not device availability. Re"
    "vision 1 of the canonical household capability; availability is separa"
    'te State metadata.","events":{},"properties":{"is_on":{"description":"'
    "Boolean control state: true means on and false means off; this is not "
    'device availability.","read_only":false,"title":"On state","value_sche'
    'ma":{"type":"boolean"}}},"schema_version":1,"title":"Switchable"},{"ac'
    'tions":{"set_position":{"completion_policy":{"kind":"state_converged",'
    '"targets":{"position_percent":{"field":"position_percent","source":"in'
    'put"}}},"description":"Declare an absolute target; completion requires'
    " eligible observed State agreement, not provider ACK. No execution is "
    'implemented by this descriptor.","idempotency":"safe_repeat","input_sc'
    'hema":{"additionalProperties":false,"properties":{"position_percent":{'
    '"maximum":100,"minimum":0,"type":"integer"}},"required":["position_per'
    'cent"],"type":"object"},"output_schema":{"type":"null"},"risk":"medium'
    '","timeout_ms":120000,"title":"Set absolute opening position"}},"capab'
    'ility_id":"home.positionable","capability_version":1,"description":"Ab'
    "solute opening percent as an integer: 0 means fully closed, 100 means "
    "fully open; inclusive range 0\\u2013100 with no tolerance or rounding. "
    "Revision 1 of the canonical household capability; availability is sepa"
    'rate State metadata.","events":{},"properties":{"position_percent":{"d'
    'escription":"Absolute opening percent as an integer: 0 means fully clo'
    "sed, 100 means fully open; inclusive range 0\\u2013100 with no toleranc"
    'e or rounding.","read_only":false,"title":"Opening position","value_sc'
    'hema":{"maximum":100,"minimum":0,"type":"integer"}}},"schema_version":'
    '1,"title":"Positionable"},{"actions":{},"capability_id":"home.temperat'
    'ure_sensor","capability_version":1,"description":"Temperature in degre'
    "es Celsius; minimum -273.15 (absolute zero), with no generic upper bou"
    "nd. Known finite values only. Revision 1 of the canonical household ca"
    'pability; availability is separate State metadata.","events":{},"prope'
    'rties":{"temperature_c":{"description":"Temperature in degrees Celsius'
    "; minimum -273.15 (absolute zero), with no generic upper bound. Known "
    'finite values only.","read_only":true,"title":"Temperature","value_sch'
    'ema":{"minimum":-273.15,"type":"number"}}},"schema_version":1,"title":'
    '"TemperatureSensor"}]'
)
