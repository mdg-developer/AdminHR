import xmlrpc.client

url = "http://localhost:8813"
db = "boc"
username = "admin"
password = "admin"
# username = "admin"
# password = "admin"
#
# url = "http://69.175.42.237:9000"
# db = "divyasree_live_051118"
# username = "admin"
# password = "admin"
# username = "gosala444@gmail.com"
# password = "Shiva@123"


# 1.Update the one signal device details
denali_model = "one_signal_notification.users_device_ids"
denali_method = "update_one_signal_device"
denali_parameters = [{
    'device_id': '78', 'operation': "login"  # ['login', 'logout']
}]


common = xmlrpc.client.ServerProxy('{}/xmlrpc/2/common'.format(url))
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy('{}/xmlrpc/2/object'.format(url))
result = models.execute_kw(db, uid, password, denali_model, denali_method, denali_parameters)

print("uid", uid)
print("denali_method", denali_method)
print("result", result)