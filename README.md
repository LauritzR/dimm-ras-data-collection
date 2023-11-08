# dimm-ras
DIMM RAS feature monitoring on Linux servers

This tool was developed with the publication ... for data collection to train CNNs for failure risk estimation of memory modules among other things. If you use our work, we are happy if you cite it.

## Linux kernel module modification

sb_edac.c contains the necessary code to fetch corrected error address on Intel E5 and E7 v4 processors.
staticint sb_rd_err_log(void *data) has been added for this purpose.
sb_edac driver is modified to be a poll mode driver (hardcoded to 10ms) instead of depending on MCE interrupt.
This is a driver to be used with BROADWELL and HASWELL processors. For the recent Skylake onwards, skx_edac.c exists in linux tree.
The modified driver contains sb_rd_err_log function to poll the RANK level memory counters from the aforementioned processors.
This approach is necessary when HW vendors disable interrupt delivery to the OS or Hypervisor.

## Compiling the Kernel Module:

Goto the path of linux source

Copy the symbol table: for example:

cp /usr/src/kernels/5.9.8-asgard-git-/Module.symvers ./

Copy the existing kernel config to the path where xlane-patched-linux is present.

Ex: cp /boot/config-5.9.8-asgard-git-+ ./.config

Run menuconfig to modify kernel configuration settings (Optional)

make menuconfig

Run prepare scripts

make scripts prepare modules_prepare

Run make for desired target. For example: to compile all the network drivers run as below:

make -C . M=drivers/edac/

Copy the compiled .ko file to the path where current kernel modules are present.

sudo cp drivers/edac/sb_edac.ko  /lib/modules/5.9.8-asgard-git-+/kernel/drivers/edac/

Resolve the dependency

sudo depmod

The latest kernel module should be in effect at this point. Verify by running the command

modinfo module_name


## Enabling MCEnterrupts with vendor collaboration

Please refer to the document CMCI_IntelMCA_inFFM_Mode for more information.


## VME metrics

* bin/
  * mem_inspector.py - Memory Inpsector (collects data from MEM_BW, CORRERRCNT, HWMON, DIMM temp)
* demos/ - set of standalone demos based on PMON,HWMON libraries
* services/
  * mem_inspector.service - Systemd service, collecting mem_inpsector output in CSV format
  * pcm_memory_bw.service - Systemd service, collecting memory bandwidth in CSV format

### Instalation
```
cp services/*.service /etc/systemd/system
systemctl enable mem_inspector.service
systemctl enable pcm_memory_bw.service
```
Check the ./vme/bin/mem_inspector.py for
* interval time values
* DID values<br>
    ```
    Command("read_correrrcnt", 
    [
        "read_correrrcnt",
        "0x6fb2", "0x6fb3", "0x6fb6", "0x6fb7", "0x6fd2", "0x6fd3", "0x6fd6", "0x6fd7"
    ], 15)
  ```

interval time is 15 seconds<br>
DIDs are the list of PCI devices identified by DeviceID.<br>
If not sure please check "lspci -D -nn" output and search for Memory Controller the [VID:DID] sequence is<br>
present in every row. Intel E7 V4 has [8086:6f**] where Intel E7 V3 might have [8086:2f**].<br>
Please setup accordingly.
At the end please launch:

```
systemctl start mem_inspector.service
systemctl start pcm_memory_bw.service
```

and check the /var/log/mem_inspector*.log or /var/log/pcm_memory_bw.csv

### Read CSV data

When memory inspector is controlled by mem_inspector.service all standard output / error streams are redirected to files:

StandardOutput=file:/var/log/mem_inspector_stdout.log
StandardError=file:/var/log/mem_inspector_stderr.log

File mem_inspector_stdout.log should include CSV data that can be view and edit in Excel environment.


#### Header file PMON read_correrrcnt

Date ; Tool Name ; Host ID ; Device address ; correrrcnt_0 ; correrrcnt_1 ; correrrcnt_2 ; correrrcnt_3 ; correrrthrshld_0 ; correrrthrshld_1 ; correrrthrshld_2 ; correrrthrshld_3 ; correrrorstatus

```
"2022-11-22 15:52:55.487297";"pmon.read_correrrcnt";"h03hcrbbm06";"0000:ff:14.3";"0";"0";"0";"0";"2147450879";"2147450879";"2147450879";"2147450879";"274432";
```

#### Header file PMON read_dimm_temp

Date ; Tool Name ; Host ID ; Device address ; channel0_max_temp ; channel1_max_temp ; channel2_max_temp ; channel3_max_temp

```
"2022-11-22 15:52:55.564085";"pmon.read_dimm_temp";"h03hcrbbm06";"0000:3f:14.0";"0";"0";"0";"0";
```

#### Header file PMON HWMON read_temp

Date ; Tool Name ; Host ID ; Temperature sensor name ; Sensor # ; Socket # ; Input temp ; Critical temp ; Maximum temp

```
"2022-11-22 15:52:55.569925";"hwmon.read_temp";"h03hcrbbm06";"Package 0";"1";"0";"29.0";"98.0";"88.0";
"2022-11-22 15:52:55.569942";"hwmon.read_temp";"h03hcrbbm06";"Core 0";"10";"0";"27.0";"98.0";"88.0";
"2022-11-22 15:52:55.569950";"hwmon.read_temp";"h03hcrbbm06";"Core 1";"20";"0";"28.0";"98.0";"88.0";
"2022-11-22 15:52:55.569958";"hwmon.read_temp";"h03hcrbbm06";"Core 2";"21";"0";"27.0";"98.0";"88.0";
```

Where Input temp, Critial temp, Maximum temp are represented by float values in Celcius degree i.e 27.0°C
