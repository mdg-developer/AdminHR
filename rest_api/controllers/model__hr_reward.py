# -*- coding: utf-8 -*-
from .main import *

_logger = logging.getLogger(__name__)


# List of REST resources in current file:
#   (url prefix)               (method)     (action)
# /api/hr.reward                GET     - Read all (with optional filters, offset, limit, order, exclude_fields, include_fields)
# /api/hr.reward/<id>           GET     - Read one (with optional exclude_fields, include_fields)
# /api/hr.reward                POST    - Create one
# /api/hr.reward/<id>           PUT     - Update one
# /api/hr.reward/<id>           DELETE  - Delete one
# /api/hr.reward/<id>/<method>  PUT     - Call method (with optional parameters)


# List of IN/OUT data (json data and HTTP-headers) for each REST resource:

# /api/hr.reward  GET  - Read all (with optional filters, offset, limit, order, exclude_fields, include_fields)
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
OUT__hr_reward__read_all__SUCCESS_CODE = 200       # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#   JSON:
#       {
#           "count":   XXX,     # number of returned records
#           "results": [
OUT__hr_reward__read_all__SCHEMA = (                 # editable
    'id',
    'name',
    ('employee_id', [(
        'id',
        'name',
        'reward_carried_forward',
        'reward_this_year',
        'reward_total',
    )]),
    ('company_id', [(
        'id',
        'name',
    )]),
    ('branch_id', [(
        'id',
        'name',
    )]),
    ('department_id', [(
        'id',
        'name',
    )]),
    ('warning_attach_id', [(
        'id',
        'attached_filename',
        'attachment',
    )]),
    ('reward_type_id', [(
        'id',
        'name',
    )]),
    ('reward_title_id', [(
        'id',
        'name',
    )]),
    'state',
    'date',
    'description',
    'mark',
    ('manager_reward_ids', [(
        ('employee_id', (
            'id',
            'name',
        )),
        'mark',
    )]),
)
#           ]
#       }

# /api/hr.reward/<id>  GET  - Read one (with optional exclude_fields, include_fields)
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
OUT__hr_reward__read_one__SUCCESS_CODE = 200       # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       404 'not_found_object_in_odoo'
OUT__hr_reward__read_one__SCHEMA = (                 # editable
    'id',
    'name',
    ('employee_id', [(
        'id',
        'name',
        'reward_carried_forward',
        'reward_this_year',
        'reward_total',
    )]),
    ('company_id', [(
        'id',
        'name',
    )]),
    ('branch_id', [(
        'id',
        'name',
    )]),
    ('department_id', [(
        'id',
        'name',
    )]),
    ('warning_attach_id', [(
        'id',
        'attached_filename',
        'attachment',
    )]),
    ('reward_type_id', [(
        'id',
        'name',
    )]),
    ('reward_title_id', [(
        'id',
        'name',
    )]),
    'state',
    'date',
    'description',
    'mark',
    ('manager_reward_ids', [(
        ('employee_id', (
            'id',
            'name',
        )),
        'mark',
    )]),
)

# /api/hr.reward  POST  - Create one
# IN data:
#   HEADERS:
#       'access_token'
#   DEFAULTS:
#       (optional default values of fields)
DEFAULTS__hr_reward__create_one__JSON = {          # editable
            #"some_field_1": some_value_1,
            #"some_field_2": some_value_2,
            #...
}
#   JSON:
#       (fields and its values of created object;
#        don't forget about model's mandatory fields!)
#           ...                                     # editable
# OUT data:
OUT__hr_reward__create_one__SUCCESS_CODE = 200     # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       409 'not_created_object_in_odoo'
OUT__hr_reward__create_one__SCHEMA = (               # editable
    'id',
)

# /api/hr.reward/<id>  PUT  - Update one
# IN data:
#   HEADERS:
#       'access_token'
#   JSON:
#       (fields and new values of updated object)   # editable
#           ...
# OUT data:
OUT__hr_reward__update_one__SUCCESS_CODE = 200     # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       409 'not_updated_object_in_odoo'

# /api/hr.reward/<id>  DELETE  - Delete one
# IN data:
#   HEADERS:
#       'access_token'
# OUT data:
OUT__hr_reward__delete_one__SUCCESS_CODE = 200     # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       409 'not_deleted_object_in_odoo'

# /api/hr.reward/<id>/<method>  PUT  - Call method (with optional parameters)
# IN data:
#   HEADERS:
#       'access_token'
#   JSON:
#       (named parameters of method)                # editable
#           ...
# OUT data:
OUT__hr_reward__call_method__SUCCESS_CODE = 200    # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       501 'method_not_exist_in_odoo'
#       409 'not_called_method_in_odoo'


# HTTP controller of REST resources:

class ControllerREST(http.Controller):
    
    # Read all (with optional filters, offset, limit, order, exclude_fields, include_fields):
    @http.route('/api/hr.reward', methods=['GET'], type='http', auth='none')
    @check_permissions
    def api__hr_reward__GET(self, **kw):
        return wrap__resource__read_all(
            modelname = 'hr.reward',
            default_domain = [],
            success_code = OUT__hr_reward__read_all__SUCCESS_CODE,
            OUT_fields = OUT__hr_reward__read_all__SCHEMA
        )
    
    # Read one (with optional exclude_fields, include_fields):
    @http.route('/api/hr.reward/<id>', methods=['GET'], type='http', auth='none')
    @check_permissions
    def api__hr_reward__id_GET(self, id, **kw):
        return wrap__resource__read_one(
            modelname = 'hr.reward',
            id = id,
            success_code = OUT__hr_reward__read_one__SUCCESS_CODE,
            OUT_fields = OUT__hr_reward__read_one__SCHEMA
        )
    
    # Create one:
    @http.route('/api/hr.reward', methods=['POST'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__hr_reward__POST(self, **kw):
        return wrap__resource__create_one(
            modelname = 'hr.reward',
            default_vals = DEFAULTS__hr_reward__create_one__JSON,
            success_code = OUT__hr_reward__create_one__SUCCESS_CODE,
            OUT_fields = OUT__hr_reward__create_one__SCHEMA
        )
    
    # Update one:
    @http.route('/api/hr.reward/<id>', methods=['PUT'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__hr_reward__id_PUT(self, id, **kw):
        return wrap__resource__update_one(
            modelname = 'hr.reward',
            id = id,
            success_code = OUT__hr_reward__update_one__SUCCESS_CODE
        )
    
    # Delete one:
    @http.route('/api/hr.reward/<id>', methods=['DELETE'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__hr_reward__id_DELETE(self, id, **kw):
        return wrap__resource__delete_one(
            modelname = 'hr.reward',
            id = id,
            success_code = OUT__hr_reward__delete_one__SUCCESS_CODE
        )
    
    # Call method (with optional parameters):
    @http.route('/api/hr.reward/<id>/<method>', methods=['PUT'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__hr_reward__id__method_PUT(self, id, method, **kw):
        return wrap__resource__call_method(
            modelname = 'hr.reward',
            id = id,
            method = method,
            success_code = OUT__hr_reward__call_method__SUCCESS_CODE
        )
