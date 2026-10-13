"""Independent public-boundary drivers; usable unchanged against installed wheels."""

from dataclasses import replace

from home_device_fabric import Delivery, MockProvider
from home_device_fabric.conformance import ConformanceDriver
from state_schema.provider_contracts import MockConfiguration, NormalizedInput, ProviderOutcome


class Forward:
    def __init__(self, data, defect=None):
        self.delegate = MockProvider(data)
        self.configuration = MockConfiguration.from_dict(data)
        self.task = None
        self.defect = defect
        self.previous = []
        self.last_horizon = None

    def discover(self):
        result = self.delegate.discover()
        if self.defect == "identity":
            result = (replace(result[0], device_id="device-wrong"), *result[1:])
        elif self.defect == "support":
            result = (
                replace(result[0], supported_capabilities=(("home.switchable", 2),)),
                *result[1:],
            )
        return result

    def snapshot(self):
        return self.delegate.snapshot()

    def submit(self, task, *, binding, attempt_id):
        self.task = task
        return self.delegate.submit(task, binding=binding, attempt_id=attempt_id)

    def settle(self, task):
        return self.delegate.settle(task)

    @property
    def now_ms(self):
        return self.delegate.now_ms

    @property
    def dispatch_log(self):
        return self.delegate.dispatch_log

    @property
    def delivery_log(self):
        return self.delegate.delivery_log

    def advance(self, now_ms):
        if self.defect == "repeat" and now_ms == self.last_horizon:
            yield from self.previous
            return
        delivered = []
        iterator = iter(self.delegate.advance(now_ms))
        for item in iterator:
            if (
                self.defect == "mismatch"
                and item.input
                and self.task
                and self.task["request"]["arguments"].get("is_on") is True
            ):
                raw = item.input.to_dict()
                if raw["member"] == "is_on" and raw["payload"]["value"] is False:
                    raw["payload"]["value"] = True
                    item = Delivery(
                        item.time_ms,
                        NormalizedInput.from_dict(raw, configuration=self.configuration),
                        None,
                    )
            if self.defect == "ack" and item.outcome and item.outcome.result.state == "running":
                raw = item.outcome.to_dict()
                raw["result"]["state"] = "succeeded"
                raw["result"]["physical_outcome"] = "confirmed"
                item = Delivery(item.time_ms, None, ProviderOutcome.from_dict(raw))
            if self.defect == "tie" and item.outcome and item.outcome.result.state == "timed_out":
                following = next(iterator, None)
                if following and following.time_ms == item.time_ms and following.input:
                    delivered.append(following)
                    yield following
                elif following:
                    delivered.extend((item, following))
                    yield item
                    yield following
                    continue
            delivered.append(item)
            yield item
        self.previous = delivered
        self.last_horizon = now_ms


class BadPolicy(ConformanceDriver):
    def dispatch(self, task, *, binding, attempt_id, verdict):
        # Uses actual provider submissions; valid candidate scripts make replay effects observable.
        self.provider.submit(task, binding=binding, attempt_id=attempt_id)


def factory(defect=None):
    return lambda data: (BadPolicy if defect == "policy" else ConformanceDriver)(
        Forward(data, defect)
    )
