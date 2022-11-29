odoo.define('web_iframe.iframe', function (require) {
    "use strict";

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var framework = require('web.framework');
    var session = require('web.session');
    var Dialog = require('web.Dialog');
    var rpc = require('web.rpc');
    var _t = core._t;
    var apps_client = null;
    var Dashboard = AbstractAction.extend({
    	 init: function (parent, action) {
             this._super(parent, action);
             this.action = _.clone(action);
             this.action.params = _.extend({
                 'link': 'https://yelizariev.github.io/'
             }, this.action.params);
         },
        start: function () {
            var self = this;
            self.view_dashboard();
        },
        view_dashboard: function () {
            var self = this;
            var def = $.Deferred();
            var url = this.action.params.link;
            rpc.query({
                model: 'res.users',
                method: 'read',
                args: [[session.uid], ['branch_ids']],
            }).then(function (record) {
                if (record)
                {
                    var branch_url = '';
                    if (record[0]['branch_ids'].length > 0) {
                        branch_url += '&p.branchid='+ record[0]['branch_ids'];
                    }
                    var final_url = url + branch_url;
                    var width = '100%';
                    var height = '100%';
                    var css = {width: width, height: height};
                    self.$ifr = $('<iframe>').attr('src', final_url);
                    self.$ifr.appendTo(self.$('.o_content')).css(css);
                    self.$ifr.appendTo();
                }
            });
        }    
    });

    core.action_registry.add("web_iframe.iframe", Dashboard);
    return Dashboard;

});
