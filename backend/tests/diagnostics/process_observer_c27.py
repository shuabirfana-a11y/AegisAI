"""Opt-in test/diagnostic observer: no launch, cleanup or acceptance decisions change."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import ctypes, inspect, json, os, sys, threading, subprocess


@contextmanager
def installed(path):
    from app.runtime import process
    from app.agents import executor
    from tests.diagnostics.artifact_observer import Observer, installed as artifacts_installed
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);lock=threading.RLock()
    watched={f.__code__ for f in [process.create_isolation,process.ProcessSupervisor.execute,
        process._WindowsJob.__init__,process._WindowsJob.attach,process._WindowsJob.terminate,
        process._WindowsJob.empty,process._WindowsJob.close]}
    watched.update(getattr(subprocess.Popen,n).__code__ for n in ("_execute_child","_get_handles") if hasattr(subprocess.Popen,n))
    supervisor_code=process.ProcessSupervisor.execute.__code__
    def iterate_tb(tb):
        while tb is not None:
            yield tb;tb=tb.tb_next
    def record(code,offset,exc):
        if code not in watched:return
        try:
            last_error=ctypes.get_last_error()
            frame=sys._getframe(1);at=frame;context=None;task=None;pid=None
            for _ in range(15):
                if at is None:break
                if at.f_code is supervisor_code:
                    context=at.f_locals.get('context');task=at.f_locals.get('task')
                    child=at.f_locals.get('process');pid=getattr(child,'pid',None);break
                at=at.f_back
            text=str(exc)
            safe=text if text.startswith(('Unable to ','Task process ','can\'t start new thread','cannot start new thread')) else 'REDACTED'
            data={'at_utc':datetime.now(timezone.utc).isoformat(),'function':code.co_name,'source_line':frame.f_lineno,
                'source':Path(code.co_filename).name,'exception_type':type(exc).__name__,'reason':safe,
                'winerror':getattr(exc,'winerror',None),'errno':getattr(exc,'errno',None),
                'exception_file':getattr(exc,'filename',None),'subprocess_stack':[{'function':t.tb_frame.f_code.co_name,'file':Path(t.tb_frame.f_code.co_filename).name,'line':t.tb_lineno} for t in iterate_tb(exc.__traceback__)],'thread_last_error':last_error,'offset':offset,'process_id':os.getpid(),
                'thread_id':threading.get_ident(),'worker_pid':pid,'run_id':str(getattr(context,'run_id','')),
                'trace_id':str(getattr(context,'trace_id','')),'task_id':getattr(task,'task_id',None)}
            with lock:
                with path.open('a',encoding='utf8') as f:f.write(json.dumps(data,ensure_ascii=False)+'\n')
        except Exception:pass  # Observability cannot grant execution or change failure handling.
    monitor=next(i for i in [3,4,5] if sys.monitoring.get_tool(i) is None)
    sys.monitoring.use_tool_id(monitor,'c27-process-diagnostics')
    sys.monitoring.register_callback(monitor,sys.monitoring.events.RAISE,record)
    sys.monitoring.set_events(monitor,sys.monitoring.events.RAISE)
    try:
        with artifacts_installed(Observer(path.with_suffix('.artifacts.jsonl'))):yield
    finally:
        sys.monitoring.set_events(monitor,0)
        sys.monitoring.register_callback(monitor,sys.monitoring.events.RAISE,None)
        sys.monitoring.free_tool_id(monitor)


def pytest_configure(config):
    path=os.environ.get('AEGIS_C27_PROCESS_LOG')
    if path:
        scope=installed(path);scope.__enter__();config._c27_process_scope=scope


def pytest_unconfigure(config):
    scope=getattr(config,'_c27_process_scope',None)
    if scope:scope.__exit__(None,None,None)

# Optional prefix-only launch probe; never activates in regular regression or HTTP.
def pytest_runtest_teardown(item,nextitem):
    if os.environ.get('AEGIS_C27_PREFIX_PROBE')!='1':return
    try:
        child=subprocess.run([sys.executable,'-c','print("probe")'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        info={'after':item.nodeid,'exit_code':child.returncode,'launch':'OK'}
    except OSError as e:
        info={'after':item.nodeid,'launch':'FAILED','exception':type(e).__name__,'winerror':getattr(e,'winerror',None),'filename':e.filename}
    with Path(os.environ['AEGIS_C27_PROCESS_LOG']).with_suffix('.prefix.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(info)+'\n')
