import os

path_cur = os.path.abspath(os.path.dirname(__file__))
zk_lib_path = path_cur + '/util/libs/zk_lib'
print(zk_lib_path)
file_path = '/etc/ld.so.conf.d/zk_lib.conf'
with open(file_path, "w") as file:
    file.write(zk_lib_path)
os.system('bash ldconfig')
