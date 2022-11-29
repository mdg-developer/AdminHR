# -*- coding: utf-8 -*-
from .main import *

_logger = logging.getLogger(__name__)


# List of REST resources in current file:
#   (url prefix)               (method)     (action)
# /api/summary.request                GET     - Read all (with optional filters, offset, limit, order, exclude_fields, include_fields)
# /api/summary.request/<id>           GET     - Read one (with optional exclude_fields, include_fields)
# /api/summary.request                POST    - Create one
# /api/summary.request/<id>           PUT     - Update one
# /api/summary.request/<id>           DELETE  - Delete one
# /api/summary.request/<id>/<method>  PUT     - Call method (with optional parameters)


# List of IN/OUT data (json data and HTTP-headers) for each REST resource:

# /api/summary.request  GET  - Read all (with optional filters, offset, limit, order, exclude_fields, include_fields)
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
OUT__summary_request__read_all__SUCCESS_CODE = 200       # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#   JSON:
#       {
#           "count":   XXX,     # number of returned records
#           "results": [
OUT__summary_request__read_all__SCHEMA = (                 # editable
    'id',
    'name',
    ('employee_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('holiday_status_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    'start_date',
    'end_date',
    'duration',
    'attachment',
    'file_name',
    'description',
    'resource_calendar_id',
    'state',
    ('leave_line', [(
        'date',
        'dayofweek',
        'full',
        'first',
        'second',
        'start_date',
        'end_date',
        'this_day_hour_id',
        'next_day_hour_id',
        'resource_calendar_id',
        'distinct_shift',
        'allow_full_edit',
        'allow_first_edit',
        'allow_second_edit',
    )]),
    'create_date',
    'duration_unpaid_leave',
)
#           ]
#       }

# /api/summary.request/<id>  GET  - Read one (with optional exclude_fields, include_fields)
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
OUT__summary_request__read_one__SUCCESS_CODE = 200       # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       404 'not_found_object_in_odoo'
OUT__summary_request__read_one__SCHEMA = (                 # editable
    # (The order of fields of different types can be arbitrary)
    # simple fields (non relational):
    'id',
    'name',
    ('employee_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('holiday_status_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    'start_date',
    'end_date',
    'duration',
    'attachment',
    'file_name',
    'description',
    'resource_calendar_id',
    'state',
    ('leave_line', [(
        'date',
        'dayofweek',
        'full',
        'first',
        'second',
        'start_date',
        'end_date',
        'this_day_hour_id',
        'next_day_hour_id',
        'resource_calendar_id',
        'distinct_shift',
        'allow_full_edit',
        'allow_first_edit',
        'allow_second_edit',
    )]),
    'create_date',
    'duration_unpaid_leave',
)

# /api/summary.request  POST  - Create one
# IN data:
#   HEADERS:
#       'access_token'
#   DEFAULTS:
#       (optional default values of fields)
DEFAULTS__summary_request__create_one__JSON = {          # editable
            #"some_field_1": some_value_1,
            #"some_field_2": some_value_2,
            #...
}
#   JSON:
#       (fields and its values of created object;
#        don't forget about model's mandatory fields!)
#           ...                                     # editable
# OUT data:
OUT__summary_request__create_one__SUCCESS_CODE = 200     # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       409 'not_created_object_in_odoo'
OUT__summary_request__create_one__SCHEMA = (               # editable
    'id',
)

# /api/summary.request/<id>  PUT  - Update one
# IN data:
#   HEADERS:
#       'access_token'
#   JSON:
#       (fields and new values of updated object)   # editable
#           ...
# OUT data:
OUT__summary_request__update_one__SUCCESS_CODE = 200     # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       409 'not_updated_object_in_odoo'

# /api/summary.request/<id>  DELETE  - Delete one
# IN data:
#   HEADERS:
#       'access_token'
# OUT data:
OUT__summary_request__delete_one__SUCCESS_CODE = 200     # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       409 'not_deleted_object_in_odoo'

# /api/summary.request/<id>/<method>  PUT  - Call method (with optional parameters)
# IN data:
#   HEADERS:
#       'access_token'
#   JSON:
#       (named parameters of method)                # editable
#           ...
# OUT data:
OUT__summary_request__call_method__SUCCESS_CODE = 200    # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       501 'method_not_exist_in_odoo'
#       409 'not_called_method_in_odoo'


# HTTP controller of REST resources:

class ControllerREST(http.Controller):
    
    # Read all (with optional filters, offset, limit, order, exclude_fields, include_fields):
    @http.route('/api/summary.request', methods=['GET'], type='http', auth='none')
    @check_permissions
    def api__summary_request__GET(self, **kw):
        return wrap__resource__read_all(
            modelname = 'summary.request',
            default_domain = [],
            success_code = OUT__summary_request__read_all__SUCCESS_CODE,
            OUT_fields = OUT__summary_request__read_all__SCHEMA
        )
    
    # Read one (with optional exclude_fields, include_fields):
    @http.route('/api/summary.request/<id>', methods=['GET'], type='http', auth='none')
    @check_permissions
    def api__summary_request__id_GET(self, id, **kw):
        return wrap__resource__read_one(
            modelname = 'summary.request',
            id = id,
            success_code = OUT__summary_request__read_one__SUCCESS_CODE,
            OUT_fields = OUT__summary_request__read_one__SCHEMA
        )
    
    # Create one:
    @http.route('/api/summary.request', methods=['POST'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__summary_request__POST(self, **kw):
        return wrap__resource__create_one(
            modelname = 'summary.request',
            default_vals = DEFAULTS__summary_request__create_one__JSON,
            success_code = OUT__summary_request__create_one__SUCCESS_CODE,
            OUT_fields = OUT__summary_request__create_one__SCHEMA
        )
    
    # Update one:
    @http.route('/api/summary.request/<id>', methods=['PUT'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__summary_request__id_PUT(self, id, **kw):
        return wrap__resource__update_one(
            modelname = 'summary.request',
            id = id,
            success_code = OUT__summary_request__update_one__SUCCESS_CODE
        )
    
    # Delete one:
    @http.route('/api/summary.request/<id>', methods=['DELETE'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__summary_request__id_DELETE(self, id, **kw):
        return wrap__resource__delete_one(
            modelname = 'summary.request',
            id = id,
            success_code = OUT__summary_request__delete_one__SUCCESS_CODE
        )
    
    # Call method (with optional parameters):
    @http.route('/api/summary.request/<id>/<method>', methods=['PUT'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__summary_request__id__method_PUT(self, id, method, **kw):
        return wrap__resource__call_method(
            modelname = 'summary.request',
            id = id,
            method = method,
            success_code = OUT__summary_request__call_method__SUCCESS_CODE
        )
