odoo.define('widget_coordinates.get_location', function (require) {
    "use strict";
     var Widget = require('web.Widget');
    var core = require('web.core');
    var widgetRegistry = require('web.widget_registry');
    var FieldManagerMixin = require('web.FieldManagerMixin');
    var QWeb = core.qweb;
    var session = require('web.session');

    var WidgetCoordinates = Widget.extend(FieldManagerMixin, {
        className: 'o_map_view',
        template: 'MapView.MapView',
             events: {
            'click button': function () {
                var self = this;
                console.log("self customer location"+self.customer_location)
                if (self.customer_location!= null) {
                    self.trigger_up('field_changed', {
                             dataPointID: self.id,
                             changes: {
                                  partner_latitude: self.customer_location.lat(),
                                  partner_longitude: self.customer_location.lng(),
                             },
                             viewType: self.viewType,
                         });
                }else{
                    alert("Please Update location with marker.");
                }
            }
        },
        custom_events: _.extend({}, FieldManagerMixin.custom_events, {
            field_changed: '_onFieldChanged',
        }),
            init: function (parent, options) {
                this._super.apply(this, arguments);
                FieldManagerMixin.init.call(this);
                this.id = options.id;
                this.data = options.data;
                if(this.data.partner_latitude){
                    this.partner_latitude = this.data.partner_latitude;
                    this.partner_longitude = this.data.partner_longitude;
                }
                this.res_id = options.res_id;
                this.viewType = options.viewType;
            },
            start: function () {
                var sup = this._super();
                this.initMap();
                return sup;
            },
                error:function(err) {
                  console.warn(`ERROR(${err.code}): ${err.message}`);
                },
                 _onFieldChanged: function (ev) {
            if (ev.target === this) {
                ev.initialEvent = this.lastInitialEvent;
                return;
            }
            ev.stopPropagation();
            // changes occured in an editable list
            var changes = ev.data.changes;
            // save the initial event triggering the field_changed, as it will be
            // necessary when the field triggering this event will be reset (to
            // prevent it from re-rendering itself, formatting its value, loosing
            // the focus... while still being edited)
            this.lastInitialEvent = undefined;
            if (Object.keys(changes).length) {
                this.lastInitialEvent = ev;
                this._setValue({
                    operation: 'UPDATE',
                    id: ev.data.dataPointID,
                    data: changes,
                }).done(function () {
                    if (ev.data.onSuccess) {
                        ev.data.onSuccess();
                    }
                }).fail(function () {
                    if (ev.data.onFailure) {
                        ev.data.onFailure();
                    }
                });
            }
        },
            initMap: function () {
                 var marker, gmap, infoWindow;
                 var self = this;
                 var data = this.data;
                 var map_div = this.$('.o_map_view').get(0);

                    var options = {
                      enableHighAccuracy: true,
                      timeout: 20000,
                      maximumAge: 10000
                    };
                    var customer_loc = {
                              lat: 16.8767626,
                              lng: 96.1571778,
                            };
                   gmap  = new google.maps.Map(map_div, {
                                        mapTypeId: google.maps.MapTypeId.ROADMAP,
                                        zoom: 17,
                                        center: customer_loc,
                                        mapTypeControl: true,
                                        zoomControl: true,
                                        rotateControl: true,
                                        streetViewControl:true,
                                        });
                    var partner_longitude = this.partner_longitude;
                    var partner_latitude = this.partner_latitude;
                    var custName = this.data.name;
                    var partner_id = this.data.partner_id;

                    console.log("Existing customer location:LON"+partner_longitude + ",LAT"+partner_latitude);
                    if(partner_longitude!=null && partner_latitude!=null)
                    {
                         customer_loc = {
                              lat: partner_latitude,
                              lng: partner_longitude,
                            };


                        gmap  = new google.maps.Map(map_div, {
                                        mapTypeId: google.maps.MapTypeId.ROADMAP,
                                        zoom: 17,
                                        center: customer_loc,
                                        mapTypeControl: true,
                                        zoomControl: true,
                                        rotateControl: true,
                                        streetViewControl:true,
                                        });

                          infoWindow = new google.maps.InfoWindow({
                                           content: custName
                                      });
                           marker = new google.maps.Marker({
                            position: customer_loc,
                            draggable: true,
                            animation: google.maps.Animation.DROP,
                            title: custName
                          });
                          marker.setMap(gmap);
                          marker.addListener('dragend', function(mouseEvent) {
                                console.log("Change Location lat"+session.customer_location
                                            +",long"+marker.getPosition().lng());
                                            var currentLatLng =  new google.maps.LatLng(marker.getPosition().lat(), marker.getPosition().lng())
                                          self.trigger_up('field_changed', {
                                                     dataPointID: self.id,
                                                     changes: {
                                                         partner_latitude: marker.getPosition().lat(),
                                                         partner_longitude: marker.getPosition().lng(),
                                                     },
                                                     viewType: self.viewType,
                                         });

                                            infoWindow.open(gmap, marker);
                              });
                            self.marker = marker;

                    }else{
                            navigator.geolocation.getCurrentPosition(
                                   function(position){
                                        var pos = {
                                              lat: position.coords.latitude,
                                              lng: position.coords.longitude,
                                            };

                                        var currentLatLng =  new google.maps.LatLng(position.coords.latitude, position.coords.longitude)
                                        console.log("Navigation position:"+currentLatLng);
                                        self.customer_location = currentLatLng;
                                        gmap  = new google.maps.Map(map_div, {
                                                        mapTypeId: google.maps.MapTypeId.ROADMAP,
                                                        zoom: 17,
                                                        center: pos,
                                                        mapTypeControl: true,
                                                        zoomControl: true,
                                                        rotateControl: true,
                                                        streetViewControl:true,
                                                        });

                                          infoWindow = new google.maps.InfoWindow({
                                                           content: custName
                                                      });

                                         marker = new google.maps.Marker({
                                            position: pos,
                                            draggable: true,
                                            animation: google.maps.Animation.DROP,
                                            title: custName
                                          });
                                          if(partner_id!=""||Boolean(partner_id)!=false)
                                          {
                                              if(session.currentLatLng==null || session.currentLatLng!=currentLatLng){
                                                      console.log("session Customer Location:"+currentLatLng);

                                                     self.trigger_up('field_changed', {
                                                                             dataPointID: self.id,
                                                                             changes: {
                                                                                 partner_latitude: position.coords.latitude,
                                                                                 partner_longitude: position.coords.longitude,
                                                                             },
                                                                             viewType: self.viewType,
                                                                 });
                                                     session.currentLatLng = currentLatLng;
                                                  }
                                              }
                                          self.marker = marker;
                                          marker.setMap(gmap);
                                          marker.addListener('dragend', function(mouseEvent) {
                                                var currentLatLng =  new google.maps.LatLng(marker.getPosition().lat(), marker.getPosition().lng())

                                                self.customer_location = currentLatLng;

                                                console.log("Change Location lat"+marker.getPosition().lat()
                                                            +",long"+marker.getPosition().lng());
                                                          self.trigger_up('field_changed', {
                                                                     dataPointID: self.id,
                                                                     changes: {
                                                                         partner_latitude: marker.getPosition().lat(),
                                                                         partner_longitude: marker.getPosition().lng(),
                                                                     },
                                                                     viewType: self.viewType,
                                                         });

                                                            infoWindow.open(gmap, marker);
                                              });

                                     }
                                   , function(error){
                                         var pos = {
                                              lat: 16.8767626,
                                              lng: 96.1571778,
                                            };

                                        marker = new google.maps.Marker({
                                            position: pos,
                                            draggable: true,
                                            animation: google.maps.Animation.DROP,
                                            title: custName
                                          });
                                          infoWindow = new google.maps.InfoWindow({
                                                           content: custName
                                                      });
                                          self.marker = marker;
                                          marker.setMap(gmap);
                                          marker.addListener('dragend', function(mouseEvent) {
                                                var currentLatLng =  new google.maps.LatLng(marker.getPosition().lat(), marker.getPosition().lng())
                                                self.customer_location = currentLatLng;

                                                console.log("Change Location lat"+marker.getPosition().lat()
                                                            +",long"+marker.getPosition().lng());
                                                          self.trigger_up('field_changed', {
                                                                     dataPointID: self.id,
                                                                     changes: {
                                                                         partner_latitude: marker.getPosition().lat(),
                                                                         partner_longitude: marker.getPosition().lng(),
                                                                     },
                                                                     viewType: self.viewType,
                                                         });

                                                            infoWindow.open(gmap, marker);
                                              });

                                   }, options);

                    }

                 },
        });
    widgetRegistry.add('location_ci', WidgetCoordinates);
});
