from libs.hwmon.hwmon import HWMON

hwmon = HWMON()
for item in hwmon.get_temperatures():
    print(item)
