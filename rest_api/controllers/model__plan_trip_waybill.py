# -*- coding: utf-8 -*-
from .main import *

_logger = logging.getLogger(__name__)


# List of REST resources in current file:
#   (url prefix)               (method)     (action)
# /api/plan.trip.waybill                GET     - Read all (with optional filters, offset, limit, order, exclude_fields, include_fields)
# /api/plan.trip.waybill/<id>           GET     - Read one (with optional exclude_fields, include_fields)
# /api/plan.trip.waybill                POST    - Create one
# /api/plan.trip.waybill/<id>           PUT     - Update one
# /api/plan.trip.waybill/<id>           DELETE  - Delete one
# /api/plan.trip.waybill/<id>/<method>  PUT     - Call method (with optional parameters)


# List of IN/OUT data (json data and HTTP-headers) for each REST resource:

# /api/plan.trip.waybill  GET  - Read all (with optional filters, offset, limit, order, exclude_fields, include_fields)
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
OUT__plan_trip_waybill__read_all__SUCCESS_CODE = 200       # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#   JSON:
#       {
#           "count":   XXX,     # number of returned records
#           "results": [
OUT__plan_trip_waybill__read_all__SCHEMA = (                 # editable
    'id',
    'name',
    'code',
    'state',
    'from_datetime',
    'to_datetime',
    'duration',
    'duration_hrs',
    'plan_duration',
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
    ('driver_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('trailer_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('spare_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('route_plan_ids', [(
        ('company_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        ('route_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
    )]),
    ('waybill_ids', [(
        ('account_move_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        ('partner_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'date',
        'amount',
        'state',
    )]),
    ('expense_ids', [(
        'id',
        ('route_expense_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'standard_amount',
        'actual_amount',
        'over_amount',
        'description',
        'attached_file',
    )]),
    ('consumption_ids', [(
        'id',
        'is_required',
        ('route_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'standard_liter',
        'consumed_liter',
        'description',
        'date',
    )]),
    'last_odometer',
    'current_odometer',
    'trip_distance',
    'total_standard_liter',
    'total_consumed_liter',
    'avg_calculation',
    ('commission_ids', [(
        ('route_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'commission_driver',
        'commission_spare',
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
        'slip_no',
        'liter',
        'price_unit',
        'amount',
        ('location_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
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
        'remark',
    )]),
    'total_advance',
    'tyre_points',
    'engine_oil_points',
    'unit_expense',
    ('driver_move_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('spare_move_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
)
#           ]
#       }

# /api/plan.trip.waybill/<id>  GET  - Read one (with optional exclude_fields, include_fields)
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
OUT__plan_trip_waybill__read_one__SUCCESS_CODE = 200       # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       404 'not_found_object_in_odoo'
OUT__plan_trip_waybill__read_one__SCHEMA = (                 # editable
    # (The order of fields of different types can be arbitrary)
    # simple fields (non relational):
    'id',
    'name',
    'code',
    'state',
    'from_datetime',
    'to_datetime',
    'duration',
    'duration_hrs',
    'plan_duration',
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
    ('driver_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('trailer_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('spare_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('route_plan_ids', [(
        ('route_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
    )]),
    ('waybill_ids', [(
        ('account_move_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        ('partner_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'date',
        'amount',
        'state',
    )]),
    ('expense_ids', [(
        'id',
        ('route_expense_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'standard_amount',
        'actual_amount',
        'over_amount',
        'description',
        'attached_file',
    )]),
    ('consumption_ids', [(
        'id',
        'is_required',
        ('route_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'standard_liter',
        'consumed_liter',
        'description',
        'date',
    )]),
    'last_odometer',
    'current_odometer',
    'trip_distance',
    'total_standard_liter',
    'total_consumed_liter',
    'avg_calculation',
    ('commission_ids', [(
        ('route_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'commission_driver',
        'commission_spare',
    )]),
    ('fuelin_ids', [(
        'id',
        'date',
        'shop',
        ('product_id', (  # will return dictionary of inner fields
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
        'remark',
    )]),
    'total_advance',
    'tyre_points',
    'engine_oil_points',
    'unit_expense',
    ('driver_move_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('spare_move_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
)

# /api/plan.trip.waybill  POST  - Create one
# IN data:
#   HEADERS:
#       'access_token'
#   DEFAULTS:
#       (optional default values of fields)
DEFAULTS__plan_trip_waybill__create_one__JSON = {          # editable
            #"some_field_1": some_value_1,
            #"some_field_2": some_value_2,
            #...
}
#   JSON:
#       (fields and its values of created object;
#        don't forget about model's mandatory fields!)
#           ...                                     # editable
# OUT data:
OUT__plan_trip_waybill__create_one__SUCCESS_CODE = 200     # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       409 'not_created_object_in_odoo'
OUT__plan_trip_waybill__create_one__SCHEMA = (               # editable
    'id',
)

# /api/plan.trip.waybill/<id>  PUT  - Update one
# IN data:
#   HEADERS:
#       'access_token'
#   JSON:
#       (fields and new values of updated object)   # editable
#           ...
# OUT data:
OUT__plan_trip_waybill__update_one__SUCCESS_CODE = 200     # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       409 'not_updated_object_in_odoo'

# /api/plan.trip.waybill/<id>  DELETE  - Delete one
# IN data:
#   HEADERS:
#       'access_token'
# OUT data:
OUT__plan_trip_waybill__delete_one__SUCCESS_CODE = 200     # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       409 'not_deleted_object_in_odoo'

# /api/plan.trip.waybill/<id>/<method>  PUT  - Call method (with optional parameters)
# IN data:
#   HEADERS:
#       'access_token'
#   JSON:
#       (named parameters of method)                # editable
#           ...
# OUT data:
OUT__plan_trip_waybill__call_method__SUCCESS_CODE = 200    # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       501 'method_not_exist_in_odoo'
#       409 'not_called_method_in_odoo'


# HTTP controller of REST resources:

class ControllerREST(http.Controller):
    
    # Read all (with optional filters, offset, limit, order, exclude_fields, include_fields):
    @http.route('/api/plan.trip.waybill', methods=['GET'], type='http', auth='none')
    @check_permissions
    def api__plan_trip_waybill__GET(self, **kw):
        return wrap__resource__read_all(
            modelname = 'plan.trip.waybill',
            default_domain = [],
            success_code = OUT__plan_trip_waybill__read_all__SUCCESS_CODE,
            OUT_fields = OUT__plan_trip_waybill__read_all__SCHEMA
        )
    
    # Read one (with optional exclude_fields, include_fields):
    @http.route('/api/plan.trip.waybill/<id>', methods=['GET'], type='http', auth='none')
    @check_permissions
    def api__plan_trip_waybill__id_GET(self, id, **kw):
        return wrap__resource__read_one(
            modelname = 'plan.trip.waybill',
            id = id,
            success_code = OUT__plan_trip_waybill__read_one__SUCCESS_CODE,
            OUT_fields = OUT__plan_trip_waybill__read_one__SCHEMA
        )
    
    # Create one:
    @http.route('/api/plan.trip.waybill', methods=['POST'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__plan_trip_waybill__POST(self, **kw):
        return wrap__resource__create_one(
            modelname = 'plan.trip.waybill',
            default_vals = DEFAULTS__plan_trip_waybill__create_one__JSON,
            success_code = OUT__plan_trip_waybill__create_one__SUCCESS_CODE,
            OUT_fields = OUT__plan_trip_waybill__create_one__SCHEMA
        )
    
    # Update one:
    @http.route('/api/plan.trip.waybill/<id>', methods=['PUT'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__plan_trip_waybill__id_PUT(self, id, **kw):
        return wrap__resource__update_one(
            modelname = 'plan.trip.waybill',
            id = id,
            success_code = OUT__plan_trip_waybill__update_one__SUCCESS_CODE
        )
    
    # Delete one:
    @http.route('/api/plan.trip.waybill/<id>', methods=['DELETE'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__plan_trip_waybill__id_DELETE(self, id, **kw):
        return wrap__resource__delete_one(
            modelname = 'plan.trip.waybill',
            id = id,
            success_code = OUT__plan_trip_waybill__delete_one__SUCCESS_CODE
        )
    
    # Call method (with optional parameters):
    @http.route('/api/plan.trip.waybill/<id>/<method>', methods=['PUT'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__plan_trip_waybill__id__method_PUT(self, id, method, **kw):
        return wrap__resource__call_method(
            modelname = 'plan.trip.waybill',
            id = id,
            method = method,
            success_code = OUT__plan_trip_waybill__call_method__SUCCESS_CODE
        )
