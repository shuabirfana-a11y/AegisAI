"""Single operator loop with due checks in existing collectors and interruptible waits."""
import math
from threading import Event

class MonitoringScheduler:
    def __init__(self,pipeline,*,interval=300):
        if not math.isfinite(interval) or not 3<=interval<=86400:raise ValueError('Interval must be 3..86400 finite seconds')
        self.pipeline=pipeline;self.interval=interval
    def run(self,sources,*,cycles=1,force_first=False,stop=None,wait=None):
        if isinstance(cycles,bool) or not isinstance(cycles,int) or not 1<=cycles<=10000:raise ValueError('Cycles must be 1..10000')
        stop=stop or Event();wait=wait or stop.wait
        for cycle in range(cycles):
            if stop.is_set():break
            yield self.pipeline.run_cycle(sources,force=force_first and cycle==0,stop=stop)
            if cycle+1<cycles and not stop.is_set() and wait(self.interval):break
