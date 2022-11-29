# -*- coding: utf-8 -*-
from .main import *

_logger = logging.getLogger(__name__)


# List of REST resources in current file:
#   (url prefix)               (method)     (action)
# /api/maintenance.request                GET     - Read all (with optional filters, offset, limit, order, exclude_fields, include_fields)
# /api/maintenance.request/<id>           GET     - Read one (with optional exclude_fields, include_fields)
# /api/maintenance.request                POST    - Create one
# /api/maintenance.request/<id>           PUT     - Update one
# /api/maintenance.request/<id>           DELETE  - Delete one
# /api/maintenance.request/<id>/<method>  PUT     - Call method (with optional parameters)


# List of IN/OUT data (json data and HTTP-headers) for each REST resource:

# /api/maintenance.request  GET  - Read all (with optional filters, offset, limit, order, exclude_fields, include_fields)
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
OUT__maintenance_request__read_all__SUCCESS_CODE = 200       # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#   JSON:
#       {
#           "count":   XXX,     # number of returned records
#           "results": [
OUT__maintenance_request__read_all__SCHEMA = (                 # editable
    'id',
    'name',
    'code',
    'state',
    ('vehicle_id', (  # will return dictionary of inner fields
        'id',
        'name',
        'incharge_id',
    )),
    ('driver_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('company_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('branch_id', (  # will return dictionary of inner fields
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
    'request_date',
    'maintenance_type',
    'image',
    'image1',
    'image2',
    'image3',
    'image4',
    'image5',
    'image_filename',
    'image1_filename',
    'image2_filename',
    'image3_filename',
    'image4_filename',
    'image5_filename',
    ('maintenance_team_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('user_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    'start_date',
    'end_date',
    'actual_duration',
    'duration_days', 
    'duration_hrs',
    'priority',
    'email_cc',
    'description',
    ('purchase_line', [(
        'name',
        'date_approve',
        ('partner_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        ('company_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'date_planned',
        ('user_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'origin',
        'amount_total',
        'state',
    )]),
    ('warehouse_ids', [(
        ('product_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        ('location_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'cost',
        'qty',
    )]),
    ('maintenance_product_ids', [(
        'id',
        ('line_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        ('product_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        ('category_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'type',
        'qty',
    )]),
    ('location_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    'qty',
)
#           ]
#       }

# /api/maintenance.request/<id>  GET  - Read one (with optional exclude_fields, include_fields)
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
OUT__maintenance_request__read_one__SUCCESS_CODE = 200       # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       404 'not_found_object_in_odoo'
OUT__maintenance_request__read_one__SCHEMA = (                 # editable
    'id',
    'name',
    'code',
    'state',
    ('vehicle_id', (  # will return dictionary of inner fields
        'id',
        'name',
        'incharge_id',
    )),
    ('driver_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('company_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('branch_id', (  # will return dictionary of inner fields
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
    'request_date',
    'maintenance_type',
    'image',
    'image1',
    'image2',
    'image3',
    'image4',
    'image5',
    'image_filename',
    'image1_filename',
    'image2_filename',
    'image3_filename',
    'image4_filename',
    'image5_filename',
    ('maintenance_team_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    ('user_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    'start_date',
    'end_date',
    'actual_duration',
    'duration_days', 
    'duration_hrs',
    'priority',
    'email_cc',
    'description',
    ('purchase_line', [(
        'name',
        'date_approve',
        ('partner_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        ('company_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'date_planned',
        ('user_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'origin',
        'amount_total',
        'state',
    )]),
    ('warehouse_ids', [(
        ('product_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        ('location_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'cost',
        'qty',
    )]),
    ('maintenance_product_ids', [(
        'id',
        ('line_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        ('product_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        ('category_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'type',
        'qty',
    )]),
    ('location_id', (  # will return dictionary of inner fields
        'id',
        'name',
    )),
    'qty',
)

# /api/maintenance.request  POST  - Create one
# IN data:
#   HEADERS:
#       'access_token'
#   DEFAULTS:
#       (optional default values of fields)
DEFAULTS__maintenance_request__create_one__JSON = {          # editable
            #"some_field_1": some_value_1,
            #"some_field_2": some_value_2,
            #...
}
#   JSON:
#       (fields and its values of created object;
#        don't forget about model's mandatory fields!)
#           ...                                     # editable
# OUT data:
OUT__maintenance_request__create_one__SUCCESS_CODE = 200     # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       409 'not_created_object_in_odoo'
OUT__maintenance_request__create_one__SCHEMA = (               # editable
    'id',
)

# /api/maintenance.request/<id>  PUT  - Update one
# IN data:
#   HEADERS:
#       'access_token'
#   JSON:
#       (fields and new values of updated object)   # editable
#           ...
# OUT data:
OUT__maintenance_request__update_one__SUCCESS_CODE = 200     # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       409 'not_updated_object_in_odoo'

# /api/maintenance.request/<id>  DELETE  - Delete one
# IN data:
#   HEADERS:
#       'access_token'
# OUT data:
OUT__maintenance_request__delete_one__SUCCESS_CODE = 200     # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       409 'not_deleted_object_in_odoo'

# /api/maintenance.request/<id>/<method>  PUT  - Call method (with optional parameters)
# IN data:
#   HEADERS:
#       'access_token'
#   JSON:
#       (named parameters of method)                # editable
#           ...
# OUT data:
OUT__maintenance_request__call_method__SUCCESS_CODE = 200    # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       501 'method_not_exist_in_odoo'
#       409 'not_called_method_in_odoo'


# HTTP controller of REST resources:

class ControllerREST(http.Controller):
    
    # Read all (with optional filters, offset, limit, order, exclude_fields, include_fields):
    @http.route('/api/maintenance.request', methods=['GET'], type='http', auth='none')
    @check_permissions
    def api__maintenance_request__GET(self, **kw):
        return wrap__resource__read_all(
            modelname = 'maintenance.request',
            default_domain = [],
            success_code = OUT__maintenance_request__read_all__SUCCESS_CODE,
            OUT_fields = OUT__maintenance_request__read_all__SCHEMA
        )
    
    # Read one (with optional exclude_fields, include_fields):
    @http.route('/api/maintenance.request/<id>', methods=['GET'], type='http', auth='none')
    @check_permissions
    def api__maintenance_request__id_GET(self, id, **kw):
        return wrap__resource__read_one(
            modelname = 'maintenance.request',
            id = id,
            success_code = OUT__maintenance_request__read_one__SUCCESS_CODE,
            OUT_fields = OUT__maintenance_request__read_one__SCHEMA
        )
    
    # Create one:
    @http.route('/api/maintenance.request', methods=['POST'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__maintenance_request__POST(self, **kw):
        return wrap__resource__create_one(
            modelname = 'maintenance.request',
            default_vals = DEFAULTS__maintenance_request__create_one__JSON,
            success_code = OUT__maintenance_request__create_one__SUCCESS_CODE,
            OUT_fields = OUT__maintenance_request__create_one__SCHEMA
        )
    
    # Update one:
    @http.route('/api/maintenance.request/<id>', methods=['PUT'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__maintenance_request__id_PUT(self, id, **kw):
        return wrap__resource__update_one(
            modelname = 'maintenance.request',
            id = id,
            success_code = OUT__maintenance_request__update_one__SUCCESS_CODE
        )
    
    # Delete one:
    @http.route('/api/maintenance.request/<id>', methods=['DELETE'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__maintenance_request__id_DELETE(self, id, **kw):
        return wrap__resource__delete_one(
            modelname = 'maintenance.request',
            id = id,
            success_code = OUT__maintenance_request__delete_one__SUCCESS_CODE
        )
    
    # Call method (with optional parameters):
    @http.route('/api/maintenance.request/<id>/<method>', methods=['PUT'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__maintenance_request__id__method_PUT(self, id, method, **kw):
        return wrap__resource__call_method(
            modelname = 'maintenance.request',
            id = id,
            method = method,
            success_code = OUT__maintenance_request__call_method__SUCCESS_CODE
        )
