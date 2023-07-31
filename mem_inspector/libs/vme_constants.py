from typing import Final

# Metric names
METRIC_KIND_NAME_CEUCE_VPROBE: Final[str] = "CEnUCEVProbe"
METRIC_KIND_NAME_NET_STATS: Final[str] = "net-stats"
METRIC_KIND_NAME_ESXTOP: Final[str] = "esxtop"


# Processors
PROCESSOR_AMD_NAME: Final[str] = "AuthenticAMD"
PROCESSOR_INTEL_NAME: Final[str] = "GenuineIntel"
PCI_AMD_VENDORID: Final[int] = 0x1002
PCI_INTEL_VENDORID: Final[int] = 0x8086
PCI_UNKNOWN_VENDORID: Final[int] = 0x0BAD

# SkyLake specific model and family
INTEL_SKYLAKE_XEON_SCALABLE_FAMILY: Final[int] = 0x06
INTEL_SKYLAKE_XEON_SCALABLE_MODEL: Final[int] = 0x55


# Prometheus value names
# MCA
MCA_ERROR_CLASSIFICATIONS = "MC_Error_Classifications"
MCA_STATUS_VAL = "MCi_STATUS_register_is_valid"
MCA_STATUS_OVER = "MCi_STATUS_register_error_overflow"
MCA_STATUS_UC = "MCi_STATUS_register_UE_error"
MCA_STATUS_EN = "MCi_STATUS_register_error_reporting_enabled"
MCA_STATUS_MISCV = "MCi_STATUS_MCi_misc_register_is_valid"
MCA_STATUS_ADDRV = "MCi_STATUS_MCi_addr_register_is_valid"
MCA_STATUS_PCC = "MCi_STATUS_Processor_context_corrupted"
MCA_STATUS_S = "MCi_status_Signaling an uncorrected recoverable (UCR) error"
MCA_STATUS_AR = "MCi_STATUS_Recovery action required for UCR error"


# MC Error classifications
MCE_UC: Final[str] = "Uncorrected Error (UC)"
MCE_SRAR: Final[str] = "Software recoverable action required (SRAR)"
MCE_SRAO: Final[str] = "Software recoverable action optional (SRAO)"
MCE_UCNA: Final[str] = "Uncorrected no action required (UCNA)"
MCE_CE: Final[str] = "Corrected Error (CE)"

CPU_VENDORID: Final[str] = "cpu_vendorid"
CPU_MODEL: Final[str] = "cpu_model"
CPU_FAMILY: Final[str] = "cpu_family"

DEVICEID: Final[str] = "deviceID"
VENDORID: Final[str] = "vendorID"
