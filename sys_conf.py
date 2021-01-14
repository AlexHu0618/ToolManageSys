import os

# for ZK entrance
path_cur = os.path.abspath(os.path.dirname(__file__))
zk_lib_path = path_cur + '/util/libs/zk_lib'
print(zk_lib_path)
file_path = '/etc/ld.so.conf.d/zk_lib.conf'
with open(file_path, "w") as file:
    file.write(zk_lib_path)
os.system('ldconfig')

# for HK entrance
path_cur = os.path.abspath(os.path.dirname(__file__))
hk_lib_path = path_cur + '/util/libs/hkvision_lib/'
hk_lib_path2 = path_cur + '/util/libs/hkvision_lib/HCNetSDKCom/'
print(hk_lib_path)
file_path = '/etc/ld.so.conf.d/hkvsdk_lib.conf'
with open(file_path, "w") as file:
    file.write(hk_lib_path + '\n' + hk_lib_path2)
os.system('ldconfig')
