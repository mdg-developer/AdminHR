# -*- coding: utf-8 -*-
# Copyright 2017-2018 ZAD solutions (<http://www.zadsolutions.com>).
#  author : umar_3ziz@hotmail.com.
#  License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
{
    'name': 'Location Map Coordinates',
    'category': 'Location',
    "version": "10.0.1.0.0",
    'author': 'Omar Abdulaziz',
    'website': 'https://www.zadsolutions.com',
    'description': """
    Google Map Location,\nThis module create widget Google Map that allow you to get your coordinates (longitude and latitude)
 and with a button (Get My Current Coordinate). 
 To use this module go to your module and Create 2 new fields 'Float' with name (provider_latitude, provider_longitude)
 and 1 field Boolean with name (is_today) to check if your date is today or not to use the widget if you do not need to use
 condition of 'is_today' just make the field and put default value True,
 in your xml file you can create <widget type="location_ci"/>
 and once you click the button (Get my current coordinate) widget capture your long and lat into your fields
    """,
    'depends': [],
    'license': 'AGPL-3',
    'data': [
        'views/widget_coordinates_template.xml',
    ],
    'qweb': ['static/src/xml/coordinates_template.xml'],
    'installable': True,
    'images': [
        'static/description/Googlemap.jpg',
    ],
    'price': 15.00,
    'currency': 'EUR',

}