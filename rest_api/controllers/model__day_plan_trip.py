# -*- coding: utf-8 -*-
from .main import *

_logger = logging.getLogger(__name__)


# List of REST resources in current file:
#   (url prefix)               (method)     (action)
# /api/day.plan.trip                GET     - Read all (with optional filters, offset, limit, order, exclude_fields, include_fields)
# /api/day.plan.trip/<id>           GET     - Read one (with optional exclude_fields, include_fields)
# /api/day.plan.trip                POST    - Create one
# /api/day.plan.trip/<id>           PUT     - Update one
# /api/day.plan.trip/<id>           DELETE  - Delete one
# /api/day.plan.trip/<id>/<method>  PUT     - Call method (with optional parameters)


# List of IN/OUT data (json data and HTTP-headers) for each REST resource:

# /api/day.plan.trip  GET  - Read all (with optional filters, offset, limit, order, exclude_fields, include_fields)
# IN data:
#   HEADERS:
#       'access_token'
#   JSON:
#       (optional filters (Odoo domain), offset, limit, order, exclude_fields, include_fields)
#           {                                       # editable
#               "filters": [('some_field_1', '=', some_value_1), ('some_field_2', '!=', some_value_2), ...],
#               "offset":  XXX,
#               "limit":   XXX,
#               "order":   "list_of_fields",  # default 'name asc'
#               "exclude_fields": ["some_field_1", "some_field_2", ...],
#                                   # "*" or "__all_fields__" - excludes all fields from schema
#               "include_fields": ["some_field_1", "some_field_2", ...]
#           }
# OUT data:
OUT__day_plan_trip__read_all__SUCCESS_CODE = 200       # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#   JSON:
#       {
#           "count":   XXX,     # number of returned records
#           "results": [
OUT__day_plan_trip__read_all__SCHEMA = (                 # editable
    'id',
    'code',
    'name',
    'state',
    'from_datetime',
    'to_datetime',
    'duration',
    'advance_allowed',
    ('company_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('branch_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('vehicle_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('create_uid', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    'fuel_type',
    'odometer',
    'odometer_unit',
    ('driver_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('spare1_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('spare2_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('expense_ids', [(
        'id',
        ('company_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        ('product_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'name',
        'amount',
        'attached_file',
    )]),
    ('consumption_ids', [(
        'id',
        'is_required',
        'last_odometer',
        'current_odometer',
        'trip_distance',
        'standard_liter',
        'consumed_liter',
        'avg_calculation',
        'description',
        'date',
    )]),
    ('fuelin_ids', [(
        'id',
        ('company_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'date',
        'shop',
        ('product_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        ('location_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'slip_no',
        'liter',
        'price_unit',
        'amount',
        'add_from_office',
    )]),
    ('request_allowance_lines', [(
        'id',
        ('expense_categ_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'quantity',
        'amount',
        'total_amount',
        'remark'
    )]),
    ('product_lines', [(
        'id',
        ('company_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        ('product_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        ('product_uom', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'quantity',
    )]),
    'total_advance',
    'destination',
    'unit_expense',
    'tyre_points',
    'engine_oil_points',
)
#           ]
#       }

# /api/day.plan.trip/<id>  GET  - Read one (with optional exclude_fields, include_fields)
# IN data:
#   HEADERS:
#       'access_token'
#   JSON:
#       (optional search_field, exclude_fields, include_fields)
#           {                                       # editable
#               "search_field": "some_field_name" # for searching object not by 'id' field
#               "exclude_fields": ["some_field_1", "some_field_2", ...],
#                                   # "*" or "__all_fields__" - excludes all fields from schema
#               "include_fields": ["some_field_1", "some_field_2", ...]
#           }
# OUT data:
OUT__day_plan_trip__read_one__SUCCESS_CODE = 200       # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       404 'not_found_object_in_odoo'
OUT__day_plan_trip__read_one__SCHEMA = (                 # editable
    # (The order of fields of different types can be arbitrary)
    # simple fields (non relational):
    'id',
    'code',
    'name',
    'state',
    'from_datetime',
    'to_datetime',
    'duration',
    'advance_allowed',
    ('company_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('branch_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('vehicle_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('create_uid', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    'fuel_type',
    'odometer',
    'odometer_unit',
    ('driver_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('spare1_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('spare2_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('expense_ids', [(
        'id',
        ('company_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        ('product_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'name',
        'amount',
        'attached_file',
    )]),
    ('consumption_ids', [(
        'id',
        'last_odometer',
        'current_odometer',
        'trip_distance',
        'standard_liter',
        'consumed_liter',
        'avg_calculation',
    )]),
    ('fuelin_ids', [(
        'id',
        ('company_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'date',
        'shop',
        ('product_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        ('location_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'slip_no',
        'liter',
        'price_unit',
        'amount',
        'add_from_office',
    )]),
    ('request_allowance_lines', [(
        'id',
        ('expense_categ_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'quantity',
        'amount',
        'total_amount',
        'remark'
    )]),
    ('product_lines', [(
        'id',
        ('company_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        ('product_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        ('product_uom', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'quantity',
    )]),
    'total_advance',
    'destination',
    'unit_expense',
    'tyre_points',
    'engine_oil_points',
)

# /api/day.plan.trip  POST  - Create one
# IN data:
#   HEADERS:
#       'access_token'
#   DEFAULTS:
#       (optional default values of fields)
DEFAULTS__day_plan_trip__create_one__JSON = {          # editable
            #"some_field_1": some_value_1,
            #"some_field_2": some_value_2,
            #...
}
#   JSON:
#       (fields and its values of created object;
#        don't forget about model's mandatory fields!)
#           ...                                     # editable
# OUT data:
OUT__day_plan_trip__create_one__SUCCESS_CODE = 200     # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       409 'not_created_object_in_odoo'
OUT__day_plan_trip__create_one__SCHEMA = (               # editable
    'id',
)

# /api/day.plan.trip/<id>  PUT  - Update one
# IN data:
#   HEADERS:
#       'access_token'
#   JSON:
#       (fields and new values of updated object)   # editable
#           ...
# OUT data:
OUT__day_plan_trip__update_one__SUCCESS_CODE = 200     # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       409 'not_updated_object_in_odoo'

# /api/day.plan.trip/<id>  DELETE  - Delete one
# IN data:
#   HEADERS:
#       'access_token'
# OUT data:
OUT__day_plan_trip__delete_one__SUCCESS_CODE = 200     # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       409 'not_deleted_object_in_odoo'

# /api/day.plan.trip/<id>/<method>  PUT  - Call method (with optional parameters)
# IN data:
#   HEADERS:
#       'access_token'
#   JSON:
#       (named parameters of method)                # editable
#           ...
# OUT data:
OUT__day_plan_trip__call_method__SUCCESS_CODE = 200    # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       501 'method_not_exist_in_odoo'
#       409 'not_called_method_in_odoo'


# HTTP controller of REST resources:

class ControllerREST(http.Controller):
    
    # Read all (with optional filters, offset, limit, order, exclude_fields, include_fields):
    @http.route('/api/day.plan.trip', methods=['GET'], type='http', auth='none')
    @check_permissions
    def api__day_plan_trip__GET(self, **kw):
        return wrap__resource__read_all(
            modelname = 'day.plan.trip',
            default_domain = [],
            success_code = OUT__day_plan_trip__read_all__SUCCESS_CODE,
            OUT_fields = OUT__day_plan_trip__read_all__SCHEMA
        )
    
    # Read one (with optional exclude_fields, include_fields):
    @http.route('/api/day.plan.trip/<id>', methods=['GET'], type='http', auth='none')
    @check_permissions
    def api__day_plan_trip__id_GET(self, id, **kw):
        return wrap__resource__read_one(
            modelname = 'day.plan.trip',
            id = id,
            success_code = OUT__day_plan_trip__read_one__SUCCESS_CODE,
            OUT_fields = OUT__day_plan_trip__read_one__SCHEMA
        )
    
    # Create one:
    @http.route('/api/day.plan.trip', methods=['POST'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__day_plan_trip__POST(self, **kw):
        return wrap__resource__create_one(
            modelname = 'day.plan.trip',
            default_vals = DEFAULTS__day_plan_trip__create_one__JSON,
            success_code = OUT__day_plan_trip__create_one__SUCCESS_CODE,
            OUT_fields = OUT__day_plan_trip__create_one__SCHEMA
        )
    
    # Update one:
    @http.route('/api/day.plan.trip/<id>', methods=['PUT'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__day_plan_trip__id_PUT(self, id, **kw):
        return wrap__resource__update_one(
            modelname = 'day.plan.trip',
            id = id,
            success_code = OUT__day_plan_trip__update_one__SUCCESS_CODE
        )
    
    # Delete one:
    @http.route('/api/day.plan.trip/<id>', methods=['DELETE'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__day_plan_trip__id_DELETE(self, id, **kw):
        return wrap__resource__delete_one(
            modelname = 'day.plan.trip',
            id = id,
            success_code = OUT__day_plan_trip__delete_one__SUCCESS_CODE
        )
    
    # Call method (with optional parameters):
    @http.route('/api/day.plan.trip/<id>/<method>', methods=['PUT'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__day_plan_trip__id__method_PUT(self, id, method, **kw):
        return wrap__resource__call_method(
            modelname = 'day.plan.trip',
            id = id,
            method = method,
            success_code = OUT__day_plan_trip__call_method__SUCCESS_CODE
        )
