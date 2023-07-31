from abc import ABC
from typing import List

from libs.metric_values import AbsMetricValues

class AbsDataProcessor(ABC):
    def write_metric(self, data: List[AbsMetricValues]) -> None:
        print(data)
