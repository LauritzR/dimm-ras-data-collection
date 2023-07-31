from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from libs.pmon.pmon_metric_values import ABSPMONValues

@dataclass
class MetricMetaData:
    tool: str
    creation_timestamp: datetime
    tool_timestamp: Optional[datetime] = None
    hostname: Optional[str] = None


@dataclass
class AbsMetrics(ABC):
    """Parent class for the metric value for a specific tool"""


@dataclass
class AbsMetricValues(ABC):
    metrics: Any
    meta: MetricMetaData


@dataclass
class PMONMetricValues(AbsMetricValues):
    metrics: ABSPMONValues


@dataclass
class SimpleMetricValue(AbsMetricValues):
    metrics: Any
    meta: MetricMetaData = field(
        default_factory=lambda: MetricMetaData(
            tool="SimpleMetric", creation_timestamp=datetime.now()
        )
    )
