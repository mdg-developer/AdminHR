# -*- coding: utf-8 -*-
from .main import *

_logger = logging.getLogger(__name__)


# List of REST resources in current file:
#   (url prefix)               (method)     (action)
# /api/fleet.vehicle                GET     - Read all (with optional filters, offset, limit, order, exclude_fields, include_fields)
# /api/fleet.vehicle/<id>           GET     - Read one (with optional exclude_fields, include_fields)
# /api/fleet.vehicle                POST    - Create one
# /api/fleet.vehicle/<id>           PUT     - Update one
# /api/fleet.vehicle/<id>           DELETE  - Delete one
# /api/fleet.vehicle/<id>/<method>  PUT     - Call method (with optional parameters)


# List of IN/OUT data (json data and HTTP-headers) for each REST resource:

# /api/fleet.vehicle  GET  - Read all (with optional filters, offset, limit, order, exclude_fields, include_fields)
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
OUT__fleet_vehicle__read_all__SUCCESS_CODE = 200       # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#   JSON:
#       {
#           "count":   XXX,     # number of returned records
#           "results": [
OUT__fleet_vehicle__read_all__SCHEMA = (                 # editable
    'id',
    'name',
    'traccar_uniqueID',
    ('model_id', (
        'id',
        'name',
    )),
    'license_plate',
    ('tag_ids', [(
        'id',
        'name',
    )]),
    ('incharge_id', (
        'id',
        'name',
    )),
    ('future_driver_id', (
        'id',
        'name',
    )),
    'plan_to_change_car',
    'next_assignation_date',
    'location',
    ('spare_id', (
        'id',
        'name',
    )),
    ('trailer_id', (
        'id',
        'name',
    )),
    ('future_trailer_id', (
        'id',
        'name',
    )),
    'trailer_assignation_date',
    'trailer_location',
    ('fuel_tank', (
        'id',
        'name',
    )),
    ('manager_id', (
        'id',
        'name',
    )),
    ('company_id', (
        'id',
        'name',
    )),
    ('branch_id', (
        'id',
        'name',
    )),
    'first_contract_date',
    'image_128',
    ('driver_id', (
        'id',
        'name',
    )),
    'odometer',
    'odometer_unit',
    'fuel_type',
    'acquisition_date',
    'horsepower',
    'vin_sn',
    'car_value',
    'net_car_value',
    'residual_value',
    'average_speed',
    'maxs_peed',
    'engine_hours',
    'display_engine_hours',
    'morning_engine_on',
    'last_engine_off',
    'day_trip',
    'seats',
    'doors',
    'color',
    'consuption_average',
    'grant_consuption_average',
    ('consumption_average_history_ids', [(
        ('employee_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'modified_date',
        'consumption_liter',
        'odometer',
        'great_average',
        'source_doc',
    )]),
    'transmission',
    'fuel_type',
    'horsepower_tax',
    'power',
    ('fleet_tyre_history_ids', [(
        ('vehicle_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'date',
        'used_points',
        'source_doc',
        'note',
    )]),
)
#           ]
#       }

# /api/fleet.vehicle/<id>  GET  - Read one (with optional exclude_fields, include_fields)
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
OUT__fleet_vehicle__read_one__SUCCESS_CODE = 200       # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       404 'not_found_object_in_odoo'
OUT__fleet_vehicle__read_one__SCHEMA = (                 # editable
    'id',
    'name',
    'traccar_uniqueID',
    ('model_id', (
        'id',
        'name',
    )),
    'license_plate',
    ('tag_ids', [(
        'id',
        'name',
    )]),
    ('incharge_id', (
        'id',
        'name',
    )),
    ('future_driver_id', (
        'id',
        'name',
    )),
    'plan_to_change_car',
    'next_assignation_date',
    'location',
    ('spare_id', (
        'id',
        'name',
    )),
    ('trailer_id', (
        'id',
        'name',
    )),
    ('future_trailer_id', (
        'id',
        'name',
    )),
    'trailer_assignation_date',
    'trailer_location',
    ('fuel_tank', (
        'id',
        'name',
    )),
    ('manager_id', (
        'id',
        'name',
    )),
    ('company_id', (
        'id',
        'name',
    )),
    ('branch_id', (
        'id',
        'name',
    )),
    'first_contract_date',
    'image_128',
    ('driver_id', (
        'id',
        'name',
    )),
    'odometer',
    'odometer_unit',
    'fuel_type',
    'acquisition_date',
    'horsepower',
    'vin_sn',
    'car_value',
    'net_car_value',
    'residual_value',
    'average_speed',
    'maxs_peed',
    'engine_hours',
    'display_engine_hours',
    'morning_engine_on',
    'last_engine_off',
    'day_trip',
    'seats',
    'doors',
    'color',
    'consuption_average',
    'grant_consuption_average',
    ('consumption_average_history_ids', [(
        ('employee_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'modified_date',
        'consumption_liter',
        'odometer',
        'great_average',
        'source_doc',
    )]),
    'transmission',
    'fuel_type',
    'horsepower_tax',
    'power',
    ('fleet_tyre_history_ids', [(
        ('vehicle_id', (  # will return dictionary of inner fields
            'id',
            'name',
        )),
        'date',
        'used_points',
        'source_doc',
        'note',
    )]),
)

# /api/fleet.vehicle  POST  - Create one
# IN data:
#   HEADERS:
#       'access_token'
#   DEFAULTS:
#       (optional default values of fields)
DEFAULTS__fleet_vehicle__create_one__JSON = {          # editable
            #"some_field_1": some_value_1,
            #"some_field_2": some_value_2,
            #...
}
#   JSON:
#       (fields and its values of created object;
#        don't forget about model's mandatory fields!)
#           ...                                     # editable
# OUT data:
OUT__fleet_vehicle__create_one__SUCCESS_CODE = 200     # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       409 'not_created_object_in_odoo'
OUT__fleet_vehicle__create_one__SCHEMA = (               # editable
    'id',
)

# /api/fleet.vehicle/<id>  PUT  - Update one
# IN data:
#   HEADERS:
#       'access_token'
#   JSON:
#       (fields and new values of updated object)   # editable
#           ...
# OUT data:
OUT__fleet_vehicle__update_one__SUCCESS_CODE = 200     # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       409 'not_updated_object_in_odoo'

# /api/fleet.vehicle/<id>  DELETE  - Delete one
# IN data:
#   HEADERS:
#       'access_token'
# OUT data:
OUT__fleet_vehicle__delete_one__SUCCESS_CODE = 200     # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       409 'not_deleted_object_in_odoo'

# /api/fleet.vehicle/<id>/<method>  PUT  - Call method (with optional parameters)
# IN data:
#   HEADERS:
#       'access_token'
#   JSON:
#       (named parameters of method)                # editable
#           ...
# OUT data:
OUT__fleet_vehicle__call_method__SUCCESS_CODE = 200    # editable
#   Possible ERROR CODES:
#       401 'invalid_token'
#       400 'no_access_token'
#       400 'invalid_object_id'
#       501 'method_not_exist_in_odoo'
#       409 'not_called_method_in_odoo'


# HTTP controller of REST resources:

class ControllerREST(http.Controller):
    
    # Read all (with optional filters, offset, limit, order, exclude_fields, include_fields):
    @http.route('/api/fleet.vehicle', methods=['GET'], type='http', auth='none')
    @check_permissions
    def api__fleet_vehicle__GET(self, **kw):
        return wrap__resource__read_all(
            modelname = 'fleet.vehicle',
            default_domain = [],
            success_code = OUT__fleet_vehicle__read_all__SUCCESS_CODE,
            OUT_fields = OUT__fleet_vehicle__read_all__SCHEMA
        )
    
    # Read one (with optional exclude_fields, include_fields):
    @http.route('/api/fleet.vehicle/<id>', methods=['GET'], type='http', auth='none')
    @check_permissions
    def api__fleet_vehicle__id_GET(self, id, **kw):
        return wrap__resource__read_one(
            modelname = 'fleet.vehicle',
            id = id,
            success_code = OUT__fleet_vehicle__read_one__SUCCESS_CODE,
            OUT_fields = OUT__fleet_vehicle__read_one__SCHEMA
        )
    
    # Create one:
    @http.route('/api/fleet.vehicle', methods=['POST'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__fleet_vehicle__POST(self, **kw):
        return wrap__resource__create_one(
            modelname = 'fleet.vehicle',
            default_vals = DEFAULTS__fleet_vehicle__create_one__JSON,
            success_code = OUT__fleet_vehicle__create_one__SUCCESS_CODE,
            OUT_fields = OUT__fleet_vehicle__create_one__SCHEMA
        )
    
    # Update one:
    @http.route('/api/fleet.vehicle/<id>', methods=['PUT'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__fleet_vehicle__id_PUT(self, id, **kw):
        return wrap__resource__update_one(
            modelname = 'fleet.vehicle',
            id = id,
            success_code = OUT__fleet_vehicle__update_one__SUCCESS_CODE
        )
    
    # Delete one:
    @http.route('/api/fleet.vehicle/<id>', methods=['DELETE'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__fleet_vehicle__id_DELETE(self, id, **kw):
        return wrap__resource__delete_one(
            modelname = 'fleet.vehicle',
            id = id,
            success_code = OUT__fleet_vehicle__delete_one__SUCCESS_CODE
        )
    
    # Call method (with optional parameters):
    @http.route('/api/fleet.vehicle/<id>/<method>', methods=['PUT'], type='http', auth='none', csrf=False)
    @check_permissions
    def api__fleet_vehicle__id__method_PUT(self, id, method, **kw):
        return wrap__resource__call_method(
            modelname = 'fleet.vehicle',
            id = id,
            method = method,
            success_code = OUT__fleet_vehicle__call_method__SUCCESS_CODE
        )
