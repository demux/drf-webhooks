# Django Rest Framework - Webhooks
**Configurable webhooks based on DRF Serializers**

## Goals:
- [x] Use existing DRF Serializers from REST API to serialize data in webhooks
    - [x] Consistent data formatting
    - [x] Reusable OpenAPI schemas
- [x] Configurable webhooks that simply work *(by way of django signals magic)* without the developer having to keep track of where to trigger them
    - [x] Still allow for "manual" triggering of webhooks
        - This is useful because signals aren't always triggered.
        - For example: `QuerySet.update` does not trigger signals
- [x] Disable webhooks using context managers
    - This can be useful when syncing large chunks of data
    - or with a duplex sync (when two systems sync with each other) to avoid endless loops
- [x] **Webhook Signal Session**
    - [x] A context manager gathers all models signals and at the end of the session only triggers the resulting webhooks
        - [x] If a model instance is both `created` and `deleted` within the session, then no webhook is sent for that model instance
        - [x] If a model instance is `created` and then also `updated` within the session, then a `created` event is sent with the data from the last `updated` signal. Only one webhook even is sent
        - [x] If a models instance is `updated` multiple times within the session, then only one webhook event is sent.
    - [x] Middleware wraps each request in **Webhook Signal Session** context
        - **NOTE:** The developer will have to call the context manager in code that runs outside of requests (for example in celery tasks) manually
- [ ] Automatically determine which nested models need to be monitored for changes. Currently this must be done by setting `signal_model_instance_base_getters`


## Example:

```python
from auth.models import User
from core.models import Address, Landlord, RentalUnit, Tenant
from drf_webhooks.utils import ModelSerializerWebhook


class DepositSerializerWebhook(ModelSerializerWebhook):
    serializer_class = DepositSerializer
    base_name = 'core.deposit'

    @staticmethod
    def get_address_instance_base(address):
        tenants = address.tenant_set.all()
        for tenant in tenants:
            yield from tenant.deposits.all()

        unit = getattr(address, "unit", None)
        if unit:
            yield from address.unit.deposits.all()

    # Monitor changes to data in nested serializers:
    signal_model_instance_base_getters = {
        Tenant: lambda x: x.deposits.all(),
        User: lambda x: x.tenant.deposits.all(),
        RentalUnit: lambda x: x.deposits.all(),
        Address: get_address_instance_base,
        Landlord: lambda x: [],  # Not important for this hook
    }

...

class DepositSerializer(serializers.ModelSerializer):
    tenant = TenantSerializer(read_only=True)
    landlord = LandlordSerializer(read_only=True)
    unit = RentalUnitSerializer(read_only=True)

    class Meta:
        model = Deposit
        fields = [
            'id',
            'created',
            'tenant',
            'landlord',
            'unit',
            'date_from',
            'date_to',
            'security_deposit_amount',
            'last_months_rent_amount',
            'fee_rate',
            'fee_amount',
            'status',
            'initiator',
        ]

...
```
